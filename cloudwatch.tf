resource "aws_cloudwatch_log_group" "api_lambda" {
  name              = "/aws/lambda/${aws_lambda_function.api.function_name}"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "page_generator_lambda" {
  name              = "/aws/lambda/${aws_lambda_function.page_generator.function_name}"
  retention_in_days = 7
}
