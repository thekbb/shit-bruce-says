terraform {
  required_version = ">= 1.13.1"

  required_providers {
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.7.1"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.27"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2.4"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.7.2"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
  backend "s3" {
    key          = "shitbrucesays/terraform.tfstate"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      environment = "prod"
      system      = "shit-bruce-says"
    }
  }
}

# Extra provider for us-east-1 (for CloudFront ACM)
provider "aws" {
  alias  = "use1"
  region = "us-east-1"

  default_tags {
    tags = {
      environment = "prod"
      system      = "shit-bruce-says"
    }
  }
}
