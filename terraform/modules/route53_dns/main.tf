# Create the hosted zone for the environment
resource "aws_route53_zone" "app" {
  count = 1
  name  = var.domain_name

  tags = merge(var.tags, {
    Name = "vimbiso-pay-zone-${var.environment}"
  })
}

# Create simple A record for the application
resource "aws_route53_record" "app" {
  count = var.create_dns_records ? 1 : 0

  zone_id = aws_route53_zone.app[0].zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = var.alb_dns_name
    zone_id                = var.alb_zone_id
    evaluate_target_health = true
  }
}
