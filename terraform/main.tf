data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 2)

  # Read SSH public key from ansible folder if it exists
  ssh_public_key = try(file("${path.root}/../ansible/linux-key.pub"), "")

  oauth_redirect_uri = var.google_redirect_uri != "" ? var.google_redirect_uri : "http://${module.alb.alb_dns_name}/auth/google/callback"

  tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    },
    var.common_tags
  )
}

module "network" {
  source = "./modules/network"

  project_name             = var.project_name
  environment              = var.environment
  vpc_cidr                 = var.vpc_cidr
  azs                      = local.azs
  public_subnet_cidrs      = var.public_subnet_cidrs
  private_app_subnet_cidrs = var.private_app_subnet_cidrs
  private_db_subnet_cidrs  = var.private_db_subnet_cidrs
  allowed_ingress_cidr     = var.allowed_ingress_cidr
  tags                     = local.tags
}

module "alb" {
  source = "./modules/alb"

  project_name       = var.project_name
  environment        = var.environment
  vpc_id             = module.network.vpc_id
  public_subnet_ids  = module.network.public_subnet_ids
  alb_security_group = module.network.alb_security_group_id
  health_check_path  = "/health"
  tags               = local.tags
}

module "compute" {
  source = "./modules/compute"

  project_name           = var.project_name
  environment            = var.environment
  ami_id                 = var.app_ami_id
  instance_type          = var.app_instance_type
  private_app_subnet_ids = module.network.private_app_subnet_ids
  app_security_group_id  = module.network.app_security_group_id
  target_group_arn       = module.alb.target_group_arn
  min_size               = var.app_min_size
  max_size               = var.app_max_size
  desired_capacity       = var.app_desired_capacity
  db_host                = module.rds.db_endpoint
  db_name                = var.db_name
  db_username            = var.db_username
  db_password            = var.db_password
  app_secret_key         = var.app_secret_key
  google_client_id       = var.google_client_id
  google_client_secret   = var.google_client_secret
  google_redirect_uri    = local.oauth_redirect_uri
  docker_image_uri       = var.docker_image_uri
  config_s3_prefix       = var.config_s3_prefix
  assets_bucket_name     = module.s3.assets_bucket_name
  ssh_public_key         = local.ssh_public_key
  tags                   = local.tags
}

module "rds" {
  source = "./modules/rds"

  project_name          = var.project_name
  environment           = var.environment
  db_name               = var.db_name
  db_username           = var.db_username
  db_password           = var.db_password
  db_instance_class     = var.db_instance_class
  private_db_subnet_ids = module.network.private_db_subnet_ids
  db_security_group_id  = module.network.db_security_group_id
  backups_bucket_name   = module.s3.backups_bucket_name
  backup_retention_days = var.backup_retention_days
  enable_backup_export  = var.enable_backups_bucket
  tags                  = local.tags
}

module "monitoring" {
  source = "./modules/monitoring"

  project_name            = var.project_name
  environment             = var.environment
  aws_region              = var.aws_region
  alert_email             = var.alert_email
  asg_name                = module.compute.asg_name
  alb_arn_suffix          = module.alb.alb_arn_suffix
  target_group_arn_suffix = module.alb.target_group_arn_suffix
  db_instance_identifier  = module.rds.db_identifier
}

module "s3" {
  source = "./modules/s3"

  project_name          = var.project_name
  environment           = var.environment
  enable_logging_bucket = var.enable_logging_bucket
  enable_backups_bucket = var.enable_backups_bucket
  enable_assets_bucket  = var.enable_assets_bucket
  force_destroy         = var.s3_force_destroy
  log_retention_days    = var.log_retention_days
  backup_retention_days = var.backup_retention_days
  tags                  = local.tags
}
