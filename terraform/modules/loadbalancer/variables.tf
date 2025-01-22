variable "environment" {
  description = "The deployment environment (development, production)"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs"
  type        = list(string)
}

variable "alb_security_group_id" {
  description = "Security group ID for ALB"
  type        = string
}

variable "certificate_arn" {
  description = "ARN of ACM certificate"
  type        = string
}

variable "health_check_path" {
  description = "Path for health checks"
  type        = string
  default     = "/health/"
}

variable "health_check_port" {
  description = "Port for health checks"
  type        = number
  default     = 8000
}

variable "deregistration_delay" {
  description = "Amount time to wait before deregistering targets"
  type        = number
  default     = 60
}

variable "tags" {
  description = "Common resource tags"
  type        = map(string)
  default     = {}
}

variable "enable_https" {
  description = "Whether to enable HTTPS listener. Set to false for initial deployment before certificate is validated."
  type        = bool
  default     = false
}
