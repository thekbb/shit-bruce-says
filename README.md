# Shit Bruce Says

Collects memorable quotes from Bruce. Anyone can add quotes via the web UI.

## Local Development

### Prerequisites

- Docker (tested with Rancher Desktop)
- Python
- [uv](https://github.com/astral-sh/uv) for Python deps
- AWS SAM CLI (`brew install aws-sam-cli`)
- Terraform (for deployments)
- [mise-en-place](https://mise.jdx.dev/)

### Quick Start

```bash
make dev
```

This starts DynamoDB Local, nginx (serving the web UI), and SAM (Lambda API) in the background.

Open http://localhost:8080 to use the app.

### Available Commands

```bash
make dev       # Start everything (one command)
make dev-fg    # Same, but SAM runs in foreground
make stop      # Stop everything
make logs      # View Docker logs
make test      # Run Lambda tests
```

## Testing

```bash
cd lambda
uv venv .venv
source .venv/bin/activate
uv pip install -e '.[dev]'
pytest
```

Tests use moto to mock AWS services. No credentials needed.

## Deployment

```bash
terraform init
terraform apply
```

Deploys to AWS: submission Lambda, publisher Lambda, DynamoDB, S3, CloudFront, Route53.

## How It Works

### Data Flow

1. User submits quote → API Gateway → Lambda → DynamoDB
2. Lambda writes the quote to DynamoDB and asynchronously invokes the publisher
3. Publisher Lambda rebuilds `index.html`, quote pages, and `sitemap.xml` in S3
4. CloudFront serves the generated static site

### Quote Pages

Each quote gets its own static HTML page at `/quotes/{id}/` with canonical URLs, proper Open Graph tags, and Twitter card metadata. These are real pages for both humans and crawlers.

### Storage

Quotes are stored without surrounding quotation marks. The display layer adds them for consistency. ULIDs (Crockford Base32) are used as sort keys for proper chronological ordering.
