# GitHub OIDC Provider for AWS authentication
# Allows GitHub Actions to assume AWS IAM roles without long-lived credentials

data "tls_certificate" "github" {
  url = "https://token.actions.githubusercontent.com"
}

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.github.certificates[0].sha1_fingerprint]

  tags = {
    Name = "github-actions-oidc"
  }
}

# Terraform Plan Role (Read-Only)
# Used by terraform-plan.yml workflow on pull requests
resource "aws_iam_role" "github_terraform_plan" {
  name = "${local.name}-github-terraform-plan"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.github.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          # Only allow from your repo and pull_request events
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_repo}:pull_request"
        }
      }
    }]
  })

  tags = {
    Name = "github-terraform-plan"
  }
}

# Terraform Plan Policy (Read-Only)
resource "aws_iam_role_policy" "github_terraform_plan" {
  name = "terraform-plan-permissions"
  role = aws_iam_role.github_terraform_plan.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          # Read-only Terraform state operations
          "s3:GetObject",
          "s3:ListBucket",

          # DynamoDB state locking (read)
          "dynamodb:GetItem",
          "dynamodb:DescribeTable",

          # Read AWS resources for plan
          "apigateway:GET",
          "cloudfront:Get*",
          "cloudfront:List*",
          "dynamodb:Describe*",
          "dynamodb:List*",
          "iam:Get*",
          "iam:List*",
          "lambda:Get*",
          "lambda:List*",
          "route53:Get*",
          "route53:List*",
          "s3:Get*",
          "s3:List*",
          "acm:Describe*",
          "acm:List*",
        ]
        Resource = "*"
      }
    ]
  })
}

# Terraform Apply Role (Read-Write)
# Used by terraform-apply.yml workflow on main branch pushes
resource "aws_iam_role" "github_terraform_apply" {
  name = "${local.name}-github-terraform-apply"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.github.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          # Only allow from your repo and main branch
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_repo}:ref:refs/heads/main"
        }
      }
    }]
  })

  tags = {
    Name = "github-terraform-apply"
  }
}

# Terraform Apply Policy (Full Access)
resource "aws_iam_role_policy" "github_terraform_apply" {
  name = "terraform-apply-permissions"
  role = aws_iam_role.github_terraform_apply.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          # Full Terraform state operations
          "s3:*",

          # DynamoDB state locking (read/write)
          "dynamodb:*",

          # Manage all AWS resources
          "apigateway:*",
          "cloudfront:*",
          "iam:*",
          "lambda:*",
          "route53:*",
          "acm:*",
          "logs:*",
        ]
        Resource = "*"
      }
    ]
  })
}
