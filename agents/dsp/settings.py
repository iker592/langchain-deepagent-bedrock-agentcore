from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    aws_region: str = "us-east-1"
    memory_id: str | None = None
    model: str = "bedrock:us.anthropic.claude-haiku-4-5-20251001-v1:0"
    agent_runtime_arn: str | None = None
    environment: str = "dev"
