import os

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end tests")


@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("MEMORY_ID", "test-memory-id")
    monkeypatch.setenv("MODEL", "bedrock:us.anthropic.claude-haiku-4-5-20251001-v1:0")


@pytest.fixture
def deployed_runtime_arn():
    arn = os.environ.get("AGENT_RUNTIME_ARN")
    if not arn:
        pytest.skip("AGENT_RUNTIME_ARN not set - skipping e2e test")
    return arn


@pytest.fixture
def agent_endpoint():
    return os.environ.get("AGENT_ENDPOINT", "dev")
