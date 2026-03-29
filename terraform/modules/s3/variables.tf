variable "project_name" {
  description = "Project identifier"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
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

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}
