resource "aws_db_subnet_group" "this" {
  name       = "${var.project_name}-${var.environment}-db-subnet-group"
  subnet_ids = var.private_db_subnet_ids

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-db-subnet-group"
  })
}

# IAM role for RDS enhanced monitoring and S3 export
data "aws_iam_policy_document" "rds_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["monitoring.rds.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "rds_monitoring" {
  name               = "${var.project_name}-${var.environment}-rds-monitoring"
  assume_role_policy = data.aws_iam_policy_document.rds_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# IAM role for RDS export to S3
data "aws_iam_policy_document" "rds_s3_export" {
  count = var.enable_backup_export ? 1 : 0

  statement {
    actions = [
      "s3:PutObject*",
      "s3:GetObject*",
      "s3:DeleteObject*",
      "s3:ListBucket"
    ]
    resources = [
      "arn:aws:s3:::${var.backups_bucket_name}",
      "arn:aws:s3:::${var.backups_bucket_name}/*"
    ]
  }
}

resource "aws_iam_role" "rds_s3_export" {
  count = var.enable_backup_export ? 1 : 0
  name  = "${var.project_name}-${var.environment}-rds-s3-export"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "export.rds.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "rds_s3_export" {
  count  = var.enable_backup_export ? 1 : 0
  name   = "${var.project_name}-${var.environment}-rds-s3-export"
  role   = aws_iam_role.rds_s3_export[0].id
  policy = data.aws_iam_policy_document.rds_s3_export[0].json
}

resource "aws_db_parameter_group" "mysql" {
  name   = "${var.project_name}-${var.environment}-mysql-params"
  family = "mysql8.0"

  parameter {
    name  = "max_connections"
    value = "250"
  }

  parameter {
    name  = "innodb_buffer_pool_size"
    value = "268435456"
  }

  tags = var.tags
}

resource "aws_db_instance" "this" {
  identifier                 = "${var.project_name}-${var.environment}-mysql"
  allocated_storage          = 20
  max_allocated_storage      = 100
  storage_type               = "gp3"
  engine                     = "mysql"
  engine_version             = "8.0"
  instance_class             = var.db_instance_class
  db_name                    = var.db_name
  username                   = var.db_username
  password                   = var.db_password
  db_subnet_group_name       = aws_db_subnet_group.this.name
  vpc_security_group_ids     = [var.db_security_group_id]
  parameter_group_name       = aws_db_parameter_group.mysql.name
  skip_final_snapshot        = true
  deletion_protection        = false
  backup_retention_period    = var.backup_retention_days
  backup_window              = "03:00-04:00"
  maintenance_window         = "Sun:04:30-Sun:05:30"
  multi_az                   = false
  publicly_accessible        = false
  auto_minor_version_upgrade = true

  # Enhanced Monitoring
  enabled_cloudwatch_logs_exports = ["error", "general", "slowquery"]
  monitoring_interval             = 60
  monitoring_role_arn             = aws_iam_role.rds_monitoring.arn

  # Enable automated backup export
  copy_tags_to_snapshot = true

  tags = var.tags
}
