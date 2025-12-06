# 1. Dynamic Availability Zones 
# Fetch available AZs dynamically instead of hardcoding "us-west-2a", "us-west-2b", etc
data "aws_availability_zones" "available" {
  state = "available"
}

# Get cloudflare IP address ranges
data "cloudflare_ip_ranges" "cloudflare" {}

# 2. VPC Configuration
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "eks-vpc-single-nat"
  cidr = var.vpc_cidr

  # Dynamically grab the first 3 AZs from the region
  azs = slice(data.aws_availability_zones.available.names, 0, 3)

  # Standard subnet patterns
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]

  # --- NAT GATEWAY CONFIGURATION ---
  # We enable NAT but restrict it to a SINGLE gateway to save ~$64/month
  # Because each available zone is $32/month, and we only run it in 1 out of 3 AZs
  enable_nat_gateway     = true
  single_nat_gateway     = true
  one_nat_gateway_per_az = false
  enable_vpn_gateway     = false

  # Tags for Public Load Balancers (Internet facing)
  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }

  # Tags for Private Load Balancers (Internal only)
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
  }
}

# 2. Create a dedicated Security Group for the NLB / Nodes
resource "aws_security_group" "ingress_allow_cloudflare" {
  name        = "allow-cloudflare-only"
  description = "Allow HTTPS from Cloudflare IPs only"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description = "HTTPS from Cloudflare IPv4"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = data.cloudflare_ip_ranges.cloudflare.ipv4_cidr_blocks
  }

  ingress {
    description      = "HTTPS from Cloudflare IPv6"
    from_port        = 443
    to_port          = 443
    protocol         = "tcp"
    ipv6_cidr_blocks = data.cloudflare_ip_ranges.cloudflare.ipv6_cidr_blocks
  }
}

# 3. EKS Cluster
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = var.cluster_name
  cluster_version = "1.34"

  vpc_id = module.vpc.vpc_id

  # Control Plane ENIs live in ALL private subnets (Required by AWS for HA)
  subnet_ids = module.vpc.private_subnets

  # We keep the API public so you can run kubectl from your laptop
  cluster_endpoint_public_access = true

  cluster_addons = {
    coredns = { most_recent = true }
    kube-proxy = { most_recent = true }
    vpc-cni = {
      most_recent = true
      configuration_values = jsonencode({
        env = {
          ENABLE_PREFIX_DELEGATION = "true"
          WARM_PREFIX_TARGET       = "1"
        }
      })
    }
    eks-pod-identity-agent = { most_recent = true }
  }

  # This creates the OpenID Connect Provider URL for the cluster
  enable_irsa = true

  # 4. Managed Node Group
  eks_managed_node_groups = {
    main = {
      # Use variables for scaling
      min_size     = var.node_min_size
      max_size     = var.node_max_size
      desired_size = var.node_desired_size

      instance_types = var.node_instance_types
      capacity_type  = "SPOT"

      # --- COST SAVING PIN ---
      # We force nodes to live ONLY in the first private subnet.
      # This matches where the single NAT Gateway lives (usually the first AZ).
      # This minimizes cross-AZ data transfer fees.
      subnet_ids = [element(module.vpc.private_subnets, 0)]

      # Allow access from cloudflare ips only
      vpc_security_group_ids = [aws_security_group.ingress_allow_cloudflare.id]

      ami_type = "AL2023_x86_64_STANDARD"

      # Add SSM permissions so we can "console in" to private nodes
      iam_role_additional_policies = {
        AmazonSSMManagedInstanceCore = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
      }

      cloudinit_pre_nodeadm = [
        {
          content_type = "application/node.eks.aws"
          content      = <<-EOT
            ---
            apiVersion: node.eks.aws/v1alpha1
            kind: NodeConfig
            spec:
              kubelet:
                config:
                  maxPods: 110
          EOT
        }
      ]
    }
  }

  enable_cluster_creator_admin_permissions = true

  # Disable these for cost savings (enabled by default).
  # 1. Cluster logging: uses CloudWatch which is not free
  cluster_enabled_log_types = []  # Empty list disables all logging
  create_cloudwatch_log_group = false

  # 2. KMS encryption: encrypts etcd database entries, but is also not free
  create_kms_key = false
  cluster_encryption_config = {}
}

# ---------------------------------------------------------
# 5. Install NGINX Ingress Controller and TLS certificate
# ---------------------------------------------------------
resource "kubernetes_secret" "cloudflare_origin_cert" {
  metadata {
    name      = "cloudflare-origin-cert"
    namespace = "default"                # Must be same namespace as your Ingress
  }

  type = "kubernetes.io/tls"

  data = {
    "tls.crt" = var.tls_crt
    "tls.key" = var.tls_key
  }
}

resource "helm_release" "nginx_ingress" {
  name             = "ingress-nginx"
  repository       = "https://kubernetes.github.io/ingress-nginx"
  chart            = "ingress-nginx"
  namespace        = "ingress-nginx"
  create_namespace = true
  version          = "4.10.0" # Stable version

  # This forces Terraform to wait until the Load Balancer is actually ready
  wait = true

  # --- CONFIGURING THE AWS LOAD BALANCER ---
  set {
    name  = "controller.service.annotations.service\\.beta\\.kubernetes\\.io/aws-load-balancer-type"
    value = "nlb" # Uses the modern Network Load Balancer (High Performance)
  }

  # Use the "external" scheme so it is reachable from the internet
  set {
    name  = "controller.service.annotations.service\\.beta\\.kubernetes\\.io/aws-load-balancer-scheme"
    value = "internet-facing"
  }
}

# ---------------------------------------------------------
# 6. The Ingress Rule (Routing Traffic)
# ---------------------------------------------------------
resource "kubernetes_ingress_v1" "main_ingress" {
  metadata {
    name      = "main-ingress"
    namespace = "default" # Must match where your Apps are
    annotations = {
      # Tell K8s this rule belongs to NGINX
      "kubernetes.io/ingress.class" = "nginx"

      # Rewrite logic for the API
      # This strips "/backend" from the request before sending it to FastAPI
      "nginx.ingress.kubernetes.io/rewrite-target" = "/$2"
      "nginx.ingress.kubernetes.io/use-regex"      = "true"

      # Optimization: Allow larger uploads (e.g. images) if needed
      "nginx.ingress.kubernetes.io/proxy-body-size" = "10m"
    }
  }

  spec {
    # Use the Cloudflare Secret for SSL
    tls {
      hosts       = ["iotsmarthome.org"]
      secret_name = kubernetes_secret.cloudflare_origin_cert.metadata[0].name
    }

    rule {
      host = "iotsmarthome.org"
      http {
        # --- FRONTEND ROUTE ---
        path {
          path      = "/()(.*)"
          path_type = "ImplementationSpecific"
          backend {
            # MAKE SURE THIS MATCHES YOUR K8S SERVICE NAME FOR FLUTTER
            service {
              name = "flutter-frontend"
              port { number = 80 }
            }
          }
        }

        # --- BACKEND ROUTE ---
        path {
          path      = "/backend(/|$)(.*)"
          path_type = "ImplementationSpecific"
          backend {
            # MAKE SURE THIS MATCHES YOUR K8S SERVICE NAME FOR FASTAPI
            service {
              name = "fastapi-backend"
              port { number = 8001 }
            }
          }
        }
      }
    }
  }

  # Ensure NGINX is installed before we try to create rules for it
  depends_on = [helm_release.nginx_ingress]
}

# ---------------------------------------------------------
# 7. Create ECR container repositories
# ---------------------------------------------------------
resource "aws_ecr_repository" "flutter_app" {
  name                 = "into-the-wild-web-app"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "fastapi_backend" {
  name                 = "into-the-wild-backend"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

# ---------------------------------------------------------
# 8. Build & Push Flutter Image
# ---------------------------------------------------------
resource "docker_image" "flutter_image" {
  name = "${aws_ecr_repository.flutter_app.repository_url}:latest"

  build {
    # Path to the folder containing the Flutter Dockerfile
    context = "./" 
    dockerfile = "Dockerfile"
    platform = "linux/amd64" 

    build_args = {
      BACKEND_BASE_URL_ARG = var.backend_base_url
      WEBSOCKET_BASE_URL_ARG = var.websocket_base_url
    }
  }

  # This ensures the image is rebuilt if files change
  triggers = {
    dir_sha1 = sha1(join("", [for f in fileset("./lib", "**") : filesha1("./lib/${f}")], [filesha1("./Dockerfile")]))
  }
}

resource "docker_registry_image" "flutter_push" {
  name          = docker_image.flutter_image.name
  keep_remotely = false # Delete the image from ECR when you run 'terraform destroy'
  
  # Wait for the build to finish
  triggers = {
    image_sha1 = docker_image.flutter_image.repo_digest
  }
}

# A null_resource that executes the docker build command verbosely.
# This is purely for displaying the output during 'terraform apply' execution.
resource "null_resource" "verbose_flutter_docker_build" {
  triggers = {
    dir_sha1           = sha1(join("", [for f in fileset("./lib", "**") : filesha1("./lib/${f}")], [filesha1("./Dockerfile")]))
  }

  provisioner "local-exec" {
    # The command runs docker build with the same arguments as the docker_image resource.
    command = <<-EOT
      echo "--- STARTING VERBOSE DOCKER BUILD FOR DEBUGGING ---"
      docker build \
        --platform linux/amd64 \
        --tag ${aws_ecr_repository.flutter_app.repository_url}:latest \
        --file Dockerfile \
        --build-arg BACKEND_BASE_URL_ARG=${var.backend_base_url} \
        --build-arg WEBSOCKET_BASE_URL_ARG=${var.websocket_base_url} \
        ./
      echo "--- VERBOSE DOCKER BUILD COMPLETE ---"
    EOT

    # Setting the interpreter to bash helps with multiline commands
    interpreter = ["bash", "-c"] 
  }
}

# ---------------------------------------------------------
# 9. Flutter Frontend Deployment
# ---------------------------------------------------------
resource "kubernetes_deployment_v1" "flutter_frontend" {
  metadata {
    name      = "flutter-frontend"
    namespace = "default"
    labels = {
      app = "flutter-frontend"
    }
  }

  spec {
    # Run 3 copies for high availability (zero downtime during updates)
    replicas = 3

    selector {
      match_labels = {
        app = "flutter-frontend"
      }
    }

    template {
      metadata {
        labels = {
          app = "flutter-frontend"
        }
      }

      spec {
        container {
          name  = "flutter-web-ui"
          # Dynamically grab the ECR URL we created earlier + the tag
          image = docker_image.flutter_image.repo_digest

          # Always pull the latest version of the tag (useful for dev)
          image_pull_policy = "Always"

          port {
            container_port = 80 # Nginx inside the container listens on 80
          }

          # (Optional) Health Check: Nginx is healthy if it serves the index
          liveness_probe {
            http_get {
              path = "/"
              port = 80
            }
            initial_delay_seconds = 3
            period_seconds        = 3
          }
        }
      }
    }
  }

  depends_on = [docker_registry_image.flutter_push]
}

# ---------------------------------------------------------
# 10. Flutter Frontend Service
# ---------------------------------------------------------
resource "kubernetes_service_v1" "flutter_frontend" {
  metadata {
    # CRITICAL: This name must match what you put in the Ingress!
    name      = "flutter-frontend"
    namespace = "default"
  }

  spec {
    selector = {
      app = "flutter-frontend" # Matches the deployment labels above
    }

    port {
      port        = 80 # Port the Service listens on
      target_port = 80 # Port the Container listens on
    }

    type = "ClusterIP" # Internal only. Ingress exposes it to the world.
  }
}

# ---------------------------------------------------------
# 11. Build & Push FastAPI Image
# ---------------------------------------------------------
resource "docker_image" "fastapi_image" {
  name = "${aws_ecr_repository.fastapi_backend.repository_url}:latest"

  build {
    # Path to the folder containing the FastAPI Dockerfile
    context = "./backend" 
    dockerfile = "Dockerfile.fastapi"
    
    # Platform for compatibility
    platform = "linux/amd64"
  }

  triggers = {
    dir_sha1 = sha1(join("", [for f in fileset("./backend", "**") : filesha1("./backend/${f}")]))
  }
}

resource "docker_registry_image" "fastapi_push" {
  name          = docker_image.fastapi_image.name
  keep_remotely = false
  
  triggers = {
    image_sha1 = docker_image.fastapi_image.repo_digest
  }
}

# ---------------------------------------------------------
# 12. FastAPI Backend Deployment
# ---------------------------------------------------------
resource "kubernetes_deployment_v1" "fastapi_backend" {
  metadata {
    name      = "fastapi-backend"
    namespace = "default"
    labels = {
      app = "fastapi-backend"
    }
  }

  spec {
    replicas = 1 # High Availability Not Yet Supported
    #replicas = 3 # High Availability

    selector {
      match_labels = {
        app = "fastapi-backend"
      }
    }

    template {
      metadata {
        labels = {
          app = "fastapi-backend"
        }
      }

      spec {
        container {
          name  = "fastapi-server"
          image = docker_image.fastapi_image.repo_digest
          image_pull_policy = "Always"

          port {
            container_port = 8001
          }

          # Environment Variables for Google SSO
          env {
            name  = "GOOGLE_CLIENT_ID"
            value = "your-google-client-id"
          }

          # Liveness Probe (Health Check)
          # Assumes you have a GET / or GET /health endpoint
          liveness_probe {
            http_get {
              path = "/"
              port = 8001
            }
            initial_delay_seconds = 5
            period_seconds        = 10
          }
        }
      }
    }
  }

  depends_on = [docker_registry_image.fastapi_push]
}

# ---------------------------------------------------------
# 13. FastAPI Backend Service
# ---------------------------------------------------------
resource "kubernetes_service_v1" "fastapi_backend" {
  metadata {
    # CRITICAL: Must match the backend service name in your Ingress
    name      = "fastapi-backend"
    namespace = "default"
  }

  spec {
    selector = {
      app = "fastapi-backend"
    }

    port {
      port        = 8001 # Service Port (Ingress talks to this)
      target_port = 8001 # Container Port (Uvicorn listens on this)
    }

    type = "ClusterIP" # Internal only
  }
}

# ---------------------------------------------------------
# 14. Cloudflare WAF Rules
# ---------------------------------------------------------
resource "cloudflare_ruleset" "zone_custom_firewall" {
  zone_id     = var.cloudflare_zone_id
  name        = "Basic Security Rules"
  description = "Block bad countries and admin panels"
  kind        = "zone"
  phase       = "http_request_firewall_custom"

  # Rule 1: Block specific countries (e.g., CN, RU, NK)
  rules {
    action = "block"
    expression = "(ip.geoip.country in {\"CN\" \"RU\" \"KP\" \"IR\"})"
    description = "Block High Risk Countries"
    enabled = true
  }

  # Rule 2: Challenge bad user agents (Python scripts, curl, etc)
  rules {
    action = "managed_challenge"
    expression = "(http.user_agent contains \"Python\" or http.user_agent contains \"curl\" or http.user_agent contains \"wget\")"
    description = "Challenge Script Bots"
    enabled = true
  }
}
