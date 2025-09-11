# shit-bruce-says

A collection of shit Bruce said, with input to grow the collection.

## Prereqs

- Terraform ≥ 1.13.1
- Python 3.12 for local tools/tests
- [uv](https://github.com/astral-sh/uv) (`pipx install uv` or Homebrew)
- Docker engine (Rancher Desktop)
- AWS SAM CLI (`brew tap aws/tap && brew install aws-sam-cli`)
- AWS CLI (optional; for local table checks)

## One-shot local dev (Compose + SAM in background)

```bash
make dev
```

This will:

1. Start **DynamoDB Local** (port `8000`) and **nginx** (serves `./web` on port `8080`) via `docker compose up -d`.
2. (Re)create the DynamoDB table `bruce-quotes` locally.
3. Render `web/index.html` from `web/index.html.tpl` pointing to **`http://127.0.0.1:3000`**.
4. Run **SAM** (Lambda/API) on the same Docker network **in the background**.

Open:

- **Web UI** → http://localhost:8080
- **API** → http://127.0.0.1:3000/quotes

Stop everything:

```bash
make stop
```

## Useful make targets

```bash
make up        # docker compose up -d  (DDB + nginx)
make table     # (re)create the local DynamoDB table
make render    # render web/index.html from web/index.html.tpl (API_URL overridable)
make sam       # start SAM in background, PID saved to .sam-local.pid
make dev       # up + table + render + sam   <-- one-shot
make dev-fg    # same but SAM in foreground (blocks)
make logs      # tail compose logs
make status    # show compose services + SAM pid
make stop      # stop SAM (if running) + compose down
```

Override the rendered API base:

```bash
make render API_URL=http://127.0.0.1:3000
```

## Unit tests (no AWS)

```bash
cd lambda
uv venv .venv
source .venv/bin/activate
uv pip install -e '.[dev]'
pytest -q
```

Tests use **moto**; no AWS creds required.

## Build & deploy to AWS

```bash
# from repo root
terraform init
terraform apply
```
