output "certificate_arn" {
  description = "The ARN of the certificate"
  value       = try(data.aws_acm_certificate.app[0].arn, null)
}

output "domain_name" {
  description = "The domain name for which the certificate was issued"
  value       = var.domain_name
}

output "validation_info" {
  description = "Certificate validation information for debugging"
  value = local.debug
}
