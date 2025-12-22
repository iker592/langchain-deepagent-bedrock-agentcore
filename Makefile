.PHONY: help setup sync lint format fix build start restart down logs dev local deploy invoke invoke-stream invoke-agui chat clean aws-auth

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
	@echo "  Deployment & Invocation"
	@echo "    make deploy         Deploy to AWS with CDK"
	@echo "    make invoke         Invoke deployed agent (non-streaming)"
	@echo "    make invoke-stream  Invoke with plain text streaming"
	@echo "    make invoke-agui    Invoke with AG-UI protocol streaming"
	@echo "    make chat           Interactive streaming chat (local)"
	@echo "                        Usage: make invoke INPUT=<msg> [SESSION_ID=<id>] [USER_ID=<id>]"
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

deploy:
	uv run cdk deploy --require-approval never

invoke: aws-auth
	@if [ -z "$(INPUT)" ]; then \
		echo "Usage: make invoke INPUT=<msg> [SESSION_ID=<id>] [USER_ID=<id>]"; \
		exit 1; \
	fi
	@if [ -z "$(SESSION_ID)" ] || [ -z "$(USER_ID)" ]; then \
		echo " Note: SESSION_ID and USER_ID not provided. Using defaults (memory won't persist across invocations)."; \
	fi
	uv run python -c "from scripts.invoke import main; main('$(INPUT)', $(if $(SESSION_ID),'$(SESSION_ID)',None), $(if $(USER_ID),'$(USER_ID)',None), stream=False)"

invoke-stream: aws-auth
	@if [ -z "$(INPUT)" ]; then \
		echo "Usage: make invoke-stream INPUT=<msg> [SESSION_ID=<id>] [USER_ID=<id>]"; \
		exit 1; \
	fi
	@if [ -z "$(SESSION_ID)" ] || [ -z "$(USER_ID)" ]; then \
		echo " Note: SESSION_ID and USER_ID not provided. Using defaults (memory won't persist across invocations)."; \
	fi
	uv run python -c "from scripts.invoke import main; main('$(INPUT)', $(if $(SESSION_ID),'$(SESSION_ID)',None), $(if $(USER_ID),'$(USER_ID)',None), stream=True)"

invoke-agui: aws-auth
	@if [ -z "$(INPUT)" ]; then \
		echo "Usage: make invoke-agui INPUT=<msg> [SESSION_ID=<id>] [USER_ID=<id>]"; \
		exit 1; \
	fi
	@if [ -z "$(SESSION_ID)" ] || [ -z "$(USER_ID)" ]; then \
		echo " Note: SESSION_ID and USER_ID not provided. Using defaults (memory won't persist across invocations)."; \
	fi
	uv run python -c "from scripts.invoke import main; main('$(INPUT)', $(if $(SESSION_ID),'$(SESSION_ID)',None), $(if $(USER_ID),'$(USER_ID)',None), stream_agui=True)"

chat:
	@echo "Starting interactive chat (make sure local server is running with 'make local')"
	./scripts/chat_stream.sh --default

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

