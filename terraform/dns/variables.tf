variable "environment" {
  description = "Environment name (production or development)"
  type        = string
}

variable "domain_name" {
  description = "Domain name for the application (e.g., vimbiso-chatserver.vimbisopay.africa)"
  type        = string
}

variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}

# ALB inputs
variable "alb_arn" {
  description = "ARN of the application load balancer"
  type        = string
}

variable "alb_dns_name" {
  description = "DNS name of the application load balancer"
  type        = string
}

variable "alb_zone_id" {
  description = "Route53 zone ID of the application load balancer"
  type        = string
}

variable "target_group_arn" {
  description = "ARN of the ALB target group"
  type        = string
}

variable "enable_https" {
  description = "Whether to enable HTTPS listener and certificate validation. Set to false for initial deployment, true after DNS is configured."
  type        = bool
  default     = false
}

# Validation
locals {
  valid_environments = ["production", "development"]

  # Validate environment
  validate_environment = (
    contains(local.valid_environments, var.environment)
    ? null
    : file("ERROR: environment must be either 'production' or 'development'")
  )

  # Validate domain format
  validate_domain = (
    can(regex("^[a-zA-Z0-9][a-zA-Z0-9-]*(\\.[a-zA-Z0-9][a-zA-Z0-9-]*)*$", var.domain_name))
    ? null
    : file("ERROR: invalid domain name format")
  )
}
