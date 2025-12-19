from logging import INFO, basicConfig, getLogger
from uuid import uuid4

from bedrock_agentcore import BedrockAgentCoreApp
from yahoo_dsp_agent_sdk.agent import Agent

from .example_strands_agent import create_example_agent
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

    agent: Agent = create_example_agent(
        memory_id=settings.memory_id,
        session_id=session_id,
        actor_id=user_id,
        region_name=settings.aws_region,
    )

    user_message = payload.get("input")
    structured_output, response = agent.invoke(user_message)
    content = str(response) if response else structured_output
    logger.info(f"Response: {content}")
    return {
        "content": content,
        "session_id": session_id,
        "user_id": user_id,
    }


if __name__ == "__main__":
    app.run()
