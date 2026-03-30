terraform {
  required_version = ">= 1.6.0"

  backend "s3" {
    bucket  = "todo-capstone-tfstate-288390777244"
    key     = "dev/terraform.tfstate"
    region  = "ap-south-1"
    encrypt = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.86"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile != "" ? var.aws_profile : null
}
