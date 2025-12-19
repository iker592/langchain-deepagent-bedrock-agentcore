.PHONY: setup sync lint format fix build start restart down logs dev local deploy invoke clean

setup:
	@command -v uv >/dev/null 2>&1 || { echo "Installing uv..."; curl -LsSf https://astral.sh/uv/install.sh | sh; }
	@$(MAKE) sync

sync:
	uv sync

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
	MODEL=bedrock:us.anthropic.claude-haiku-4-5-20251001-v1:0 uv run python -m agent.main

deploy:
	uv run cdk deploy --require-approval never

invoke:
	@if [ -z "$(SESSION_ID)" ] || [ -z "$(USER_ID)" ] || [ -z "$(INPUT)" ] || [ -z "$(ARN)" ]; then \
		echo "Usage: make invoke SESSION_ID=<id> USER_ID=<id> INPUT=<msg> ARN=<arn> [REGION=us-east-1]"; \
		exit 1; \
	fi
	uv run python -c "from scripts.invoke import main; main('$(SESSION_ID)', '$(USER_ID)', '$(INPUT)', '$(ARN)', '$(or $(REGION),us-east-1)')"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

