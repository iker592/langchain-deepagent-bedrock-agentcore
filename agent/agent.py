import os
import sys
from pathlib import Path

import boto3
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import (
    AgentCoreMemorySessionManager,
)
from strands.models.bedrock import BedrockModel
from strands_tools import calculator

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from yahoo_dsp_agent_sdk.agent import Agent


def create_agent(
    memory_id: str | None = None,
    session_id: str | None = None,
    actor_id: str | None = None,
    region_name: str = "us-east-1",
    agent_id: str | None = None,
) -> Agent:
    """Create a configured Strands agent with standard tools and AgentCore Memory.

    Args:
        memory_id: AgentCore Memory ID (optional, uses MEMORY_ID env var)
        session_id: Session ID for memory (optional)
        actor_id: Actor/user ID for memory (optional)
        region_name: AWS region for memory
        agent_id: Consistent agent ID for memory persistence (optional)

    Returns:
        Configured Agent instance
    """
    memory_id = memory_id or os.environ.get("MEMORY_ID")

    session_manager = None
    if memory_id:
        config = AgentCoreMemoryConfig(
            memory_id=memory_id,
            session_id=session_id or "default-session",
            actor_id=actor_id or "default-actor",
        )
        session_manager = AgentCoreMemorySessionManager(
            agentcore_memory_config=config,
            region_name=region_name,
        )

    model = BedrockModel(
        model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        boto_session=boto3.Session(region_name="us-west-2"),
        temperature=0.0,
    )

    agent = Agent(
        model=model,
        system_prompt=(
            "You are a data analyst. You help users analyze data, perform calculations,"
            "and provide insights. Be precise and concise in your responses."
        ),
        tools=[calculator],
        session_manager=session_manager,
        agent_id=agent_id or "analyst-agent",
    )

    return agent


if __name__ == "__main__":
    print("=== Testing Analyst Agent ===\n")

    agent = create_agent()

    print("Example 1: Simple calculation")
    structured_output, result = agent.invoke("What is 15 * 3?")
    print(f"✅ Result: {result}\n")

    print("Example 2: Percentage calculation")
    structured_output, result = agent.invoke("What is 25% of 200?")
    print(f"✅ Result: {result}\n")

    print("Example 3: Growth analysis")
    structured_output, result = agent.invoke(
        "If revenue grew from 100 to 150, what's the percentage increase?"
    )
    print(f"✅ Result: {result}\n")
