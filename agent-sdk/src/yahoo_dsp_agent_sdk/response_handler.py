import json
from typing import Any, AsyncGenerator, Dict, Union

from .agent import Agent
from .logger import get_logger

logger = get_logger(__name__)


async def handle_agent_response(
    agent: Agent,
    message: str,
    user_id: str,
    session_id: str,
    stream_agui: bool = False,
    stream: bool = False,
    agentcore_mode: bool = False,
) -> Union[AsyncGenerator[Dict[str, Any], None], AsyncGenerator[str, None], Dict[str, Any]]:
    """
    Handle agent response based on the requested mode.

    Args:
        agent: The agent instance to invoke
        message: The user message to process
        config: Configuration dict with thread_id, user_id, session_id, etc.
        stream_agui: If True, return AG-UI protocol streaming response
        stream: If True, return plain text streaming response
        agentcore_mode: If True, decode SSE to dicts (for BedrockAgentCoreApp).
                        If False, yield raw SSE strings (for FastAPI StreamingResponse).

    Returns:
        AsyncGenerator yielding dicts (agentcore_mode) or SSE strings, or dict for sync mode
    """
    config = {
        "thread_id": session_id,
        "user_id": user_id,
    }
    if stream_agui:

        async def stream_agui_response():
            async for sse_event in agent.stream_with_agui_bridge(message, config):
                yield decode_sse(sse_event) if agentcore_mode else sse_event

        return stream_agui_response()

    if stream:

        async def stream_response():
            async for chunk in agent.stream_plain_text(message):
                yield chunk

        return stream_response()

    structured_output, response = agent.invoke(message)
    content = str(response) if response else None
    logger.info(f"Response: {content}")
    return {
        "content": content,
        "structured_output": structured_output,
        "session_id": session_id,
        "user_id": user_id,
    }


def decode_sse(sse_data: Union[str, bytes]) -> dict:
    """Decode SSE 'data: {...}\\n\\n' format back to dict."""
    if isinstance(sse_data, bytes):
        sse_data = sse_data.decode("utf-8")
    json_str = sse_data.removeprefix("data: ").rstrip("\n")
    return json.loads(json_str)
