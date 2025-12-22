from logging import INFO, basicConfig, getLogger
from uuid import uuid4

from bedrock_agentcore import BedrockAgentCoreApp
from yahoo_dsp_agent_sdk.agent import Agent
from yahoo_dsp_agent_sdk.agui_bridge import StrandsToAGUIBridge

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
    run_id = f"{thread_id}_{user_id}"

    if stream_agui:

        async def stream_agui_response():
            bridge = StrandsToAGUIBridge()
            yield bridge.start_run(thread_id, run_id).model_dump()
            yield bridge.start_message().model_dump()

            async for strands_event in agent.agent.stream_async(user_message):
                for agui_event in bridge.convert_strands_event(strands_event):
                    yield agui_event.model_dump()

            yield bridge.end_message().model_dump()
            yield bridge.finish_run(thread_id, run_id).model_dump()

        return stream_agui_response()

    if stream:

        async def stream_response():
            yield {"type": "start", "session_id": session_id, "user_id": user_id}
            async for chunk in agent.stream_plain_text(user_message):
                yield {"type": "chunk", "content": chunk}
            yield {"type": "end"}

        return stream_response()

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
