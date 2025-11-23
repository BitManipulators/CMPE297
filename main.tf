# 1. Dynamic Availability Zones 
# Fetch available AZs dynamically instead of hardcoding "us-west-2a", "us-west-2b", etc
data "aws_availability_zones" "available" {
  state = "available"
}

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
