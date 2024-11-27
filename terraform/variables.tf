# Required Environment Variables
variable "environment" {
  description = "The deployment environment (staging, production)"
  type        = string

  validation {
    condition     = contains(["production", "staging"], var.environment)
    error_message = "Environment must be one of: production, staging"
  }
}

# Application Configuration
variable "docker_image" {
  description = "The full Docker image to deploy (including repository and tag)"
  type        = string
}

# Django Environment Variables
variable "django_secret" {
  description = "Django secret key"
  type        = string
  sensitive   = true
}

variable "mycredex_app_url" {
  description = "URL for the Credex Core API"
  type        = string
}

# WhatsApp Integration Variables
variable "whatsapp_bot_api_key" {
  description = "API key for WhatsApp bot"
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
  sensitive   = true
}

# Neo4j License
variable "neo4j_enterprise_license" {
  description = "Neo4j Enterprise Edition license key"
  type        = string
  sensitive   = true
}
