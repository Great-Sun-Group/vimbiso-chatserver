output "certificate_arn" {
  description = "The ARN of the certificate"
  value       = aws_acm_certificate.app.arn
}

output "domain_name" {
  description = "The domain name for which the certificate was issued"
  value       = var.domain_name
}

output "validation_info" {
  description = "Certificate validation information for debugging"
  value = {
    zone_id = var.create_dns_records ? data.aws_route53_zone.root[0].zone_id : null
    zone_name = var.create_dns_records ? data.aws_route53_zone.root[0].name : null
    validation_record_name = var.create_dns_records ? aws_route53_record.cert_validation[0].name : null
    validation_record_type = var.create_dns_records ? aws_route53_record.cert_validation[0].type : null
    validation_record_ttl = var.create_dns_records ? aws_route53_record.cert_validation[0].ttl : null
    validation_status = var.create_dns_records ? "Validation records created" : "Validation records disabled"
  }
}
