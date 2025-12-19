from logging import INFO, basicConfig, getLogger
from uuid import uuid4

from bedrock_agentcore import BedrockAgentCoreApp
from yahoo_dsp_agent_sdk.agent import Agent

from .example_strands_agent import create_example_agent

basicConfig(level=INFO)

logger = getLogger(__name__)
app = BedrockAgentCoreApp()
agent: Agent = create_example_agent()


@app.entrypoint
async def invoke(payload, context):
    user_id = payload.get("user_id", str(uuid4()))
    session_id = (
        context.session_id
        if context and context.session_id
        else payload.get("session_id", "DEFAULT")
    )
    user_message = payload.get("input")
    structured_output, response = agent.invoke(user_message)
    logger.info(f"Response: {response}")
    return {
        "content": structured_output,
        "session_id": session_id,
        "user_id": user_id,
    }


if __name__ == "__main__":
    app.run()
