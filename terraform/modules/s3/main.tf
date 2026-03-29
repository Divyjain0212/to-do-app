# S3 Bucket for Application and ALB Logs
resource "aws_s3_bucket" "logs" {
  count  = var.enable_logging_bucket ? 1 : 0
  bucket = "${var.project_name}-${var.environment}-logs-${data.aws_caller_identity.current.account_id}"

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-logs"
    }
  )
}

resource "aws_s3_bucket_versioning" "logs" {
  count  = var.enable_logging_bucket ? 1 : 0
  bucket = aws_s3_bucket.logs[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  count  = var.enable_logging_bucket ? 1 : 0
  bucket = aws_s3_bucket.logs[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  count  = var.enable_logging_bucket ? 1 : 0
  bucket = aws_s3_bucket.logs[0].id

  rule {
    id     = "transition_to_glacier"
    status = "Enabled"

    filter {}

    transition {
      days          = var.log_retention_days
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}

resource "aws_s3_bucket_public_access_block" "logs" {
  count  = var.enable_logging_bucket ? 1 : 0
  bucket = aws_s3_bucket.logs[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket for Database Backups
resource "aws_s3_bucket" "backups" {
  count  = var.enable_backups_bucket ? 1 : 0
  bucket = "${var.project_name}-${var.environment}-backups-${data.aws_caller_identity.current.account_id}"

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-backups"
    }
  )
}

resource "aws_s3_bucket_versioning" "backups" {
  count  = var.enable_backups_bucket ? 1 : 0
  bucket = aws_s3_bucket.backups[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  count  = var.enable_backups_bucket ? 1 : 0
  bucket = aws_s3_bucket.backups[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  count  = var.enable_backups_bucket ? 1 : 0
  bucket = aws_s3_bucket.backups[0].id

  rule {
    id     = "transition_old_backups"
    status = "Enabled"

    filter {}

    transition {
      days          = var.backup_retention_days
      storage_class = "GLACIER"
    }

    expiration {
      days = 90
    }
  }
}

resource "aws_s3_bucket_public_access_block" "backups" {
  count  = var.enable_backups_bucket ? 1 : 0
  bucket = aws_s3_bucket.backups[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket for Application Assets and Media
resource "aws_s3_bucket" "assets" {
  count  = var.enable_assets_bucket ? 1 : 0
  bucket = "${var.project_name}-${var.environment}-assets-${data.aws_caller_identity.current.account_id}"

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-assets"
    }
  )
}

resource "aws_s3_bucket_versioning" "assets" {
  count  = var.enable_assets_bucket ? 1 : 0
  bucket = aws_s3_bucket.assets[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "assets" {
  count  = var.enable_assets_bucket ? 1 : 0
  bucket = aws_s3_bucket.assets[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "assets" {
  count  = var.enable_assets_bucket ? 1 : 0
  bucket = aws_s3_bucket.assets[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CORS Configuration for Assets bucket
resource "aws_s3_bucket_cors_configuration" "assets" {
  count  = var.enable_assets_bucket ? 1 : 0
  bucket = aws_s3_bucket.assets[0].id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
  }
}

# Data source for AWS account ID
data "aws_caller_identity" "current" {}
