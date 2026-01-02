.PHONY: help setup sync lint format fix build start restart down logs dev local deploy invoke invoke-stream invoke-agui chat clean aws-auth test test-unit test-e2e promote-canary promote-prod get-latest-version promote-canary-latest promote-prod-latest pipeline-pr pipeline-merge

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
	@echo "    make test-e2e    Run e2e tests (uses dev endpoint by default)"
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
	@echo "  Deployment"
	@echo "    make deploy      Deploy runtime (creates new version, dev endpoint auto-updates)"
	@echo ""
	@echo "  Endpoint Promotion"
	@echo "    make promote-canary VERSION=N  Update canary endpoint to version N"
	@echo "    make promote-prod VERSION=N    Update prod endpoint to version N"
	@echo "    make promote-canary-latest     Promote canary to latest version"
	@echo "    make promote-prod-latest       Promote prod to latest version"
	@echo "    make get-latest-version        Show latest deployed version"
	@echo ""
	@echo "  Pipeline Simulation"
	@echo "    make pipeline-pr               Run PR checks (lint, test)"
	@echo "    make pipeline-merge            Run full deploy pipeline"
	@echo ""
	@echo "  Invocation"
	@echo "    make invoke ENDPOINT=dev|canary|prod INPUT=<msg>"
	@echo "    make invoke-stream ENDPOINT=dev|canary|prod INPUT=<msg>"
	@echo "    make invoke-agui ENDPOINT=dev|canary|prod INPUT=<msg>"
	@echo "    make chat        Interactive streaming chat (local)"
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
	$(eval ARN := $(shell cat cdk-outputs.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['DSPAgentStack']['RuntimeArn'])" 2>/dev/null || echo ""))
	$(eval ENDPOINT := $(or $(ENDPOINT),dev))
	@if [ -z "$(ARN)" ]; then \
		echo "Error: No deployment found. Run 'make deploy' first."; \
		exit 1; \
	fi
	AGENT_RUNTIME_ARN=$(ARN) AGENT_ENDPOINT=$(ENDPOINT) uv run pytest -m e2e

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

deploy: aws-auth
	@echo "Deploying runtime (creates new version)..."
	uv run cdk deploy --require-approval never --outputs-file cdk-outputs.json
	@echo ""
	@echo "Deployment complete! Endpoints:"
	@cat cdk-outputs.json | python3 -c "import sys,json; d=json.load(sys.stdin)['DSPAgentStack']; print(f\"  dev:    {d['DevEndpointArn']}\"); print(f\"  canary: {d['CanaryEndpointArn']}\"); print(f\"  prod:   {d['ProdEndpointArn']}\")"

promote-canary: aws-auth
	@if [ -z "$(VERSION)" ]; then \
		echo "Usage: make promote-canary VERSION=N"; \
		exit 1; \
	fi
	$(eval RUNTIME_ID := $(shell cat cdk-outputs.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['DSPAgentStack']['RuntimeId'])"))
	@echo "Promoting canary endpoint to version $(VERSION)..."
	aws bedrock-agentcore-control update-agent-runtime-endpoint \
		--agent-runtime-id $(RUNTIME_ID) \
		--endpoint-name canary \
		--agent-runtime-version $(VERSION) \
		--region us-east-1

promote-prod: aws-auth
	@if [ -z "$(VERSION)" ]; then \
		echo "Usage: make promote-prod VERSION=N"; \
		exit 1; \
	fi
	$(eval RUNTIME_ID := $(shell cat cdk-outputs.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['DSPAgentStack']['RuntimeId'])"))
	@echo "Promoting prod endpoint to version $(VERSION)..."
	aws bedrock-agentcore-control update-agent-runtime-endpoint \
		--agent-runtime-id $(RUNTIME_ID) \
		--endpoint-name prod \
		--agent-runtime-version $(VERSION) \
		--region us-east-1

get-latest-version:
	@$(eval RUNTIME_ID := $(shell cat cdk-outputs.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['DSPAgentStack']['RuntimeId'])"))
	@uv run python scripts/get_latest_version.py $(RUNTIME_ID)

promote-canary-latest: aws-auth
	$(eval RUNTIME_ID := $(shell cat cdk-outputs.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['DSPAgentStack']['RuntimeId'])"))
	$(eval VERSION := $(shell uv run python scripts/get_latest_version.py $(RUNTIME_ID)))
	@echo "Promoting canary endpoint to latest version $(VERSION)..."
	aws bedrock-agentcore-control update-agent-runtime-endpoint \
		--agent-runtime-id $(RUNTIME_ID) \
		--endpoint-name canary \
		--agent-runtime-version $(VERSION) \
		--region us-east-1

promote-prod-latest: aws-auth
	$(eval RUNTIME_ID := $(shell cat cdk-outputs.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['DSPAgentStack']['RuntimeId'])"))
	$(eval VERSION := $(shell uv run python scripts/get_latest_version.py $(RUNTIME_ID)))
	@echo "Promoting prod endpoint to latest version $(VERSION)..."
	aws bedrock-agentcore-control update-agent-runtime-endpoint \
		--agent-runtime-id $(RUNTIME_ID) \
		--endpoint-name prod \
		--agent-runtime-version $(VERSION) \
		--region us-east-1

pipeline-pr:
	@bash scripts/on_pr.sh

pipeline-merge: aws-auth
	@bash scripts/on_merge.sh

invoke: aws-auth
	@if [ -z "$(INPUT)" ]; then \
		echo "Usage: make invoke INPUT=<msg> [ENDPOINT=dev|canary|prod] [SESSION_ID=<id>] [USER_ID=<id>]"; \
		exit 1; \
	fi
	$(eval ENDPOINT := $(or $(ENDPOINT),dev))
	$(eval ARN := $(shell cat cdk-outputs.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['DSPAgentStack']['RuntimeArn'])" 2>/dev/null || echo ""))
	@if [ -z "$(ARN)" ]; then \
		echo "Error: No deployment found. Run 'make deploy' first."; \
		exit 1; \
	fi
	@echo "Invoking $(ENDPOINT) endpoint..."
	AGENT_RUNTIME_ARN=$(ARN) AGENT_ENDPOINT=$(ENDPOINT) uv run python -c "from scripts.invoke import main; main('$(INPUT)', $(if $(SESSION_ID),'$(SESSION_ID)',None), $(if $(USER_ID),'$(USER_ID)',None), stream=False, endpoint='$(ENDPOINT)')"

invoke-stream: aws-auth
	@if [ -z "$(INPUT)" ]; then \
		echo "Usage: make invoke-stream INPUT=<msg> [ENDPOINT=dev|canary|prod] [SESSION_ID=<id>] [USER_ID=<id>]"; \
		exit 1; \
	fi
	$(eval ENDPOINT := $(or $(ENDPOINT),dev))
	$(eval ARN := $(shell cat cdk-outputs.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['DSPAgentStack']['RuntimeArn'])" 2>/dev/null || echo ""))
	@if [ -z "$(ARN)" ]; then \
		echo "Error: No deployment found. Run 'make deploy' first."; \
		exit 1; \
	fi
	@echo "Invoking $(ENDPOINT) endpoint (streaming)..."
	AGENT_RUNTIME_ARN=$(ARN) AGENT_ENDPOINT=$(ENDPOINT) uv run python -c "from scripts.invoke import main; main('$(INPUT)', $(if $(SESSION_ID),'$(SESSION_ID)',None), $(if $(USER_ID),'$(USER_ID)',None), stream=True, endpoint='$(ENDPOINT)')"

invoke-agui: aws-auth
	@if [ -z "$(INPUT)" ]; then \
		echo "Usage: make invoke-agui INPUT=<msg> [ENDPOINT=dev|canary|prod] [SESSION_ID=<id>] [USER_ID=<id>]"; \
		exit 1; \
	fi
	$(eval ENDPOINT := $(or $(ENDPOINT),dev))
	$(eval ARN := $(shell cat cdk-outputs.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['DSPAgentStack']['RuntimeArn'])" 2>/dev/null || echo ""))
	@if [ -z "$(ARN)" ]; then \
		echo "Error: No deployment found. Run 'make deploy' first."; \
		exit 1; \
	fi
	@echo "Invoking $(ENDPOINT) endpoint (AG-UI streaming)..."
	AGENT_RUNTIME_ARN=$(ARN) AGENT_ENDPOINT=$(ENDPOINT) uv run python -c "from scripts.invoke import main; main('$(INPUT)', $(if $(SESSION_ID),'$(SESSION_ID)',None), $(if $(USER_ID),'$(USER_ID)',None), stream_agui=True, endpoint='$(ENDPOINT)')"

chat:
	@echo "Starting interactive chat (make sure local server is running with 'make local')"
	uv run python -m yahoo_dsp_agent_sdk.chat --endpoint=invocations --default

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -f cdk-outputs*.json 2>/dev/null || true
