# Serverless Deep Agent

A serverless AI agent built with **Amazon Bedrock AgentCore** + **DeepAgents** framework. Deploys to AWS as a fully managed runtime with conversation memory.

## 🚀 Quick Start

```bash
# Setup
make setup

# Run locally (no Docker)
make local

# Or with Docker
make start
```

## 📋 Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager
- Docker (for containerized development)
- AWS CLI + credentials (for deployment)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AWS Bedrock AgentCore                     │
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │  Agent Runtime  │───▶│  Bedrock LLM    │                 │
│  │  (DeepAgent)    │    │  (Claude)       │                 │
│  └─────────────────┘    └─────────────────┘                 │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐                                        │
│  │  Memory Store   │  (AgentCore Memory / MemorySaver)      │
│  └─────────────────┘                                        │
└─────────────────────────────────────────────────────────────┘
```

**Stack:**
- **[DeepAgents](https://github.com/anthropics/deepagents)** - AI agent framework with tool use
- **[LangGraph](https://github.com/langchain-ai/langgraph)** - Graph-based agent orchestration
- **[AWS Bedrock AgentCore](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)** - Serverless agent runtime
- **[AWS CDK](https://aws.amazon.com/cdk/)** - Infrastructure as Code

## 📁 Project Structure

```
.
├── agent/
│   ├── main.py           # Agent entrypoint (BedrockAgentCoreApp)
│   └── settings.py       # Configuration (Pydantic)
├── iac/
│   ├── app.py            # CDK app entry point
│   └── stack.py          # CDK stack (Runtime + Memory)
├── scripts/
│   └── invoke.py         # CLI to invoke deployed agent
├── .vscode/
│   └── launch.json       # Debug configuration
├── Dockerfile            # Container definition
├── docker-compose.yml    # Local Docker development
├── cdk.json              # CDK configuration
├── Makefile              # Task automation
└── pyproject.toml        # Python dependencies
```

## 🛠️ Available Commands

Run `make help` to see all commands:

```
Setup & Dependencies
  make setup       Install uv and sync dependencies
  make sync        Sync dependencies with uv
  make aws-auth    Setup AWS authentication (federate)

Code Quality
  make lint        Check code with ruff
  make format      Format code with ruff
  make fix         Format and fix linting issues

Docker Development
  make build       Build Docker image
  make start       Start container (detached)
  make restart     Rebuild and restart container
  make down        Stop and remove container
  make logs        Follow container logs
  make dev         Start with hot reload (watch mode)

Local Development
  make local       Run agent locally without Docker

Deployment
  make deploy      Deploy to AWS with CDK
  make invoke      Invoke deployed agent

Utilities
  make clean       Clean cache files
```

## 💻 Development Modes

### 1. Local (No Docker)

Fastest for development. Uses in-memory checkpointer.

```bash
make local
# Agent runs at http://localhost:8080
```

Test with:
```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello!", "user_id": "test"}'
```

### 2. Docker

Closer to production environment.

```bash
make start       # Start container
make logs        # View logs
make dev         # Hot reload mode
```

### 3. VS Code Debugging

Press **F5** to start debugging with breakpoints.

## ☁️ AWS Deployment

### Deploy

```bash
make aws-auth    # Authenticate (if using federated creds)
make deploy      # Deploy via CDK
```

Outputs:
- `RuntimeName`: Agent runtime ID
- `MemoryId`: Memory store ID

### Invoke Deployed Agent

```bash
make invoke \
  SESSION_ID="my-session-123456789012345678" \
  USER_ID="user-123" \
  INPUT="Hello, what can you do?" \
  ARN="arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:runtime/RUNTIME_ID"
```

### AWS Console Sandbox

1. Go to **Bedrock AgentCore** → **Agent runtimes** → Your agent
2. Click **Test endpoint**
3. Use JSON payload:
```json
{
  "input": "Hello!",
  "user_id": "12345"
}
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MODEL` | Bedrock model ID | Required |
| `AWS_REGION` | AWS region | `us-east-1` |
| `MEMORY_ID` | AgentCore Memory ID | Optional (local uses MemorySaver) |

### Local Development

```bash
MODEL=bedrock:us.anthropic.claude-haiku-4-5-20251001-v1:0 make local
```

### CDK Configuration

Edit `cdk.json` to change bootstrap qualifier:
```json
{
  "app": "uv run python -m iac.app",
  "context": {
    "@aws-cdk/core:bootstrapQualifier": "your-qualifier"
  }
}
```

## 🔧 Customization

### Change the Model

Edit `iac/stack.py`:
```python
environment_variables={
    "MODEL": "bedrock:global.anthropic.claude-sonnet-4-5-20250929-v1:0",
}
```

### Add Tools to the Agent

The DeepAgent comes with built-in tools (file ops, search, todo management). To add custom tools, modify `agent/main.py`:

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model=settings.model,
    checkpointer=MemorySaver(),
    # tools=[your_custom_tools],  # Add custom tools here
)
```

## 📚 Resources

- [DeepAgents Documentation](https://github.com/anthropics/deepagents)
- [AWS Bedrock AgentCore](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [AWS CDK Python](https://docs.aws.amazon.com/cdk/v2/guide/work-with-cdk-python.html)

## 📄 License

MIT
