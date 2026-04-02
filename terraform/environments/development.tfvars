environment  = "dev"
aws_region   = "ap-south-1"
project_name = "todo-capstone"

vpc_cidr                 = "10.20.0.0/16"
public_subnet_cidrs      = ["10.20.1.0/24", "10.20.2.0/24"]
private_app_subnet_cidrs = ["10.20.11.0/24", "10.20.12.0/24"]
private_db_subnet_cidrs  = ["10.20.21.0/24", "10.20.22.0/24"]
allowed_ingress_cidr     = "0.0.0.0/0"

app_instance_type    = "t3.micro"
app_min_size         = 1
app_max_size         = 2
app_desired_capacity = 1

# Provide your own AMI ID per region/account
app_ami_id = "ami-05d2d839d4f73aafb"

db_instance_class = "db.t4g.micro"
db_name           = "todo_dev"
db_username       = "todoadmin"
db_password       = "div#321jain"
google_client_id  = "863075274301-c04a44e8dbbkuaej1skj2n4j8igaoc5p.apps.googleusercontent.com"
google_client_secret = "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"
google_redirect_uri  = "http://todo-app.divyjain.in/auth/google/callback"

# Optional: set to receive CloudWatch alarm emails
alert_email = "divyjain07291@gmail.com"

# S3 Bucket Configuration
enable_logging_bucket = true
enable_backups_bucket = true
enable_assets_bucket  = true
s3_force_destroy      = true
log_retention_days    = 90
backup_retention_days = 7

common_tags = {
  Owner = "platform-team"
}
