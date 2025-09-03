terraform {
  required_version = ">= 1.13.1"

  required_providers {
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.7.1"
    }
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.11.0"
    }
    null = {
      source  = "hashicorp/null"
      version = ">= 3.2.4"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.7.2"
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
}
