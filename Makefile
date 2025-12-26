.PHONY: help setup sync lint format fix build start restart down logs dev local deploy deploy-dev deploy-canary deploy-prod invoke invoke-stream invoke-agui chat clean aws-auth test test-unit test-e2e pipeline-dev pipeline-canary pipeline-prod

help:
	@echo "Available commands:"
	@echo ""
	@echo "  Setup & Dependencies"
	@echo "    make setup       Install uv and sync dependencies"
	@echo "    make sync        Sync dependencies with uv"
	@echo "    make aws-auth    Setup AWS authentication (federate)"
	@echo ""
	@echo "  Code Quality"
	@echo "    make lint        Check code with ruff"
	@echo "    make format      Format code with ruff"
	@echo "    make fix         Format and fix linting issues"
	@echo ""
	@echo "  Testing"
	@echo "    make test        Run all tests"
	@echo "    make test-unit   Run unit tests only (before deploy)"
	@echo "    make test-e2e    Run e2e tests (after deploy, needs AGENT_RUNTIME_ARN)"
	@echo ""
	@echo "  Docker Development"
	@echo "    make build       Build Docker image"
	@echo "    make start       Start container (detached)"
	@echo "    make restart     Rebuild and restart container"
	@echo "    make down        Stop and remove container"
	@echo "    make logs        Follow container logs"
	@echo "    make dev         Start with hot reload (watch mode)"
	@echo ""
	@echo "  Local Development"
	@echo "    make local       Run agent locally (in-memory state)"
	@echo "    make local MEMORY_ID=<id>  Run with AWS AgentCore Memory"
	@echo ""
	@echo "  Deployment Pipelines"
	@echo "    make pipeline-dev     Run UTs -> deploy dev -> E2E tests"
	@echo "    make pipeline-canary  Deploy canary -> E2E tests"
	@echo "    make pipeline-prod    Deploy prod -> E2E tests"
	@echo ""
	@echo "  Individual Deployment"
	@echo "    make deploy-dev       Deploy to dev environment"
	@echo "    make deploy-canary    Deploy to canary environment"
	@echo "    make deploy-prod      Deploy to prod environment"
	@echo ""
	@echo "  Invocation"
	@echo "    make invoke         Invoke deployed agent (non-streaming)"
	@echo "    make invoke-stream  Invoke with plain text streaming"
	@echo "    make invoke-agui    Invoke with AG-UI protocol streaming"
	@echo "    make chat           Interactive streaming chat (local)"
	@echo "                        Usage: make invoke INPUT=<msg> [SESSION_ID=<id>] [USER_ID=<id>] [ENV=dev|canary|prod]"
	@echo ""
	@echo "  Utilities"
	@echo "    make clean       Clean cache files"

setup:
	@command -v uv >/dev/null 2>&1 || { echo "Installing uv..."; curl -LsSf https://astral.sh/uv/install.sh | sh; }
	@$(MAKE) sync

sync:
	uv sync

aws-auth:
	@if command -v setyinit; then \
		setyinit; \
	elif command -v jyinit; then \
		jyinit; \
	elif command -v yinit; then \
		yinit; \
	fi
	@if command -v awsfed2; then \
		awsfed2 -n -a 905418222531 -r sso/fed.bedrock-poc.user; \
	fi

lint:
	uv run ruff check .

format:
	uv run ruff format .

fix: format
	uv run ruff check . --fix

test:
	uv run pytest

test-unit:
	uv run pytest -m unit

test-e2e: aws-auth
	@if [ -z "$(AGENT_RUNTIME_ARN)" ]; then \
		echo "Error: AGENT_RUNTIME_ARN is required for e2e tests"; \
		echo "Usage: make test-e2e AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:..."; \
		exit 1; \
	fi
	AGENT_RUNTIME_ARN=$(AGENT_RUNTIME_ARN) uv run pytest -m e2e

build:
	docker compose build

start:
	docker compose up -d

restart:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

dev:
	docker compose watch

local:
	MODEL=bedrock:us.anthropic.claude-haiku-4-5-20251001-v1:0 \
	MEMORY_ID=$(or $(MEMORY_ID),) \
	uv run python -m agent.main

deploy: deploy-dev

deploy-dev: aws-auth
	@echo "🚀 Deploying to DEV environment..."
	uv run cdk deploy -c env=dev --require-approval never --outputs-file cdk-outputs-dev.json

deploy-canary: aws-auth
	@echo "🚀 Deploying to CANARY environment..."
	uv run cdk deploy -c env=canary --require-approval never --outputs-file cdk-outputs-canary.json

deploy-prod: aws-auth
	@echo "🚀 Deploying to PROD environment..."
	uv run cdk deploy -c env=prod --require-approval never --outputs-file cdk-outputs-prod.json

pipeline-dev: test-unit deploy-dev
	@echo "🧪 Running E2E tests against DEV..."
	$(eval ARN := $(shell cat cdk-outputs-dev.json | python -c "import sys,json; d=json.load(sys.stdin); print(list(d.values())[0]['RuntimeArn'])"))
	AGENT_RUNTIME_ARN=$(ARN) $(MAKE) test-e2e
	@echo "✅ DEV pipeline complete!"

pipeline-canary: deploy-canary
	@echo "🧪 Running E2E tests against CANARY..."
	$(eval ARN := $(shell cat cdk-outputs-canary.json | python -c "import sys,json; d=json.load(sys.stdin); print(list(d.values())[0]['RuntimeArn'])"))
	AGENT_RUNTIME_ARN=$(ARN) $(MAKE) test-e2e
	@echo "✅ CANARY pipeline complete!"

pipeline-prod: deploy-prod
	@echo "🧪 Running E2E tests against PROD..."
	$(eval ARN := $(shell cat cdk-outputs-prod.json | python -c "import sys,json; d=json.load(sys.stdin); print(list(d.values())[0]['RuntimeArn'])"))
	AGENT_RUNTIME_ARN=$(ARN) $(MAKE) test-e2e
	@echo "✅ PROD pipeline complete!"

get-arn:
	@if [ -z "$(ENV)" ]; then ENV=dev; fi
	@cat cdk-outputs-$(ENV).json | python -c "import sys,json; d=json.load(sys.stdin); print(list(d.values())[0]['RuntimeArn'])"

invoke: aws-auth
	@if [ -z "$(INPUT)" ]; then \
		echo "Usage: make invoke INPUT=<msg> [SESSION_ID=<id>] [USER_ID=<id>] [ENV=dev|canary|prod]"; \
		exit 1; \
	fi
	@if [ -z "$(SESSION_ID)" ] || [ -z "$(USER_ID)" ]; then \
		echo " Note: SESSION_ID and USER_ID not provided. Using defaults (memory won't persist across invocations)."; \
	fi
	$(eval ENV := $(or $(ENV),dev))
	$(eval ARN := $(shell cat cdk-outputs-$(ENV).json 2>/dev/null | python -c "import sys,json; d=json.load(sys.stdin); print(list(d.values())[0]['RuntimeArn'])" 2>/dev/null || echo ""))
	@if [ -z "$(ARN)" ]; then \
		echo "Error: No deployment found for ENV=$(ENV). Run 'make deploy-$(ENV)' first."; \
		exit 1; \
	fi
	AGENT_RUNTIME_ARN=$(ARN) uv run python -c "from scripts.invoke import main; main('$(INPUT)', $(if $(SESSION_ID),'$(SESSION_ID)',None), $(if $(USER_ID),'$(USER_ID)',None), stream=False)"

invoke-stream: aws-auth
	@if [ -z "$(INPUT)" ]; then \
		echo "Usage: make invoke-stream INPUT=<msg> [SESSION_ID=<id>] [USER_ID=<id>] [ENV=dev|canary|prod]"; \
		exit 1; \
	fi
	@if [ -z "$(SESSION_ID)" ] || [ -z "$(USER_ID)" ]; then \
		echo " Note: SESSION_ID and USER_ID not provided. Using defaults (memory won't persist across invocations)."; \
	fi
	$(eval ENV := $(or $(ENV),dev))
	$(eval ARN := $(shell cat cdk-outputs-$(ENV).json 2>/dev/null | python -c "import sys,json; d=json.load(sys.stdin); print(list(d.values())[0]['RuntimeArn'])" 2>/dev/null || echo ""))
	@if [ -z "$(ARN)" ]; then \
		echo "Error: No deployment found for ENV=$(ENV). Run 'make deploy-$(ENV)' first."; \
		exit 1; \
	fi
	AGENT_RUNTIME_ARN=$(ARN) uv run python -c "from scripts.invoke import main; main('$(INPUT)', $(if $(SESSION_ID),'$(SESSION_ID)',None), $(if $(USER_ID),'$(USER_ID)',None), stream=True)"

invoke-agui: aws-auth
	@if [ -z "$(INPUT)" ]; then \
		echo "Usage: make invoke-agui INPUT=<msg> [SESSION_ID=<id>] [USER_ID=<id>] [ENV=dev|canary|prod]"; \
		exit 1; \
	fi
	@if [ -z "$(SESSION_ID)" ] || [ -z "$(USER_ID)" ]; then \
		echo " Note: SESSION_ID and USER_ID not provided. Using defaults (memory won't persist across invocations)."; \
	fi
	$(eval ENV := $(or $(ENV),dev))
	$(eval ARN := $(shell cat cdk-outputs-$(ENV).json 2>/dev/null | python -c "import sys,json; d=json.load(sys.stdin); print(list(d.values())[0]['RuntimeArn'])" 2>/dev/null || echo ""))
	@if [ -z "$(ARN)" ]; then \
		echo "Error: No deployment found for ENV=$(ENV). Run 'make deploy-$(ENV)' first."; \
		exit 1; \
	fi
	AGENT_RUNTIME_ARN=$(ARN) uv run python -c "from scripts.invoke import main; main('$(INPUT)', $(if $(SESSION_ID),'$(SESSION_ID)',None), $(if $(USER_ID),'$(USER_ID)',None), stream_agui=True)"

chat:
	@echo "Starting interactive chat (make sure local server is running with 'make local')"
	uv run python -m yahoo_dsp_agent_sdk.chat --endpoint=invocations --default

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

