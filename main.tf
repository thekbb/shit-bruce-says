locals {
  # Render web/index.html.tpl with the API custom domain base URL
  index_html = templatefile("${path.module}/web/index.html.tpl", {
    api_base_url = "https://${aws_apigatewayv2_domain_name.api.domain_name}"
  })

  name = "bruce-quotes"
}

resource "aws_dynamodb_table" "quotes" {
  name         = var.table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }
}

resource "aws_iam_role" "lambda_exec" {
  name = "${local.name}-lambda-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# Minimal DDB access (PutItem, Query). Add /index/* if you later use GSIs.
resource "aws_iam_policy" "ddb_access" {
  name        = "${local.name}-ddb-access"
  description = "Allow Lambda to access DynamoDB table"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:PutItem", "dynamodb:Query"]
      Resource = aws_dynamodb_table.quotes.arn
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ddb_to_lambda" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.ddb_access.arn
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda"
  output_path = "${path.module}/.dist/lambda.zip"

  excludes = [
    "*.pyc",
    ".aws-sam",
    ".DS_Store",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "dev_*",
    "pyproject.toml",
    "template.yaml",
    "tests",
    "uv.lock",
  ]
}

resource "aws_lambda_function" "api" {
  function_name = "${local.name}-api"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "app.handler"
  runtime       = "python3.12"
  architectures = ["arm64"]

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  reserved_concurrent_executions = 25

  environment {
    variables = {
      TABLE_NAME   = aws_dynamodb_table.quotes.name
      ALLOW_ORIGIN = var.allow_origin
    }
  }
}

resource "aws_apigatewayv2_api" "http_api" {
  name          = "${local.name}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins  = [var.allow_origin] # e.g., https://shitbrucesays.co.uk (prod) or * (dev)
    allow_methods  = ["GET", "POST", "OPTIONS"]
    allow_headers  = ["content-type"]
    expose_headers = ["content-type"]
    max_age        = 3600
  }
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
}

# GET route (no throttling)
resource "aws_apigatewayv2_route" "get_quotes" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /quotes"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_route" "post_quotes" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /quotes"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# OPTIONS route (for CORS, no throttling)
resource "aws_apigatewayv2_route" "options_quotes" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "OPTIONS /quotes"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true

}

resource "aws_lambda_permission" "api_invoke" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}

resource "aws_apigatewayv2_domain_name" "api" {
  domain_name = "${var.api_subdomain}.${var.domain_name}"

  domain_name_configuration {
    certificate_arn = aws_acm_certificate_validation.api.certificate_arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }
}

resource "aws_apigatewayv2_api_mapping" "api" {
  api_id      = aws_apigatewayv2_api.http_api.id
  domain_name = aws_apigatewayv2_domain_name.api.id
  stage       = aws_apigatewayv2_stage.default.name
}

resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "site" {
  bucket = "${local.name}-site-${random_id.suffix.hex}"
}

resource "aws_s3_bucket_ownership_controls" "site" {
  bucket = aws_s3_bucket.site.id
  rule { object_ownership = "BucketOwnerEnforced" }
}

resource "aws_s3_bucket_public_access_block" "site" {
  bucket                  = aws_s3_bucket.site.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Upload rendered assets
resource "aws_s3_object" "index" {
  bucket       = aws_s3_bucket.site.id
  key          = "index.html"
  content      = local.index_html
  content_type = "text/html; charset=utf-8"
  etag         = md5(local.index_html) # forces update when template changes
}

resource "aws_s3_object" "css" {
  bucket       = aws_s3_bucket.site.id
  key          = "styles.css"
  source       = "${path.module}/web/styles.css"
  content_type = "text/css; charset=utf-8"
  etag         = filemd5("${path.module}/web/styles.css")
}

resource "aws_s3_object" "js" {
  bucket       = aws_s3_bucket.site.id
  key          = "app.js"
  source       = "${path.module}/web/app.js"
  content_type = "application/javascript; charset=utf-8"
  etag         = filemd5("${path.module}/web/app.js")
}

# CloudFront OAC
resource "aws_cloudfront_origin_access_control" "site" {
  name                              = "${local.name}-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# CloudFront Distribution with custom domains & ACM (cert from acm.tf)
resource "aws_cloudfront_distribution" "site" {
  enabled             = true
  default_root_object = "index.html"

  origin {
    domain_name              = aws_s3_bucket.site.bucket_regional_domain_name
    origin_id                = "s3-site"
    origin_access_control_id = aws_cloudfront_origin_access_control.site.id
  }

  default_cache_behavior {
    target_origin_id       = "s3-site"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]

    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }
  }

  # Only serve non-www version
  aliases = [
    var.domain_name,
  ]

  price_class = "PriceClass_100"

  restrictions {
    geo_restriction {
      restriction_type = "blacklist"
      locations        = ["CN", "RU"] # China, Russia
    }
  }

  # Use the us-east-1 ACM cert validated in acm.tf
  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.cf.certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  depends_on = [
    aws_acm_certificate_validation.cf
  ]
}

# S3 bucket policy to allow only CloudFront (OAC) to read
data "aws_iam_policy_document" "site_allow_cf" {
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.site.arn}/*"]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.site.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "site_cf" {
  bucket = aws_s3_bucket.site.id
  policy = data.aws_iam_policy_document.site_allow_cf.json
}
