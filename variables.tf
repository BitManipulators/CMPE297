variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-west-2"
}

variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "node_instance_types" {
  description = "List of instance types for the managed node group"
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_desired_size" {
  description = "Desired number of worker nodes"
  type        = number
  default     = 1
}

variable "node_min_size" {
  description = "Minimum number of worker nodes"
  type        = number
  default     = 1
}

variable "node_max_size" {
  description = "Maximum number of worker nodes"
  type        = number
  default     = 3
}

variable "tls_crt" {
  description = "The full content of the Cloudflare Origin Certificate"
  type        = string
  sensitive   = true
}

variable "tls_key" {
  description = "The full content of the Cloudflare Private Key"
  type        = string
  sensitive   = true
}

variable "cloudflare_zone_id" {
  description = "The Zone ID of your domain from Cloudflare Dashboard"
  type        = string
}

variable "backend_base_url" {
  description = "The URL of the backend for the web service"
  type        = string
}

variable "websocket_base_url" {
  description = "The URL of the websocket for the web service"
  type        = string
}
