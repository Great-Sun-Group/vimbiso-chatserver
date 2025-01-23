# Environment configuration
locals {
  environments = {
    production = {
      domain_name     = "vimbiso-chatserver.vimbisopay.africa"
      vpc_cidr        = "10.0.0.0/16"
      az_count        = 2
      container_port  = 8000
      task_cpu        = 1024
      task_memory     = 2048
      min_capacity    = 1
      max_capacity    = 4
    }
    development = {
      domain_name     = "dev-vimbiso-chatserver.dailycredcoin.com"
      vpc_cidr        = "10.1.0.0/16"
      az_count        = 2
      container_port  = 8000
      task_cpu        = 1024
      task_memory     = 2048
      min_capacity    = 1
      max_capacity    = 2
    }
  }

  current_env = local.environments[var.environment]

  common_tags = {
    Environment = var.environment
    Project     = "vimbiso-pay"
    ManagedBy   = "terraform"
  }
}

# Base infrastructure module
module "base" {
  source = "./base"

  environment    = var.environment
  vpc_cidr      = local.current_env.vpc_cidr
  az_count      = local.current_env.az_count
  container_port = local.current_env.container_port
  tags          = local.common_tags
}

# DNS and HTTPS module
module "dns" {
  source = "./dns"

  environment      = var.environment
  domain_name     = local.current_env.domain_name
  alb_arn         = module.base.alb_arn
  alb_dns_name    = module.base.alb_dns_name
  alb_zone_id     = module.base.alb_zone_id
  target_group_arn = module.base.target_group_arn
  tags            = local.common_tags

  depends_on = [module.base]
}

# Application module
module "app" {
  source = "./app"

  environment    = var.environment
  task_cpu      = local.current_env.task_cpu
  task_memory   = local.current_env.task_memory
  min_capacity  = local.current_env.min_capacity
  max_capacity  = local.current_env.max_capacity
  docker_image  = var.docker_image
  tags          = local.common_tags

  # Network configuration
  private_subnet_ids    = module.base.private_subnet_ids
  ecs_security_group_id = module.base.ecs_security_group_id
  target_group_arn      = module.base.target_group_arn

  # Application configuration
  django_secret            = var.django_secret
  mycredex_app_url        = var.mycredex_app_url
  client_api_key          = var.client_api_key
  whatsapp_api_url        = var.whatsapp_api_url
  whatsapp_access_token   = var.whatsapp_access_token
  whatsapp_phone_number_id = var.whatsapp_phone_number_id
  whatsapp_business_id    = var.whatsapp_business_id

  depends_on = [module.base, module.dns]
}

# Variables
variable "environment" {
  description = "Environment name (production or development)"
  type        = string
  validation {
    condition     = contains(["production", "development"], var.environment)
    error_message = "Environment must be either 'production' or 'development'."
  }
}

variable "docker_image" {
  description = "Docker image to deploy"
  type        = string
}

variable "django_secret" {
  description = "Django secret key"
  type        = string
  sensitive   = true
}

variable "mycredex_app_url" {
  description = "MyCredex app URL"
  type        = string
}

variable "client_api_key" {
  description = "Client API key"
  type        = string
  sensitive   = true
}

variable "whatsapp_api_url" {
  description = "WhatsApp API URL"
  type        = string
}

variable "whatsapp_access_token" {
  description = "WhatsApp access token"
  type        = string
  sensitive   = true
}

variable "whatsapp_phone_number_id" {
  description = "WhatsApp phone number ID"
  type        = string
}

variable "whatsapp_business_id" {
  description = "WhatsApp business ID"
  type        = string
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
