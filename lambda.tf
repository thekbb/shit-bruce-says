data "aws_s3_object" "lambda_api" {
  bucket = aws_s3_bucket.lambda_artifacts.bucket
  key    = var.lambda_api_s3_key
}

data "aws_s3_object" "lambda_page_generator" {
  bucket = aws_s3_bucket.lambda_artifacts.bucket
  key    = var.lambda_page_generator_s3_key
}

# Lambda function
resource "aws_lambda_function" "api" {
  function_name = "${local.name}-api"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "app.handler"
  runtime       = "python3.14"
  architectures = ["arm64"]

  s3_bucket         = aws_s3_bucket.lambda_artifacts.bucket
  s3_key            = var.lambda_api_s3_key
  s3_object_version = data.aws_s3_object.lambda_api.version_id

  environment {
    variables = {
      TABLE_NAME                    = aws_dynamodb_table.quotes.name
      ALLOW_ORIGIN                  = var.allow_origin
      PAGE_GENERATOR_FUNCTION_NAME  = aws_lambda_function.page_generator.function_name
    }
  }
}

resource "aws_lambda_permission" "api_invoke" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}

# Page Generator Lambda
resource "aws_lambda_function" "page_generator" {
  function_name = "${local.name}-page-generator"
  role          = aws_iam_role.page_generator_exec.arn
  handler       = "page_generator.handler"
  runtime       = "python3.14"
  architectures = ["arm64"]
  timeout       = 60

  s3_bucket         = aws_s3_bucket.lambda_artifacts.bucket
  s3_key            = var.lambda_page_generator_s3_key
  s3_object_version = data.aws_s3_object.lambda_page_generator.version_id

  environment {
    variables = {
      BUCKET_NAME  = aws_s3_bucket.site.bucket
      DOMAIN       = var.domain_name
      TABLE_NAME   = aws_dynamodb_table.quotes.name
      API_BASE_URL = "https://${aws_apigatewayv2_domain_name.api.domain_name}"
    }
  }
}
