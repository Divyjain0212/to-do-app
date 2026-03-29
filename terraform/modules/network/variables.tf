variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "vpc_cidr" {
  type = string
}

variable "azs" {
  type = list(string)
}

variable "public_subnet_cidrs" {
  type = list(string)
}

variable "private_app_subnet_cidrs" {
  type = list(string)
}

variable "private_db_subnet_cidrs" {
  type = list(string)
}

variable "allowed_ingress_cidr" {
  type = string
}

variable "tags" {
  type = map(string)
}
