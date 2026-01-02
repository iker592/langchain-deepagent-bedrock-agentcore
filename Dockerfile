FROM ghcr.io/astral-sh/uv:latest AS uv

FROM --platform=linux/arm64 public.ecr.aws/docker/library/python:3.13-slim AS builder

ENV UV_COMPILE_BYTECODE=1
ENV UV_NO_INSTALLER_METADATA=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# Copy the local agent-sdk for the build
COPY agent-sdk /app/agent-sdk

RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv export --frozen --no-dev --no-editable -o requirements.txt && \
    uv pip install -r requirements.txt --system

FROM --platform=linux/arm64 public.ecr.aws/docker/library/python:3.13-slim AS runtime

# Build arg for selecting which agent to include (default: DSP agent)
ARG AGENT_PATH=./agents/dsp

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY ${AGENT_PATH} /app/agent

RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

# Expose both protocols: HTTP (8080) and A2A (9000)
EXPOSE 8080
EXPOSE 9000

CMD ["opentelemetry-instrument", "python", "-m", "agent.main"]
