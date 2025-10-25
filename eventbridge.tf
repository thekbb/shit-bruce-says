# EventBridge rule to capture DynamoDB stream events
resource "aws_cloudwatch_event_rule" "dynamodb_changes" {
  name        = "${local.name}-dynamodb-changes"
  description = "Capture DynamoDB stream events for quote changes"

  event_pattern = jsonencode({
    source      = ["aws.dynamodb"]
    detail-type = ["DynamoDB Stream Record"]
    detail = {
      eventSource = ["aws:dynamodb"]
      eventName   = ["INSERT", "MODIFY"]
      dynamodb = {
        Keys = {
          PK = {
            S = ["QUOTE"]
          }
        }
      }
    }
  })
}

resource "aws_cloudwatch_event_target" "page_generator" {
  rule      = aws_cloudwatch_event_rule.dynamodb_changes.name
  target_id = "PageGeneratorTarget"
  arn       = aws_lambda_function.page_generator.arn
}

# EventBridge pipe to connect DynamoDB streams to EventBridge
resource "aws_pipes_pipe" "dynamodb_to_eventbridge" {
  name     = "${local.name}-dynamodb-stream-pipe"
  role_arn = aws_iam_role.eventbridge_pipe_role.arn

  source = aws_dynamodb_table.quotes.stream_arn
  target = "arn:aws:events:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:event-bus/default"

  source_parameters {
    dynamodb_stream_parameters {
      starting_position = "LATEST"
      batch_size        = 1
    }
  }

  target_parameters {
    eventbridge_event_bus_parameters {
      detail_type = "DynamoDB Stream Record"
      source      = "aws.dynamodb"
    }
  }
}

# IAM role for EventBridge Pipes
resource "aws_iam_role" "eventbridge_pipe_role" {
  name = "${local.name}-eventbridge-pipe-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "pipes.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "eventbridge_pipe_policy" {
  name        = "${local.name}-eventbridge-pipe-policy"
  description = "Allow EventBridge Pipes to read DynamoDB streams and write to EventBridge"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:DescribeStream",
          "dynamodb:GetRecords",
          "dynamodb:GetShardIterator",
          "dynamodb:ListStreams"
        ]
        Resource = aws_dynamodb_table.quotes.stream_arn
      },
      {
        Effect = "Allow"
        Action = [
          "events:PutEvents"
        ]
        Resource = "arn:aws:events:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:event-bus/default"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "eventbridge_pipe_policy" {
  role       = aws_iam_role.eventbridge_pipe_role.name
  policy_arn = aws_iam_policy.eventbridge_pipe_policy.arn
}

# Data sources for current AWS account and region
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
