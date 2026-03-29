variable "project_name" {
  type = string
}

variable "environment" {
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

variable "db_instance_class" {
  type = string
}

variable "private_db_subnet_ids" {
  type = list(string)
}

variable "db_security_group_id" {
  type = string
}

variable "backup_retention_days" {
  description = "Number of days to retain automated backups"
  type        = number
  default     = 7
}

variable "backups_bucket_name" {
  description = "Name of S3 bucket for backup export"
  type        = string
  default     = ""
}

variable "enable_backup_export" {
  description = "Enable IAM resources for RDS export to S3"
  type        = bool
  default     = true
}

variable "tags" {
  type = map(string)
}
