import sys
from pathlib import Path

import boto3
from strands.models.bedrock import BedrockModel
from strands.tools import tool

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agent import Agent


@tool
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


@tool
def greet(name: str) -> str:
    """Greet someone by name.

    Args:
        name: The name of the person to greet
    """
    return f"Hello, {name}! Nice to meet you."


@tool
def get_weather(city: str) -> str:
    """Get weather information for a city.

    Args:
        city: The city name
    """
    return f"The weather in {city} is sunny and 72°F."


def create_example_agent() -> Agent:
    """Create a configured Strands agent with standard tools.

    Returns:
        Configured Agent instance
    """
    model = BedrockModel(
        model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        boto_session=boto3.Session(region_name="us-west-2"),
        temperature=0.0,
    )

    agent = Agent(
        model=model,
        system_prompt=(
            "You are a friendly assistant that helps with stories, greetings, "
            "weather, and calculations."
        ),
        tools=[greet, get_weather, simple_calculator],
    )

    return agent


if __name__ == "__main__":
    print("=== Testing Example Strands Agent ===\n")

    agent = create_example_agent()

    print("Example 1: Greeting")
    structured_output, result = agent.invoke("Greet Alice")
    print(f"✅ Result: {result}\n")

    print("Example 2: Calculation")
    structured_output, result = agent.invoke("What is 15 * 3?")
    print(f"✅ Result: {result}\n")

    print("Example 3: Weather")
    structured_output, result = agent.invoke("What's the weather in Seattle?")
    print(f"✅ Result: {result}\n")
