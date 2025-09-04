variable "allow_origin" {
  description = "CORS allowed origin ('*' for dev, real domain in prod)"
  type        = string
  default     = "*"
}

variable "api_subdomain" {
    description = "Subdomain for the API custom domain"
    type        = string
    default     = "api"
}

variable "aws_region" {
  type    = string
  default = "us-east-2"
}

variable "domain_name" {
    description = "Root domain name"
    type        = string
    default     = "shitbrucesays.co.uk"
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
