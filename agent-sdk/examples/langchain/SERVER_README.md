# FastAPI Server Examples

## Quick Start

### 1. Start the Server

```bash
cd /Users/iredondo/dev/agent-sdk
uv run python examples/fastapi_server.py
```

Server will start on `http://localhost:8001`
- Health check: `http://localhost:8001/health`
- API docs: `http://localhost:8001/docs`

### 2. Test Streaming

**Option A: Use the test script (recommended)**
```bash
# In another terminal:
./examples/test_streaming.sh "Tell me a story about a robot"
```

**Option B: Raw curl (see SSE events)**
```bash
curl -N -X POST http://localhost:8001/stream-chat \
  -H 'Content-Type: application/json' \
  -H 'userId: testuser' \
  -d '{
    "id": "test-123",
    "conversation": [
      {"role": "user", "message": "What is 25 * 17?", "metadata": {}}
    ],
    "show_tool_calls": true
  }'
```

**Option C: Interactive mode**
```bash
./examples/test_streaming.sh
# Then choose from menu or enter custom message
```

## Streaming Behavior

The implementation uses LangChain's `astream_events` API for token-level streaming:

- **Text responses**: Stream as model generates tokens
- **Tool calls**: Show tool name, arguments, and results in real-time
- **AG-UI protocol**: Full event stream with proper SSE format

### What You'll See

```
🚀 Run started
🤖 Assistant: Once upon a time, there was a robot named R2...
🔧 Tool: simple_calculator
   Args: {"a": 25, "b": 17, "operation": "add"}
   Result: 42
The answer is 42!
✅ Run completed
```

## Available Tools

The example agent has these tools:
- `simple_calculator(a, b, operation)` - Add, subtract, multiply, divide
- `greet(name)` - Greet someone by name
- `get_weather(city)` - Get weather info (mock data)

## Endpoints

### POST /stream-chat

**Headers:**
- `Content-Type: application/json`
- `userId: string` (optional)

**Request Body:**
```json
{
  "id": "unique-request-id",
  "conversation": [
    {
      "role": "user",
      "message": "Your query here",
      "metadata": {}
    }
  ],
  "show_tool_calls": true
}
```

**Response:**
- `Content-Type: text/event-stream`
- Server-Sent Events (SSE) format
- AG-UI protocol events

## Comparing with Troubleshooting Agent

This implementation mirrors your `stream_troubleshooting.py` pattern:

| Feature | Troubleshooting Agent | LangChain Agent |
|---------|----------------------|-----------------|
| Framework | Strands | LangChain v1 |
| Streaming API | `stream_with_agui_bridge()` | `astream_events()` |
| Token-level | ✅ Yes | ✅ Yes |
| Tool calls | ✅ Visible | ✅ Visible |
| Protocol | AG-UI | AG-UI |
| FastAPI | ✅ | ✅ |

## Notes

- The server requires `fastapi` and `uvicorn` (installed via `uv sync --extra server`)
- Token streaming depends on the model - Bedrock may group tokens
- Network buffering can affect perceived streaming speed
- Use `curl -N` (no buffering) for best results

