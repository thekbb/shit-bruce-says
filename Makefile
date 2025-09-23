API_URL        ?= http://127.0.0.1:3000
SAM_NET        ?= sam-local-net
SAM_PID        ?= .sam-local.pid
SAM_LOG        ?= .sam-local.out
DOCKER_HOST_VAL := $(shell docker context inspect --format '{{ (index .Endpoints "docker").Host }}' 2>/dev/null || echo unix://$(HOME)/.rd/docker.sock)

.PHONY: dev dev-fg up down wait-ddb table render sam sam-fg stop logs test clean status doctor

up:
	docker compose up -d

down:
	docker compose down

wait-ddb:
	@echo "Waiting for DynamoDB Local on http://localhost:8000 ..."
	@for i in $$(seq 1 60); do \
		AWS_ACCESS_KEY_ID=fake AWS_SECRET_ACCESS_KEY=fake AWS_REGION=us-east-2 \
		aws dynamodb list-tables --endpoint-url http://localhost:8000 >/dev/null 2>&1 && { \
			echo "DynamoDB Local is up"; exit 0; }; \
		sleep 0.5; \
	done; \
	echo "DynamoDB Local did not become ready in time" >&2; \
	exit 1

table: wait-ddb
	cd lambda && python dev_create_table.py

render:
	python tools/render_index.py --api $(API_URL)

seo:
	python3 tools/generate_seo_page.py --output web/seo.html

quote-pages:
	python3 tools/generate_quote_pages.py

sam-fg:
	DOCKER_HOST="$(DOCKER_HOST_VAL)" sam build --use-container
	DOCKER_HOST="$(DOCKER_HOST_VAL)" sam local start-api --docker-network $(SAM_NET) --warm-containers EAGER

sam:
	@echo "Starting SAM locally (background)…"
	@rm -f "$(SAM_PID)" "$(SAM_LOG)"
	@sh -c 'DOCKER_HOST="$(DOCKER_HOST_VAL)"; export DOCKER_HOST; \
		nohup sh -c "sam build --use-container >/dev/null 2>&1 && \
		             exec sam local start-api --docker-network \"$(SAM_NET)\" --warm-containers EAGER" \
		>"$(SAM_LOG)" 2>&1 & \
		echo $$! >"$(SAM_PID)"; \
		sleep 1; \
		echo "SAM started (PID $$(cat "$(SAM_PID)")). Logs: $(SAM_LOG)" >/dev/stderr'

dev: up table render sam
	@printf "\n"
	@echo "http://localhost:8080"

dev-fg: up table render sam-fg

stop:
	@sh -c 'if [ -f "$(SAM_PID)" ]; then \
		echo "Stopping SAM (PID $$(cat "$(SAM_PID)"))…"; \
		kill $$(cat "$(SAM_PID)") 2>/dev/null || true; \
		rm -f "$(SAM_PID)"; \
	else \
		echo "No SAM PID file found ($(SAM_PID))"; \
	fi; \
	pkill -f "sam local start-api" 2>/dev/null || true; \
	docker compose down; \
	echo "Stopped."'

logs:
	docker compose logs -f

test:
	cd lambda && uv venv .venv && . .venv/bin/activate && \
	uv pip install -e '.[dev]' && pytest -q

status:
	@echo "Compose services:"; docker compose ps; echo ""
	@echo "SAM PID file: $(SAM_PID)"
	@sh -c 'if [ -f "$(SAM_PID)" ]; then ps -p $$(cat "$(SAM_PID)") -o pid,cmd; else echo "(none)"; fi'

clean:
	rm -rf .aws-sam "$(SAM_LOG)" "$(SAM_PID)"
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name "*.pyc" -delete

doctor:
	@echo "DOCKER_HOST that will be used by SAM: $(DOCKER_HOST_VAL)"
	@docker version >/dev/null 2>&1 && echo "docker version: OK" || echo "docker version: FAIL"
	@docker run --rm hello-world >/dev/null 2>&1 && echo "hello-world run: OK" || echo "hello-world run: FAIL"
	@command -v sam >/dev/null 2>&1 && echo "sam cli: OK" || echo "sam cli: FAIL (brew install aws-sam-cli)"
