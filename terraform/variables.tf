variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "ap-south-1"
}

variable "aws_profile" {
  description = "AWS shared config profile used by Terraform"
  type        = string
  default     = ""
}

variable "project_name" {
  description = "Project identifier used for naming"
  type        = string
  default     = "todo-capstone"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "CIDR for VPC"
  type        = string
  default     = "10.20.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDRs"
  type        = list(string)
  default     = ["10.20.1.0/24", "10.20.2.0/24"]
}

variable "private_app_subnet_cidrs" {
  description = "Private app subnet CIDRs"
  type        = list(string)
  default     = ["10.20.11.0/24", "10.20.12.0/24"]
}

variable "private_db_subnet_cidrs" {
  description = "Private db subnet CIDRs"
  type        = list(string)
  default     = ["10.20.21.0/24", "10.20.22.0/24"]
}

variable "allowed_ingress_cidr" {
  description = "CIDR allowed to access ALB"
  type        = string
  default     = "0.0.0.0/0"
}

variable "app_instance_type" {
  description = "EC2 instance type for app tier"
  type        = string
  default     = "t3.micro"
}

variable "app_ami_id" {
  description = "AMI for app instances"
  type        = string
}

variable "app_min_size" {
  description = "Minimum ASG size"
  type        = number
  default     = 2
}

variable "app_max_size" {
  description = "Maximum ASG size"
  type        = number
  default     = 6
}

variable "app_desired_capacity" {
  description = "Desired ASG capacity"
  type        = number
  default     = 2
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.micro"
}

variable "db_name" {
  description = "RDS database name"
  type        = string
  default     = "todo"
}

variable "db_username" {
  description = "RDS master username"
  type        = string
  default     = "todoadmin"
}

variable "db_password" {
  description = "RDS master password"
  type        = string
  sensitive   = true
}

variable "docker_image_uri" {
  description = "Docker image URI to run on app instances"
  type        = string
  default     = ""
}

variable "config_s3_prefix" {
  description = "S3 key prefix containing deployment config artifacts"
  type        = string
  default     = "runtime/current"
}

variable "active_environment" {
  description = "Active deployment slot for blue-green style rollouts"
  type        = string
  default     = "blue"
}

variable "app_secret_key" {
  description = "Flask secret key for app instances"
  type        = string
  default     = "change-me-in-production"
  sensitive   = true
}

variable "google_client_id" {
  description = "Google OAuth client ID"
  type        = string
  default     = ""
}

variable "google_client_secret" {
  description = "Google OAuth client secret"
  type        = string
  default     = ""
  sensitive   = true
}

variable "google_redirect_uri" {
  description = "Google OAuth redirect URI. If empty, defaults to ALB callback URL."
  type        = string
  default     = ""
}

variable "common_tags" {
  description = "Additional common tags"
  type        = map(string)
  default     = {}
}

variable "alert_email" {
  description = "Email address for CloudWatch alarm notifications"
  type        = string
  default     = "divyjain07291@gmail.com"
}

variable "enable_logging_bucket" {
  description = "Enable S3 bucket for application and ALB logs"
  type        = bool
  default     = true
}

variable "enable_backups_bucket" {
  description = "Enable S3 bucket for database backups"
  type        = bool
  default     = true
}

variable "enable_assets_bucket" {
  description = "Enable S3 bucket for application assets and media"
  type        = bool
  default     = true
}

variable "s3_force_destroy" {
  description = "Allow Terraform to destroy non-empty S3 buckets (recommended only for dev)"
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "Number of days to retain logs before transitioning to Glacier"
  type        = number
  default     = 90
}

variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 30
}
