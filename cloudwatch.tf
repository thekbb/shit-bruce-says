# CloudWatch Log Groups for Lambda functions
# These are imported from existing auto-created log groups to manage retention

# Import blocks - delete these after running terraform apply
import {
  to = aws_cloudwatch_log_group.api_lambda
  id = "/aws/lambda/bruce-quotes-api"
}

import {
  to = aws_cloudwatch_log_group.page_generator_lambda
  id = "/aws/lambda/bruce-quotes-page-generator"
}

resource "aws_cloudwatch_log_group" "api_lambda" {
  name              = "/aws/lambda/${aws_lambda_function.api.function_name}"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "page_generator_lambda" {
  name              = "/aws/lambda/${aws_lambda_function.page_generator.function_name}"
  retention_in_days = 7
}
