output "api_base_url" {
  description = "Invoke URL for the API Gateway HTTP API"
  value       = trim(aws_apigatewayv2_stage.default.invoke_url, "/")
}

output "site_url" {
  description = "CloudFront URL for static site"
  value       = "https://${aws_cloudfront_distribution.site.domain_name}"
}

output "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution (for cache invalidations)"
  value       = aws_cloudfront_distribution.site.id
}
