output "api_base_url" {
  description = "Custom domain URL for the API Gateway HTTP API"
  value       = "https://${aws_apigatewayv2_domain_name.api.domain_name}"
}

output "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution (for cache invalidations)"
  value       = aws_cloudfront_distribution.site.id
}

output "cloudfront_url" {
  description = "CloudFront distribution URL (for debugging)"
  value       = "https://${aws_cloudfront_distribution.site.domain_name}"
}

output "route53_nameservers" {
  description = "Route53 NS records to set at the registrar (DreamHost)"
  value       = aws_route53_zone.main.name_servers
}

output "site_url" {
  description = "Custom domain URL for the website"
  value       = "https://${var.domain_name}"
}

output "github_terraform_plan_role_arn" {
  description = "ARN for GitHub Actions Terraform Plan role (read-only)"
  value       = aws_iam_role.github_terraform_plan.arn
}

output "github_terraform_apply_role_arn" {
  description = "ARN for GitHub Actions Terraform Apply role (read-write)"
  value       = aws_iam_role.github_terraform_apply.arn
}
