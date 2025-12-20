locals {
  api_routes = {
    get = {
      method         = "GET"
      throttle_burst = 50 # Allow bursts for pagination/scrolling
      throttle_rate  = 20 # 20 req/sec for viewing quotes
    }
    post = {
      method         = "POST"
      throttle_burst = 5 # Low burst for submissions
      throttle_rate  = 2 # 2 req/sec max for submitting quotes
    }
    options = {
      method         = "OPTIONS"
      throttle_burst = 50 # CORS preflight requests
      throttle_rate  = 20 # Allow browsers to make preflight checks
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
    max_age        = 3602
  }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true

  dynamic "route_settings" {
    for_each = local.api_routes
    content {
      route_key              = "${route_settings.value.method} /quotes"
      throttling_burst_limit = route_settings.value.throttle_burst
      throttling_rate_limit  = route_settings.value.throttle_rate
    }
  }
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
}

# Routes
resource "aws_apigatewayv2_route" "quotes" {
  for_each  = local.api_routes
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "${each.value.method} /quotes"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
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
