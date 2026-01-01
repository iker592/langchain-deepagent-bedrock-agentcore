import asyncio

from example_strands_agent import create_example_agent

from yahoo_dsp_agent_sdk.agent import Agent


async def stream_response(agent: Agent, query: str) -> None:
    print("\n🤖 Assistant: ", end="", flush=True)
    async for chunk in agent.stream_plain_text(query):
        print(chunk, end="", flush=True)
    print("\n")


def sync_response(agent: Agent, query: str) -> None:
    print("\n🤖 Assistant: ")
    structured_response, result = agent.invoke(query)
    print(f"{result}")

    if structured_response:
        print(f"\n📊 Structured Response: {structured_response}")
    print()


async def main():
    print("=" * 60)
    print("🚀 Strands Agent CLI")
    print("=" * 60)
    print("\nInitializing agent...")

    agent = create_example_agent()

    print("✅ Agent ready!\n")
    print("Commands:")
    print("  - Type your message to chat")
    print("  - 'stream <message>' for streaming response")
    print("  - 'quit' or 'exit' to leave")
    print("  - 'clear' to clear screen")
    print()

    while True:
        try:
            user_input = input("👤 You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit", "q"]:
                print("\n👋 Goodbye!")
                break

            if user_input.lower() == "clear":
                print("\033[2J\033[H", end="")
                continue

            if user_input.lower().startswith("stream "):
                query = user_input[7:]
                await stream_response(agent, query)
            else:
                sync_response(agent, user_input)

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")


if __name__ == "__main__":
    asyncio.run(main())
