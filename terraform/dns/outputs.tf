output "zone_id" {
  description = "The ID of the Route53 zone"
  value       = aws_route53_zone.main.id
}

output "zone_name" {
  description = "The name of the Route53 zone"
  value       = aws_route53_zone.main.name
}

output "nameservers" {
  description = "The nameservers for the Route53 zone"
  value       = aws_route53_zone.main.name_servers
}

output "certificate_arn" {
  description = "The ARN of the validated ACM certificate"
  value       = var.enable_https ? aws_acm_certificate_validation.main[0].certificate_arn : null
}

output "domain_name" {
  description = "The domain name"
  value       = var.domain_name
}

output "https_listener_arn" {
  description = "The ARN of the HTTPS listener"
  value       = var.enable_https ? aws_lb_listener.https[0].arn : null
}
