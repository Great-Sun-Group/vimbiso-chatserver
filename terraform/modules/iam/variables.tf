variable "environment" {
  description = "The deployment environment (development, production)"
  type        = string
}

variable "tags" {
  description = "Common resource tags"
  type        = map(string)
  default     = {}
}

variable "efs_file_system_arn" {
  description = "ARN of the EFS file system"
  type        = string
}

variable "app_access_point_arn" {
  description = "ARN of the app EFS access point"
  type        = string
}

variable "cloudwatch_log_group_arn" {
  description = "ARN of the CloudWatch log group"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
}

variable "account_id" {
  description = "AWS account ID"
  type        = string
}
