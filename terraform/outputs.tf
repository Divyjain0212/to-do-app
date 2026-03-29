output "vpc_id" {
  value = module.network.vpc_id
}

output "alb_dns_name" {
  value = module.alb.alb_dns_name
}

output "app_asg_name" {
  value = module.compute.asg_name
}

output "rds_endpoint" {
  value = module.rds.db_endpoint
}

output "alerts_topic_arn" {
  value = module.monitoring.alerts_topic_arn
}

output "logs_bucket_name" {
  description = "Name of the logs S3 bucket"
  value       = module.s3.logs_bucket_name
}

output "backups_bucket_name" {
  description = "Name of the backups S3 bucket"
  value       = module.s3.backups_bucket_name
}

output "assets_bucket_name" {
  description = "Name of the assets S3 bucket"
  value       = module.s3.assets_bucket_name
}

output "assets_bucket_url" {
  description = "S3 URL for assets bucket"
  value       = module.s3.assets_bucket_url
}
