import json
from logging import INFO, basicConfig, getLogger
from uuid import uuid4

from bedrock_agentcore import BedrockAgentCoreApp
from yahoo_dsp_agent_sdk.agent import Agent

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
    stream = payload.get("stream", False)
    stream_agui = payload.get("stream_agui", False)

    agent: Agent = create_agent(
        memory_id=settings.memory_id,
        session_id=session_id,
        actor_id=user_id,
        region_name=settings.aws_region,
    )

    user_message = payload.get("input")
    thread_id = payload.get("thread_id", session_id)
    config = {"thread_id": thread_id, "userId": user_id}

    if stream_agui:

        async def stream_agui_response():
            async for sse_event in agent.stream_with_agui_bridge(user_message, config):
                yield decode_sse(sse_event)

        return stream_agui_response()

    if stream:

        async def stream_response():
            yield {"type": "start", "session_id": session_id, "user_id": user_id}
            async for chunk in agent.stream_plain_text(user_message):
                yield {"type": "chunk", "content": chunk}
            yield {"type": "end"}

        return stream_response()

    structured_output, response = agent.invoke(user_message)
    content = str(response) if response else None
    logger.info(f"Response: {content}")
    return {
        "content": content,
        "structured_output": structured_output,
        "session_id": session_id,
        "user_id": user_id,
    }


def decode_sse(sse_data: str | bytes) -> dict:
    """Decode SSE 'data: {...}\\n\\n' format back to dict."""
    if isinstance(sse_data, bytes):
        sse_data = sse_data.decode("utf-8")
    json_str = sse_data.removeprefix("data: ").rstrip("\n")
    return json.loads(json_str)


if __name__ == "__main__":
    app.run()
