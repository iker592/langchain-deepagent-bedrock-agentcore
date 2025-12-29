#!/usr/bin/env python3
import sys
from pathlib import Path

from langchain_aws import ChatBedrock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agent_langchain import AgentLangchain


def simple_calculator(a: int, b: int, operation: str) -> str:
    """Perform simple arithmetic operations.

    Args:
        a: First number
        b: Second number
        operation: One of 'add', 'subtract', 'multiply', 'divide'
    """
    operations = {
        "add": a + b,
        "subtract": a - b,
        "multiply": a * b,
        "divide": a / b if b != 0 else "Error: Division by zero",
    }
    return str(operations.get(operation, "Error: Unknown operation"))


def greet(name: str) -> str:
    """Greet someone by name.

    Args:
        name: The name of the person to greet
    """
    return f"Hello, {name}! Nice to meet you."


def get_weather(city: str) -> str:
    """Get weather information for a city.

    Args:
        city: The city name
    """
    return f"The weather in {city} is sunny and 72°F."


def create_example_agent() -> AgentLangchain:
    """Create a configured LangChain agent with standard tools.

    Returns:
        Configured AgentLangchain instance
    """
    model = ChatBedrock(
        model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        region_name="us-west-2",
    )

    agent = AgentLangchain(
        model=model,
        system_prompt=(
            "You are a friendly assistant that helps with stories, greetings, "
            "weather, and calculations."
        ),
        tools=[greet, get_weather, simple_calculator],
    )

    return agent


if __name__ == "__main__":
    print("=== Testing Example LangChain Agent ===\n")

    agent = create_example_agent()

    print("Example 1: Greeting")
    structured_output, result = agent.invoke("Greet Alice")
    print(f"✅ Result: {result['messages'][-1].content if result['messages'] else 'N/A'}\n")

    print("Example 2: Calculation")
    structured_output, result = agent.invoke("What is 15 * 3?")
    print(f"✅ Result: {result['messages'][-1].content if result['messages'] else 'N/A'}\n")

    print("Example 3: Weather")
    structured_output, result = agent.invoke("What's the weather in Seattle?")
    print(f"✅ Result: {result['messages'][-1].content if result['messages'] else 'N/A'}\n")
