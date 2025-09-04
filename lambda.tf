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

# Lambda function
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

resource "aws_lambda_permission" "api_invoke" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}
