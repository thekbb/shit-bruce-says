# Hosted Zone for the domain
resource "aws_route53_zone" "main" {
  name = var.domain_name
}

# A record for API subdomain pointing to API Gateway
resource "aws_route53_record" "api" {
  zone_id = aws_route53_zone.main.zone_id
  name    = var.api_subdomain
  type    = "A"

  alias {
    name                   = aws_apigatewayv2_domain_name.api.domain_name_configuration[0].target_domain_name
    zone_id                = aws_apigatewayv2_domain_name.api.domain_name_configuration[0].hosted_zone_id
    evaluate_target_health = false
  }
}

# Apex (root domain) to CloudFront
resource "aws_route53_record" "apex_a" {
  zone_id = aws_route53_zone.main.zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.site.domain_name
    zone_id                = "Z2FDTNDATAQYW2" # CloudFront hosted zone ID (global constant)
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "apex_aaaa" {
  zone_id = aws_route53_zone.main.zone_id
  name    = var.domain_name
  type    = "AAAA"

  alias {
    name                   = aws_cloudfront_distribution.site.domain_name
    zone_id                = "Z2FDTNDATAQYW2"
    evaluate_target_health = false
  }
}

# S3 bucket for www redirect
resource "aws_s3_bucket" "www_redirect" {
  bucket = "www-${var.domain_name}"
}

resource "aws_s3_bucket_website_configuration" "www_redirect" {
  bucket = aws_s3_bucket.www_redirect.id

  redirect_all_requests_to {
    host_name = var.domain_name
    protocol  = "https"
  }
}

resource "aws_s3_bucket_public_access_block" "www_redirect" {
  bucket = aws_s3_bucket.www_redirect.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# www → S3 redirect bucket
resource "aws_route53_record" "www_a" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "www.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_s3_bucket_website_configuration.www_redirect.website_domain
    zone_id                = aws_s3_bucket.www_redirect.hosted_zone_id
    evaluate_target_health = false
  }
}
