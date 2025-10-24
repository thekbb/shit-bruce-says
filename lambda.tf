# Data sources
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

data "archive_file" "page_generator_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda/page_generator.py"
  output_path = "${path.module}/.dist/page_generator.zip"
}

# Lambda function
resource "aws_lambda_function" "api" {
  function_name = "${local.name}-api"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "app.handler"
  runtime       = "python3.12"
  architectures = ["arm64"]

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      TABLE_NAME   = aws_dynamodb_table.quotes.name
      ALLOW_ORIGIN = var.allow_origin
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
  runtime       = "python3.12"
  architectures = ["arm64"]
  timeout       = 60

  filename         = data.archive_file.page_generator_zip.output_path
  source_code_hash = data.archive_file.page_generator_zip.output_base64sha256

  environment {
    variables = {
      BUCKET_NAME = var.domain_name
      DOMAIN      = var.domain_name
      TABLE_NAME  = aws_dynamodb_table.quotes.name
    }
  }
}

resource "aws_lambda_permission" "page_generator_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.page_generator.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.dynamodb_changes.arn
}
