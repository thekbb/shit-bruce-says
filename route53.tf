# Hosted Zone for the domain
resource "aws_route53_zone" "main" {
  name = var.domain_name
}

output "route53_nameservers" {
  description = "Route53 NS records to set at the registrar (DreamHost)"
  value       = aws_route53_zone.main.name_servers
}
