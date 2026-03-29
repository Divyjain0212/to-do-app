output "logs_bucket_name" {
  description = "Name of the logs S3 bucket"
  value       = try(aws_s3_bucket.logs[0].id, null)
}

output "logs_bucket_arn" {
  description = "ARN of the logs S3 bucket"
  value       = try(aws_s3_bucket.logs[0].arn, null)
}

output "backups_bucket_name" {
  description = "Name of the backups S3 bucket"
  value       = try(aws_s3_bucket.backups[0].id, null)
}

output "backups_bucket_arn" {
  description = "ARN of the backups S3 bucket"
  value       = try(aws_s3_bucket.backups[0].arn, null)
}

output "assets_bucket_name" {
  description = "Name of the assets S3 bucket"
  value       = try(aws_s3_bucket.assets[0].id, null)
}

output "assets_bucket_arn" {
  description = "ARN of the assets S3 bucket"
  value       = try(aws_s3_bucket.assets[0].arn, null)
}

output "assets_bucket_url" {
  description = "URL of the assets S3 bucket"
  value       = var.enable_assets_bucket ? "s3://${aws_s3_bucket.assets[0].id}" : null
}
