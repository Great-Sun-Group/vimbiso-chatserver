# Required Environment Variables
variable "environment" {
  description = "The deployment environment (development, production)"
  type        = string

  validation {
    condition     = contains(["production", "development"], var.environment)
    error_message = "Environment must be one of: production, development"
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

variable "debug" {
  description = "Django debug mode"
  type        = bool
  default     = false
}

variable "mycredex_app_url" {
  description = "URL for the VimbisoPay WhatsApp Chatbot"
  type        = string
}

# WhatsApp Integration Variables
variable "client_api_key" {
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

variable "whatsapp_business_id" {
  description = "WhatsApp business ID"
  type        = string
  sensitive   = true
}

# Infrastructure Configuration
variable "enable_https" {
  description = "Whether to enable HTTPS listener and certificate validation. Set to false for initial deployment, true after DNS is configured."
  type        = bool
  default     = false
}
