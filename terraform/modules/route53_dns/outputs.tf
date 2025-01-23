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

output "parent_domain" {
  description = "The parent domain where NS records are created"
  value       = var.parent_domain
}

output "zone_info" {
  description = "Zone information for cross-account DNS delegation"
  value = {
    zone_id = aws_route53_zone.app[0].zone_id
    zone_name = aws_route53_zone.app[0].name
    nameservers = aws_route53_zone.app[0].name_servers
  }
}

output "delegation_instructions" {
  description = "Instructions for cross-account DNS delegation"
  value = <<-EOT
Cross-Account DNS Delegation Instructions:

1. This hosted zone (${aws_route53_zone.app[0].name}) has been created in the current AWS account
2. To complete DNS delegation, manually add these NS records to the parent zone in its respective AWS account:

   Domain: ${var.domain_name}
   Type: NS
   TTL: 300
   Values:
   ${join("\n   ", aws_route53_zone.app[0].name_servers)}

Note: The root zone (${var.parent_domain}) exists in a different AWS account:
These NS records need to be manually added to the root zone (${var.parent_domain}) in the root AWS account.
This creates a direct delegation from the root domain to this environment's subdomain.
EOT
}
