terraform {
  required_version = ">= 1.6.0"

  backend "s3" {
    bucket         = "todo-capstone-terraform-state"
    region         = "ap-south-1"
    encrypt        = true
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
}
