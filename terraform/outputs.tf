# Network Outputs
output "vpc_id" {
  description = "The ID of the VPC"
  value       = module.networking.vpc_id
}

output "private_subnet_ids" {
  description = "List of private subnet IDs"
  value       = module.networking.private_subnet_ids
}

output "public_subnet_ids" {
  description = "List of public subnet IDs"
  value       = module.networking.public_subnet_ids
}

# Load Balancer Outputs
output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = module.loadbalancer.alb_dns_name
}

# DNS Outputs
output "dns_info" {
  description = "DNS configuration information"
  value = {
    domain = {
      name = module.route53_dns.domain_name
      parent = module.route53_dns.parent_domain
      zone_id = module.route53_dns.zone_id
      nameservers = module.route53_dns.nameservers
    }
    zone_details = module.route53_dns.zone_info
    certificate = {
      arn = module.route53_cert.certificate_arn
      validation = module.route53_cert.validation_info
    }
  }
}

output "dns_instructions" {
  description = "Instructions for DNS configuration"
  value = <<-EOT
DNS Setup Instructions:
1. Add these NS records to the root zone (${module.route53_dns.parent_domain}):
   Domain: ${module.route53_dns.domain_name}
   Type: NS
   TTL: 300
   Values:
   ${jsonencode(module.route53_dns.nameservers)}

2. Wait for DNS propagation (15-30 minutes)
3. After propagation, enable create_dns_records in terraform
EOT
}

# Container Registry Output
output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = module.ecr.repository_url
}

# ECS Resources
output "ecs_cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = module.ecs.cluster_arn
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = module.ecs.cluster_name
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = module.ecs.service_name
}

output "ecs_task_definition_arn" {
  description = "ARN of the ECS task definition"
  value       = module.ecs.task_definition_arn
}

# Auto Scaling
output "autoscaling_target_min_capacity" {
  description = "Minimum capacity of the auto scaling target"
  value       = local.current_env.autoscaling.min_capacity
}

output "autoscaling_target_max_capacity" {
  description = "Maximum capacity of the auto scaling target"
  value       = local.current_env.autoscaling.max_capacity
}

# EFS Resources
output "efs_file_system_id" {
  description = "ID of the EFS file system"
  value       = module.efs.file_system_id
}

output "efs_mount_targets" {
  description = "List of mount target IDs"
  value       = module.efs.mount_target_ids
}

# CloudWatch Logs
output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = module.ecs.cloudwatch_log_group_name
}

# Service Discovery
output "service_discovery_namespace_id" {
  description = "ID of the service discovery namespace"
  value       = module.ecs.service_discovery_namespace_id
}

# Security Groups
output "alb_security_group_id" {
  description = "ID of the ALB security group"
  value       = module.networking.alb_security_group_id
}

output "ecs_tasks_security_group_id" {
  description = "ID of the ECS tasks security group"
  value       = module.networking.ecs_tasks_security_group_id
}

output "efs_security_group_id" {
  description = "ID of the EFS security group"
  value       = module.networking.efs_security_group_id
}

# New Monitoring Outputs
output "container_insights_status" {
  description = "Status of Container Insights"
  value       = module.ecs.container_insights_status
}

output "cloudwatch_dashboard_name" {
  description = "Name of the CloudWatch dashboard"
  value       = module.ecs.cloudwatch_dashboard_name
}

output "monitoring_urls" {
  description = "URLs for monitoring the application"
  value = {
    cloudwatch_dashboard = "https://${local.current_env.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${local.current_env.aws_region}#dashboards:name=${module.ecs.cloudwatch_dashboard_name}"
    container_insights  = "https://${local.current_env.aws_region}.console.aws.amazon.com/ecs/home?region=${local.current_env.aws_region}#/clusters/${module.ecs.cluster_name}/containerInsights"
    application_url    = "https://${module.route53_dns.domain_name}"
  }
}

output "health_check_url" {
  description = "URL for the application health check"
  value       = "https://${module.route53_dns.domain_name}/health/"
}
