from typing import Optional

import uvicorn
from example_strands_agent import create_example_agent
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

app = FastAPI(title="Strands Agent API")


class Message(BaseModel):
    role: str
    message: str
    metadata: dict = Field(default_factory=dict)


class AgentRequest(BaseModel):
    id: str
    conversation: list[Message]
    show_tool_calls: bool = True


def get_user_id(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    user_id_legacy: Optional[str] = Header(None, alias="userId"),
) -> str:
    """Get user ID from either X-User-Id or userId header."""
    user_id = x_user_id or user_id_legacy
    if not user_id:
        raise HTTPException(
            status_code=400, detail="User ID header is required (X-User-Id or userId)"
        )
    return user_id


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/stream-chat")
async def stream_chat(
    request: AgentRequest,
    userId: Optional[str] = Header(None),
):
    """Streaming endpoint for Strands agent."""
    agent = create_example_agent()
    last_message = request.conversation[-1].message if request.conversation else ""

    async def generate():
        async for event in agent.stream_with_agui_bridge(
            last_message, config={"thread_id": request.id, "userId": userId or "anonymous"}
        ):
            yield event

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    print("🚀 Starting Strands Agent API server...")
    print("📍 Server will be available at: http://localhost:8000")
    print("📖 API docs at: http://localhost:8000/docs")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
