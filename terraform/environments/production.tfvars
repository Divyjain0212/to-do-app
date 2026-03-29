environment  = "prod"
aws_region   = "ap-south-1"
project_name = "todo-capstone"

vpc_cidr                 = "10.30.0.0/16"
public_subnet_cidrs      = ["10.30.1.0/24", "10.30.2.0/24"]
private_app_subnet_cidrs = ["10.30.11.0/24", "10.30.12.0/24"]
private_db_subnet_cidrs  = ["10.30.21.0/24", "10.30.22.0/24"]
allowed_ingress_cidr     = "0.0.0.0/0"

app_instance_type    = "m7i-flex.large"
app_min_size         = 2
app_max_size         = 6
app_desired_capacity = 2

# Provide your own AMI ID per region/account
app_ami_id = "ami-05d2d839d4f73aafb"

db_instance_class = "db.t4g.small"
db_name           = "todo"
db_username       = "todoadmin"
db_password       = "Div#321@jain$123"

# Optional: set to receive CloudWatch alarm emails
alert_email = "07291divyjain@stthomasschool.co.in"

# S3 Bucket Configuration (Production - longer retention)
enable_logging_bucket = true
enable_backups_bucket = true
enable_assets_bucket  = true
log_retention_days    = 180
backup_retention_days = 30

common_tags = {
  Owner = "platform-team"
}
