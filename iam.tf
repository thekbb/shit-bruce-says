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
      Effect = "Allow"
      Action = [
        "dynamodb:PutI*",
        "dynamodb:Query",
      ]
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

# Page Generator Lambda IAM Role
resource "aws_iam_role" "page_generator_exec" {
  name = "${local.name}-page-generator-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# Page Generator Lambda access policy
resource "aws_iam_policy" "page_generator_access" {
  name        = "${local.name}-page-generator-access"
  description = "Allow page generator Lambda to read DynamoDB and write to S3"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:Describe*",
          "dynamodb:Get*",
          "dynamodb:GetRecords",
          "dynamodb:GetShardIterator",
          "dynamodb:ListStreams",
          "dynamodb:Query",
        ]
        Resource = [
          aws_dynamodb_table.quotes.arn,
          "${aws_dynamodb_table.quotes.arn}/*",
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl",
        ]
        Resource = "${aws_s3_bucket.site.arn}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "page_generator_access" {
  role       = aws_iam_role.page_generator_exec.name
  policy_arn = aws_iam_policy.page_generator_access.arn
}

resource "aws_iam_role_policy_attachment" "page_generator_basic" {
  role       = aws_iam_role.page_generator_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
