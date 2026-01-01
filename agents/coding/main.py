import asyncio
import os
from logging import INFO, basicConfig, getLogger
from uuid import uuid4

import uvicorn
from bedrock_agentcore import BedrockAgentCoreApp
from fastapi import FastAPI
from strands.multiagent.a2a import A2AServer
from yahoo_dsp_agent_sdk.agent import Agent
from yahoo_dsp_agent_sdk.response_handler import handle_agent_response

from .agent import create_coding_agent
from .settings import Settings

basicConfig(level=INFO)
logger = getLogger(__name__)
settings = Settings()

# === HTTP Protocol (port 8080) ===
http_app = BedrockAgentCoreApp()


@http_app.entrypoint
async def invoke(payload, context):
    """HTTP endpoint at /invocations (port 8080)"""
    user_id = payload.get("user_id", str(uuid4()))
    session_id = (
        context.session_id
        if context and context.session_id
        else payload.get("session_id", "DEFAULT")
    )

    agent: Agent = create_coding_agent(
        memory_id=settings.memory_id,
        session_id=session_id,
        actor_id=user_id,
        region_name=settings.aws_region,
    )

    return await handle_agent_response(
        agent=agent,
        message=payload.get("input"),
        user_id=user_id,
        session_id=session_id,
        stream_agui=payload.get("stream_agui", False),
        stream=payload.get("stream", False),
        agentcore_mode=True,
    )


# === A2A Protocol (port 9000) ===
def create_a2a_app() -> FastAPI:
    """Create FastAPI app with A2A server mounted."""
    # For A2A, we use the underlying strands agent
    agent = create_coding_agent(
        memory_id=settings.memory_id,
        region_name=settings.aws_region,
    )

    runtime_url = os.environ.get(
        "AGENTCORE_RUNTIME_URL", settings.agentcore_runtime_url
    )

    a2a_server = A2AServer(
        agent=agent.agent,  # Use the underlying strands agent
        http_url=runtime_url,
        serve_at_root=True,
    )

    app = FastAPI(title="Coding Agent A2A")

    @app.get("/ping")
    def ping():
        return {"status": "healthy", "agent": "CodingAgent"}

    app.mount("/", a2a_server.to_fastapi_app())
    return app


async def run_servers():
    """Run both HTTP (8080) and A2A (9000) servers concurrently."""
    logger.info("Starting Coding Agent with HTTP (8080) and A2A (9000) protocols")

    # BedrockAgentCoreApp is itself an ASGI app (inherits from Starlette)
    http_config = uvicorn.Config(
        http_app,
        host="0.0.0.0",
        port=8080,
        log_level="info",
    )
    a2a_app = create_a2a_app()
    a2a_config = uvicorn.Config(
        a2a_app,
        host="0.0.0.0",
        port=9000,
        log_level="info",
    )

    await asyncio.gather(
        uvicorn.Server(http_config).serve(),
        uvicorn.Server(a2a_config).serve(),
    )


if __name__ == "__main__":
    asyncio.run(run_servers())
