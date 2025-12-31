import os

import boto3
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import (
    AgentCoreMemorySessionManager,
)
from strands.models.bedrock import BedrockModel
from strands_tools import calculator, python_repl
from yahoo_dsp_agent_sdk.agent import Agent


def create_coding_agent(
    memory_id: str | None = None,
    session_id: str | None = None,
    actor_id: str | None = None,
    region_name: str = "us-east-1",
) -> Agent:
    """Create a Coding Agent specialized in writing and executing code."""
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
            "You are a Coding Agent specialized in writing Python code, "
            "debugging, and solving programming problems. You can execute "
            "Python code to verify your solutions. Write clean, "
            "well-documented code and explain your approach."
        ),
        tools=[calculator, python_repl],
        session_manager=session_manager,
        agent_id="coding-agent",
        description="Coding Agent for Python programming and debugging.",
    )

    return agent
