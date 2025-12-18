# GitHub OIDC Provider for AWS authentication
# Allows GitHub Actions to assume AWS IAM roles without long-lived credentials

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["1c58a3a8518e8759bf075b76b750d4f2df264fcd"]

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
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_repo}:*"
        }
      }
    }]
  })

  tags = {
    Name = "github-terraform-plan"
  }
}

# Terraform Plan Policy (Read-Only + State Lock)
resource "aws_iam_role_policy" "github_terraform_plan" {
  name = "terraform-plan-permissions"
  role = aws_iam_role.github_terraform_plan.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "acm:Describe*",
          "acm:List*",
          "apigateway:Get*",
          "apigateway:List*",
          "cloudfront:Get*",
          "cloudfront:List*",
          "dynamodb:Describe*",
          "dynamodb:Get*",
          "dynamodb:List*",
          "iam:Get*",
          "iam:List*",
          "lambda:Get*",
          "lambda:List*",
          "route53:Get*",
          "route53:List*",
          "s3:Get*",
          "s3:List*",
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:DeleteObject",
        ]
        Resource = "arn:aws:s3:::tfstate-628639830692-us-east-2/*.tflock"
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
          "acm:*",
          "apigateway:*",
          "cloudfront:*",
          "dynamodb:*",
          "iam:*",
          "lambda:*",
          "logs:*",
          "route53:*",
          "s3:*",
        ]
        Resource = "*"
      }
    ]
  })
}
