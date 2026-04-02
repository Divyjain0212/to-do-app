variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "ami_id" {
  type = string
}

variable "instance_type" {
  type = string
}

variable "private_app_subnet_ids" {
  type = list(string)
}

variable "app_security_group_id" {
  type = string
}

variable "target_group_arn" {
  type = string
}

variable "min_size" {
  type = number
}

variable "max_size" {
  type = number
}

variable "desired_capacity" {
  type = number
}

variable "db_host" {
  type = string
}

variable "db_name" {
  type = string
}

variable "db_username" {
  type = string
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "app_secret_key" {
  type      = string
  sensitive = true
}

variable "google_client_id" {
  type    = string
  default = ""
}

variable "google_client_secret" {
  type      = string
  default   = ""
  sensitive = true
}

variable "google_redirect_uri" {
  type    = string
  default = ""
}

variable "docker_image_uri" {
  type    = string
  default = ""
}

variable "config_s3_prefix" {
  description = "S3 key prefix where runtime config files are uploaded"
  type        = string
  default     = "runtime/current"
}

variable "assets_bucket_name" {
  description = "Name of S3 bucket for application assets"
  type        = string
  default     = ""
}

variable "ssh_public_key" {
  description = "SSH public key for EC2 instances"
  type        = string
  default     = ""
}

variable "tags" {
  type = map(string)
}
