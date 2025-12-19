# Serverless Strands Agent

A serverless AI agent built with **Amazon Bedrock AgentCore** + **Strands Agents** + **Yahoo DSP Agent SDK**.  
Deploys to AWS as a fully managed runtime with persistent conversation memory.

## 🚀 Quick Start

```bash
# Setup
make setup

# Run locally with memory
make local MEMORY_ID=your-memory-id

# Or without memory (in-memory only)
make local

# Or with Docker
make start

# Once you are ready, deploy to AWS
make deploy
```

## 📋 Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager
- Docker/Rancher (for containerized development and CDK deployment)
- AWS CLI + credentials

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AWS Bedrock AgentCore                    │
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │  Agent Runtime  │───▶│  Bedrock LLM    │                 │
│  │  (Strands)      │    │  (Claude)       │                 │
│  └─────────────────┘    └─────────────────┘                 │
│           │                                                 │
│           ▼                                                 │
│  ┌─────────────────┐                                        │
│  │  AgentCore      │  (Persistent conversation memory)      │
│  │  Memory         │                                        │
│  └─────────────────┘                                        │
└─────────────────────────────────────────────────────────────┘
```

**Stack:**
- **[Strands Agents](https://strandsagents.com/)** - AI agent framework
- **[yahoo-dsp-agent-sdk](https://git.ouryahoo.com/iredondo/agent-sdk)** - Yahoo Agent SDK
- **[AWS Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/)** - Serverless agent runtime
- **[AgentCore Memory](https://strandsagents.com/latest/documentation/docs/community/session-managers/agentcore-memory/)** - Persistent session management
- **[AWS CDK](https://aws.amazon.com/cdk/)** - Infrastructure as Code

## 📁 Project Structure

```
.
├── agent/
│   ├── main.py                 # Agent entrypoint (BedrockAgentCoreApp)
│   ├── example_strands_agent.py # Agent configuration with tools
│   └── settings.py             # Configuration (Pydantic)
├── iac/
│   ├── app.py                  # CDK app entry point
│   └── stack.py                # CDK stack (Runtime + Memory)
├── scripts/
│   └── invoke.py               # CLI to invoke deployed agent
├── .vscode/
│   ├── launch.json             # Debug configuration
│   └── settings.json           # Ruff formatter settings
├── Dockerfile                  # Container definition
├── docker-compose.yml          # Local Docker development
├── cdk.json                    # CDK configuration
├── Makefile                    # Task automation
└── pyproject.toml              # Python dependencies
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

### 1. Local with Memory

Uses AgentCore Memory for persistent conversations across requests.

```bash
make local MEMORY_ID=memory-YkJACvBGME
# Agent runs at http://localhost:8080
```

### 2. Local without Memory

Uses in-memory storage (conversations reset on restart).

```bash
make local
```

### 3. Test the Agent

```bash
# First message
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello! My name is Iker", "user_id": "iker", "session_id": "test-session"}'

# Memory test - should remember the name
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"input": "What is my name?", "user_id": "iker", "session_id": "test-session"}'
```

### 4. Docker

Closer to production environment.

```bash
make start       # Start container
make logs        # View logs
make dev         # Hot reload mode
```

### 5. VS Code Debugging

Press **F5** to start debugging with breakpoints.

## ☁️ AWS Deployment

### Deploy

```bash
make aws-auth    # Authenticate
make deploy      # Deploy via CDK
```

Outputs:
- `RuntimeName`: Agent runtime ID (e.g., `deep_agent-grrXst44Ca`)
- `MemoryId`: Memory store ID (e.g., `memory-YkJACvBGME`)

### Invoke Deployed Agent

```bash
make invoke \
  SESSION_ID="my-session-123456789012345678" \
  USER_ID="user-123" \
  INPUT="Hello, what can you do?" \
  ARN="arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:runtime/RUNTIME_ID"
```

**Note:** Session ID must be at least 33 characters.

### AWS Console Sandbox

Test your deployed agent directly from the AWS Console:

1. Go to **Bedrock AgentCore**
2. Go to **Test/Agent Sandbox** in the left sidebar
3. Select your agent from the dropdown (`deep_agent`)
5. Choose **Endpoint**: `DEFAULT`
6. Paste this JSON payload in the **Input** field:

```json
{
  "input": "Hello!",
  "user_id": "console-user",
  "session_id": "console-session-123456789012345678"
}
```

7. Click **▶ Run**
8. View response in the **Output** section

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MODEL` | Bedrock model ID | Required |
| `AWS_REGION` | AWS region | `us-east-1` |
| `MEMORY_ID` | AgentCore Memory ID | Optional (uses in-memory if not set) |

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

### Memory Strategies

AgentCore Memory supports advanced strategies:
- **Short-term memory (STM)**: Conversation persistence within sessions
- **Long-term memory (LTM)**: User preferences, facts, session summaries

See [AgentCore Memory documentation](https://strandsagents.com/latest/documentation/docs/community/session-managers/agentcore-memory/).

## 📚 Resources

- [Strands Agents Documentation](https://strandsagents.com/)
- [AgentCore Memory Session Manager](https://strandsagents.com/latest/documentation/docs/community/session-managers/agentcore-memory/)
- [AWS Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/)
- [AWS CDK Python](https://docs.aws.amazon.com/cdk/v2/guide/work-with-cdk-python.html)

## 📄 License

MIT
