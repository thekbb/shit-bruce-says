API_URL        ?= http://127.0.0.1:3000
SITE_URL       ?= http://localhost:8080
SAM_NET        ?= sam-local-net
SAM_PID        ?= .sam-local.pid
SAM_LOG        ?= .sam-local.out
PUBLISHER_PID  ?= .local-publisher.pid
PUBLISHER_LOG  ?= .local-publisher.out
DOCKER_HOST_VAL := $(shell docker context inspect --format '{{ (index .Endpoints "docker").Host }}' 2>/dev/null || echo unix://$(HOME)/.rd/docker.sock)

.PHONY: dev dev-fg up down wait-ddb wait-api table render publisher publisher-fg sam sam-fg stop logs test typecheck tflint lint clean status doctor

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
	cd lambda && uv run dev_create_table.py

wait-api:
	@echo "Waiting for local API on $(API_URL) ..."
	@for i in $$(seq 1 60); do \
		curl -fsS -o /dev/null -X OPTIONS \
			-H "Origin: $(SITE_URL)" \
			-H "Access-Control-Request-Method: POST" \
			-H "Access-Control-Request-Headers: content-type" \
			"$(API_URL)/quotes" >/dev/null 2>&1 && { \
			echo "Local API is up"; exit 0; }; \
		if [ -f "$(SAM_PID)" ]; then \
			PID=$$(cat "$(SAM_PID)"); \
			kill -0 "$$PID" 2>/dev/null || { \
				echo "SAM exited before the local API became ready. See $(SAM_LOG)" >&2; \
				exit 1; \
			}; \
		fi; \
		sleep 0.5; \
	done; \
	echo "Local API did not become ready in time. See $(SAM_LOG)" >&2; \
	exit 1

render:
	python3 tools/render_index.py --api $(API_URL) --site-url $(SITE_URL)

publisher-fg:
	python3 tools/watch_local_site.py --api $(API_URL) --site-url $(SITE_URL)

publisher:
	@echo "Starting local static publisher (background)…"
	@rm -f "$(PUBLISHER_PID)" "$(PUBLISHER_LOG)"
	@sh -c 'nohup python3 tools/watch_local_site.py --api "$(API_URL)" --site-url "$(SITE_URL)" \
		>"$(PUBLISHER_LOG)" 2>&1 & \
		echo $$! >"$(PUBLISHER_PID)"; \
		sleep 1; \
		echo "Local publisher started (PID $$(cat "$(PUBLISHER_PID)")). Logs: $(PUBLISHER_LOG)" >/dev/stderr'

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
		echo "SAM started (PID $$(cat "$(SAM_PID)")). Logs: $(SAM_LOG)" >/dev/stderr'
	@$(MAKE) wait-api

dev: up table render publisher sam
	@printf "\n"
	@echo "http://localhost:8080"

dev-fg: up table render publisher sam-fg

stop:
	@sh -c 'if [ -f "$(PUBLISHER_PID)" ]; then \
		echo "Stopping local publisher (PID $$(cat "$(PUBLISHER_PID)"))…"; \
		kill $$(cat "$(PUBLISHER_PID)") 2>/dev/null || true; \
		rm -f "$(PUBLISHER_PID)"; \
	else \
		echo "No local publisher PID file found ($(PUBLISHER_PID))"; \
	fi; \
	if [ -f "$(SAM_PID)" ]; then \
		echo "Stopping SAM (PID $$(cat "$(SAM_PID)"))…"; \
		kill $$(cat "$(SAM_PID)") 2>/dev/null || true; \
		rm -f "$(SAM_PID)"; \
	else \
		echo "No SAM PID file found ($(SAM_PID))"; \
	fi; \
	pkill -f "tools/watch_local_site.py" 2>/dev/null || true; \
	pkill -f "sam local start-api" 2>/dev/null || true; \
	docker compose down; \
	echo "Stopped."'

logs:
	docker compose logs -f

test:
	cd lambda && uv venv .venv && . .venv/bin/activate && \
	uv pip install -e '.[dev]' && pytest -q

typecheck:
	@echo "Running mypy type checker..."
	cd lambda && uv venv .venv && . .venv/bin/activate && \
	uv pip install -e '.[dev]' && mypy app.py page_generator.py

tflint:
	@echo "Running tflint..."
	tflint --init
	tflint --config=.tflint.hcl

lint: typecheck tflint
	@echo "All checks passed!"

status:
	@echo "Compose services:"; docker compose ps; echo ""
	@echo "Local publisher PID file: $(PUBLISHER_PID)"
	@sh -c 'if [ -f "$(PUBLISHER_PID)" ]; then ps -p $$(cat "$(PUBLISHER_PID)") -o pid= -o command=; else echo "(none)"; fi'
	@echo ""
	@echo "SAM PID file: $(SAM_PID)"
	@sh -c 'if [ -f "$(SAM_PID)" ]; then ps -p $$(cat "$(SAM_PID)") -o pid= -o command=; else echo "(none)"; fi'

clean:
	rm -rf .aws-sam "$(SAM_LOG)" "$(SAM_PID)" "$(PUBLISHER_LOG)" "$(PUBLISHER_PID)"
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name "*.pyc" -delete

doctor:
	@echo "DOCKER_HOST that will be used by SAM: $(DOCKER_HOST_VAL)"
	@docker version >/dev/null 2>&1 && echo "docker version: OK" || echo "docker version: FAIL"
	@docker run --rm hello-world >/dev/null 2>&1 && echo "hello-world run: OK" || echo "hello-world run: FAIL"
	@command -v sam >/dev/null 2>&1 && echo "sam cli: OK" || echo "sam cli: FAIL (brew install aws-sam-cli)"
