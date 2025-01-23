# DNS Outputs
output "domain_name" {
  description = "The domain name for the environment"
  value       = module.dns.domain_name
}

output "route53_nameservers" {
  description = "The nameservers for the Route53 zone"
  value       = module.dns.nameservers
}

output "zone_id" {
  description = "The Route53 zone ID"
  value       = module.dns.zone_id
}

# Infrastructure Outputs
output "vpc_id" {
  description = "The ID of the VPC"
  value       = module.base.vpc_id
}

output "alb_dns_name" {
  description = "The DNS name of the ALB"
  value       = module.base.alb_dns_name
}

output "ecs_cluster_name" {
  description = "The name of the ECS cluster"
  value       = module.base.ecs_cluster_name
}

output "ecs_cluster_arn" {
  description = "The ARN of the ECS cluster"
  value       = module.base.ecs_cluster_arn
}

output "target_group_arn" {
  description = "The ARN of the target group"
  value       = module.base.target_group_arn
}

# Certificate Outputs
output "certificate_arn" {
  description = "The ARN of the ACM certificate"
  value       = module.dns.certificate_arn
}

# Environment Info
output "environment" {
  description = "The current environment"
  value       = var.environment
}

output "aws_region" {
  description = "The AWS region"
  value       = data.aws_region.current.name
}

output "account_id" {
  description = "The AWS account ID"
  value       = data.aws_caller_identity.current.account_id
}
