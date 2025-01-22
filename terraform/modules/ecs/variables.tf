variable "environment" {
  description = "The deployment environment (development, production)"
  type        = string
}

variable "tags" {
  description = "Common resource tags"
  type        = map(string)
  default     = {}
}

# Network Configuration
variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs"
  type        = list(string)
}

variable "ecs_tasks_security_group_id" {
  description = "Security group ID for ECS tasks"
  type        = string
}

# Load Balancer Configuration
variable "target_group_arn" {
  description = "ARN of the ALB target group"
  type        = string
}

variable "alb_arn" {
  description = "ARN of the Application Load Balancer"
  type        = string
}

# IAM Configuration
variable "execution_role_arn" {
  description = "ARN of the ECS task execution role"
  type        = string
}

variable "task_role_arn" {
  description = "ARN of the ECS task role"
  type        = string
}

# Container Configuration
variable "docker_image" {
  description = "Docker image to deploy"
  type        = string
}

variable "app_port" {
  description = "Port exposed by the application container"
  type        = number
  default     = 8000
}

variable "redis_state_port" {
  description = "Port exposed by the Redis state container"
  type        = number
  default     = 6379  # Changed from 6380 since it's the only Redis now
}

# AWS Account Configuration
variable "aws_account_id" {
  description = "AWS Account ID"
  type        = string
}

variable "aws_region" {
  description = "AWS Region"
  type        = string
}

# Task Resource Configuration
variable "task_cpu" {
  description = "CPU units for the task"
  type        = number
  validation {
    condition     = contains([256, 512, 1024, 2048, 4096], var.task_cpu)
    error_message = "Task CPU must be one of: 256, 512, 1024, 2048, 4096"
  }
}

variable "task_memory" {
  description = "Memory (MiB) for the task"
  type        = number
  validation {
    condition     = contains([512, 1024, 2048, 3072, 4096, 5120, 6144, 7168, 8192], var.task_memory)
    error_message = "Task memory must be one of: 512, 1024, 2048, 3072, 4096, 5120, 6144, 7168, 8192"
  }
}

# EFS Configuration
variable "efs_file_system_id" {
  description = "ID of the EFS file system"
  type        = string
}

variable "app_access_point_id" {
  description = "ID of the app EFS access point"
  type        = string
}

variable "efs_mount_targets" {
  description = "List of EFS mount target IDs to depend on"
  type        = list(string)
}

# Auto Scaling Configuration
variable "min_capacity" {
  description = "Minimum number of tasks"
  type        = number
  default     = 1
  validation {
    condition     = var.min_capacity >= 1
    error_message = "Minimum capacity must be at least 1"
  }
}

variable "max_capacity" {
  description = "Maximum number of tasks"
  type        = number
  default     = 4
  validation {
    condition     = var.max_capacity >= 1
    error_message = "Maximum capacity must be at least 1"
  }
}

variable "cpu_threshold" {
  description = "CPU utilization threshold for scaling"
  type        = number
  default     = 80
  validation {
    condition     = var.cpu_threshold > 0 && var.cpu_threshold <= 100
    error_message = "CPU threshold must be between 1 and 100"
  }
}

variable "memory_threshold" {
  description = "Memory utilization threshold for scaling"
  type        = number
  default     = 80
  validation {
    condition     = var.memory_threshold > 0 && var.memory_threshold <= 100
    error_message = "Memory threshold must be between 1 and 100"
  }
}

# Environment Variables
variable "django_env" {
  description = "Django environment configuration"
  type = object({
    django_secret                         = string
    debug                                = bool
    mycredex_app_url                     = string
    client_api_key                       = string
    whatsapp_api_url                     = string
    whatsapp_access_token                = string
    whatsapp_phone_number_id             = string
    whatsapp_business_id                 = string
  })
  sensitive = true
}

variable "allowed_hosts" {
  description = "List of allowed hosts for Django"
  type        = string
  default     = "*"  # Allow all hosts by default, relying on security groups and WAF for protection
}

# CloudWatch Configuration
variable "log_retention_days" {
  description = "Number of days to retain CloudWatch logs"
  type        = number
  default     = 30
  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_days)
    error_message = "Log retention days must be one of: 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653"
  }
}

# Service Discovery Configuration
variable "service_discovery_ttl" {
  description = "TTL for service discovery DNS records"
  type        = number
  default     = 10
  validation {
    condition     = var.service_discovery_ttl >= 0 && var.service_discovery_ttl <= 60
    error_message = "Service discovery TTL must be between 0 and 60 seconds"
  }
}
