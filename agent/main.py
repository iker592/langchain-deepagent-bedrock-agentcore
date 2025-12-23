from logging import INFO, basicConfig, getLogger
from uuid import uuid4

from bedrock_agentcore import BedrockAgentCoreApp
from yahoo_dsp_agent_sdk.agent import Agent
from yahoo_dsp_agent_sdk.response_handler import handle_agent_response

from .agent import create_agent
from .settings import Settings

basicConfig(level=INFO)

logger = getLogger(__name__)
settings = Settings()
app = BedrockAgentCoreApp()


@app.entrypoint
async def invoke(payload, context):
    user_id = payload.get("user_id", str(uuid4()))
    session_id = (
        context.session_id
        if context and context.session_id
        else payload.get("session_id", "DEFAULT")
    )

    agent: Agent = create_agent(
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


if __name__ == "__main__":
    app.run()
