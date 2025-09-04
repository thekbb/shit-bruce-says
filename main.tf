# Main Terraform configuration
# Resources are organized in separate files:
# - locals.tf: Local values and computed data
# - dynamodb.tf: DynamoDB table
# - iam.tf: IAM roles, policies, and attachments
# - lambda.tf: Lambda function and packaging
# - api-gateway.tf: API Gateway resources
# - s3-static.tf: S3 bucket and static assets
# - cloudfront.tf: CloudFront distribution and policies
# - acm.tf: SSL certificates
# - route53.tf: DNS records
# - variables.tf: Input variables
# - outputs.tf: Output values
# - versions.tf: Provider versions
