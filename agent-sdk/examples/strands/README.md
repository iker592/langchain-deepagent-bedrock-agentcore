# Strands Agent Examples

This directory contains examples demonstrating how to use the Strands `Agent` implementation.

## Interactive CLI

Run the interactive chat CLI:

```bash
uv run python examples/strands/chat_cli.py
```

This CLI uses `stream_plain_text()` and `invoke()` methods for an interactive chat session.

### Features

The CLI provides an interactive session where you can:

1. **Normal chat**: Just type your message and press Enter
   ```
   👤 You: What's 5 + 3?
   🤖 Assistant: 8
   ```

2. **Streaming responses**: Prefix your message with `stream`
   ```
   👤 You: stream Tell me about AI
   🤖 Assistant: [response streams in real-time]
   ```

3. **Tool usage**: The agent has access to:
   - `greet(name)` - Greet someone by name
   - `get_weather(city)` - Get weather info for a city
   - `simple_calculator(a, b, operation)` - Perform calculations

4. **Commands**:
   - `quit` or `exit` - Exit the CLI
   - `clear` - Clear the screen

### Example Session

```
🚀 Strands Agent CLI
====================================
✅ Agent ready!

👤 You: Greet Alice
🤖 Assistant: Hello, Alice! Nice to meet you.

👤 You: stream Calculate 15 * 8
🤖 Assistant: 120

👤 You: quit
👋 Goodbye!
```

## Programmatic Example

See `example_strands_agent.py` for a reusable agent configuration used across all examples.

This file provides:
- `create_example_agent()` - Factory function to create a configured agent
- Standard tool definitions (`greet`, `get_weather`, `simple_calculator`)
- Example usage when run directly

Run it:

```bash
uv run python examples/strands/example_strands_agent.py
```

Example code:

```python
from example_strands_agent import create_example_agent

agent = create_example_agent()
structured_output, result = agent.invoke("Greet John")
```

## FastAPI Server

For production-ready streaming with AG-UI protocol, the FastAPI server is available.

The server provides:
- Token-level streaming with SSE
- Full AG-UI protocol support
- Tool call visibility
- RESTful API endpoints

Start the server:

```bash
uv run python examples/strands/fastapi_server.py
```

Test streaming:

```bash
./examples/strands/test_streaming.sh "Calculate 10 + 5"
```

**Note:** The Strands server runs on port **8000**.

## Requirements

- Valid AWS credentials configured
- Access to AWS Bedrock Claude models
- Dependencies installed via `uv sync`

## Key Features

- **Tools**: Uses `@tool` decorator from `strands.tools`
- **Model**: Uses `BedrockModel` from `strands.models.bedrock`
- **Result**: Returns `AgentResult` object
- **Server Port**: 8000

