variable "domain_name" {
  description = "The domain name for the environment"
  type        = string
}

variable "parent_domain" {
  description = "The parent domain where NS records will be created"
  type        = string
}

variable "environment" {
  description = "The environment (development/production)"
  type        = string
}

variable "create_dns_records" {
  description = "Whether to create DNS records"
  type        = bool
  default     = true
}

variable "alb_dns_name" {
  description = "The DNS name of the ALB"
  type        = string
}

variable "alb_zone_id" {
  description = "The hosted zone ID of the ALB"
  type        = string
}

variable "health_check_id" {
  description = "ID of the health check to associate with DNS records"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
