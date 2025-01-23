# Data source to fetch the hosted zone created by route53_dns module
data "aws_route53_zone" "zone" {
  count = var.create_dns_records ? 1 : 0
  name  = var.domain_name
  private_zone = false
}

locals {
  # Add validation for domain name format
  domain_validation = regex("^[a-zA-Z0-9][a-zA-Z0-9-]*(\\.[a-zA-Z0-9][a-zA-Z0-9-]*)*$", var.domain_name)

  # Add debug outputs for certificate validation
  debug = {
    domain_name = var.domain_name
    zone_id = var.create_dns_records ? data.aws_route53_zone.zone[0].zone_id : null
    validation_options = aws_acm_certificate.app.domain_validation_options
  }
}

# Create ACM certificate with improved configuration
resource "aws_acm_certificate" "app" {
  domain_name               = var.domain_name
  validation_method         = "DNS"
  subject_alternative_names = []  # Explicitly empty to avoid validation complexity

  tags = merge(var.tags, {
    Name        = "vimbiso-pay-cert-${var.environment}"
    Environment = var.environment
    ManagedBy   = "terraform"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Create DNS validation record with improved configuration
resource "aws_route53_record" "cert_validation" {
  count           = var.create_dns_records ? 1 : 0
  allow_overwrite = true
  name            = tolist(aws_acm_certificate.app.domain_validation_options)[0].resource_record_name
  records         = [tolist(aws_acm_certificate.app.domain_validation_options)[0].resource_record_value]
  type            = tolist(aws_acm_certificate.app.domain_validation_options)[0].resource_record_type
  zone_id         = data.aws_route53_zone.zone[0].zone_id
  ttl             = 600  # Further increased TTL for validation records

  depends_on = [aws_acm_certificate.app]
}

# Validate the certificate with improved configuration
resource "aws_acm_certificate_validation" "app" {
  count                   = var.create_dns_records ? 1 : 0
  certificate_arn         = aws_acm_certificate.app.arn
  validation_record_fqdns = [aws_route53_record.cert_validation[0].fqdn]

  timeouts {
    create = "60m"  # Increased timeout for validation
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [aws_route53_record.cert_validation]
}

# Output debug information
output "certificate_validation_info" {
  value = {
    certificate_arn = aws_acm_certificate.app.arn
    domain_name    = var.domain_name
    zone_info      = local.debug
    validation_fqdn = var.create_dns_records ? aws_route53_record.cert_validation[0].fqdn : null
  }
  description = "Debug information for certificate validation"
}
