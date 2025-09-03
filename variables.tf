variable "allow_origin" {
  description = "CORS allowed origin ('*' for dev, real domain in prod)"
  type        = string
  default     = "*"
}

variable "aws_region" {
  type    = string
  default = "us-east-2"
}

variable "env" {
  type    = string
  default = "prod"
}

variable "project" {
  type    = string
  default = "bruce-quotes"
}

variable "table_name" {
  description = "Name of the DynamoDB table"
  type        = string
  default     = "bruce-quotes"
}
