variable "environment" {
  description = "Environment name (production or development)"
  type        = string
}

variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}

# Task Configuration
variable "task_cpu" {
  description = "The number of cpu units to reserve for the container"
  type        = number
  default     = 1024
}

variable "task_memory" {
  description = "The amount (in MiB) of memory to reserve for the container"
  type        = number
  default     = 2048
}

# Scaling Configuration
variable "min_capacity" {
  description = "Minimum number of tasks to run"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum number of tasks to run"
  type        = number
  default     = 4
}

# Network Configuration
variable "private_subnet_ids" {
  description = "List of private subnet IDs for ECS tasks"
  type        = list(string)
}

variable "ecs_security_group_id" {
  description = "Security group ID for ECS tasks"
  type        = string
}

variable "target_group_arn" {
  description = "ARN of the ALB target group"
  type        = string
}

# Application Configuration
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
