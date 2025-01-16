# Create the hosted zone for the environment
resource "aws_route53_zone" "app" {
  count = var.create_dns_records ? 1 : 0  # Only create zone when create_dns_records is true
  name  = var.domain_name

  tags = merge(var.tags, {
    Name        = "vimbiso-pay-zone-${var.environment}"
    Environment = var.environment
  })
}

# Data source to fetch existing zone when not creating
data "aws_route53_zone" "existing" {
  count        = var.create_dns_records ? 0 : 1
  name         = var.domain_name
  private_zone = false  # Added to specifically look for public zone
}

locals {
  zone_id = var.create_dns_records ? aws_route53_zone.app[0].zone_id : data.aws_route53_zone.existing[0].zone_id
}

# Create A record for the application
resource "aws_route53_record" "app" {
  count = var.create_dns_records ? 1 : 0

  zone_id = local.zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = var.alb_dns_name
    zone_id                = var.alb_zone_id
    evaluate_target_health = true
  }
}

# Create health check for the application
resource "aws_route53_health_check" "app" {
  count = var.create_dns_records ? 1 : 0

  fqdn              = var.alb_dns_name  # Using ALB DNS name
  port              = 443
  type              = "HTTPS"
  resource_path     = var.health_check_path
  failure_threshold = "3"
  request_interval  = "30"
  regions          = ["us-east-1", "eu-west-1", "ap-southeast-1"]  # Using allowed regions

  tags = merge(var.tags, {
    Name = "vimbiso-pay-health-${var.environment}"
  })
}
