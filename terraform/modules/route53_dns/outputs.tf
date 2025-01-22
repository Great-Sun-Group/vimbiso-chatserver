output "zone_id" {
  description = "The ID of the hosted zone"
  value       = var.create_dns_records ? aws_route53_zone.app[0].zone_id : null
}

output "nameservers" {
  description = "The nameservers for the hosted zone"
  value       = var.create_dns_records ? aws_route53_zone.app[0].name_servers : []
}

output "domain_name" {
  description = "The domain name"
  value       = var.domain_name
}

output "zone_info" {
  description = "Zone information for debugging DNS issues"
  value = {
    root_zone_id   = var.create_dns_records ? data.aws_route53_zone.root[0].zone_id : null
    root_zone_name = var.create_dns_records ? data.aws_route53_zone.root[0].name : null
    app_zone_id    = var.create_dns_records ? aws_route53_zone.app[0].zone_id : null
    nameservers    = var.create_dns_records ? aws_route53_zone.app[0].name_servers : []
  }
}
