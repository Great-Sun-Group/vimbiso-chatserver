variable "environment" {
  description = "Environment name (production or development)"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "az_count" {
  description = "Number of AZs to use"
  type        = number
  default     = 2
}

variable "container_port" {
  description = "Port exposed by the docker image"
  type        = number
  default     = 8000
}

variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}

# Environment specific defaults
locals {
  env_defaults = {
    production = {
      az_count = 2
      nat_strategy = "one_per_az"
    }
    development = {
      az_count = 2
      nat_strategy = "single"
    }
  }

  # Use environment defaults or fallback to variables
  effective_az_count = lookup(local.env_defaults[var.environment], "az_count", var.az_count)
  nat_strategy = lookup(local.env_defaults[var.environment], "nat_strategy", "single")
}
