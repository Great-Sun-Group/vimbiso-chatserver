variable "environment" {
  description = "The deployment environment (development, production)"
  type        = string
}

variable "domain_name" {
  description = "Domain name for the certificate"
  type        = string
}

variable "tags" {
  description = "Common resource tags"
  type        = map(string)
  default     = {}
}

variable "create_dns_records" {
  description = "Whether to create DNS records for certificate validation. Set to false for initial deployment before NS records are configured, then set to true after NS records are in place."
  type        = bool
  default     = false  # Default to false for safety
}
