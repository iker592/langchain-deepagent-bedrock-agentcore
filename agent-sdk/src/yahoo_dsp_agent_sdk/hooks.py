from typing import Any

from strands.experimental.hooks import AfterToolInvocationEvent, BeforeToolInvocationEvent
from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import AfterInvocationEvent, BeforeInvocationEvent, MessageAddedEvent

from .logger import get_logger
from .mcps import MCP_CONNECTION_ERROR_INDICATORS

logger = get_logger(__name__)


class AgentHookProvider(HookProvider):
    """
    Default Hook Provider for agent lifecycle events.

    Provided hooks:
    - Agent invocation start/end
    - Tool usage and results
    - Message additions to conversation history

    Agents can inherit this class and override these hooks to add custom logging or behavior.
    Additionally, agents can define their own hooks and register them by extending register_hooks.
    """

    def __init__(self, agent_name: str):
        """
        Initialize the Agent hook provider.

        Args:
            agent_name: Name of the agent for logging
        """
        self.agent_name = agent_name

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        """
        Register all hook callbacks for the agent.

        Args:
            registry: The hook registry to register callbacks with
        """
        registry.add_callback(BeforeInvocationEvent, self.invocation_start)
        registry.add_callback(AfterInvocationEvent, self.invocation_end)
        registry.add_callback(MessageAddedEvent, self.message_added)
        registry.add_callback(BeforeToolInvocationEvent, self.tool_invocation_start)
        registry.add_callback(AfterToolInvocationEvent, self.tool_invocation_end)

    def invocation_start(self, event: BeforeInvocationEvent) -> None:
        """
        Start of agent invocation.

        Args:
            event: The before invocation event
        """
        logger.info(f"{self.agent_name} invocation started")
        logger.info(f"Agent ID: {getattr(event.agent, 'agent_id', 'unknown')}")

        # Log session information if available
        if hasattr(event.agent, "_session_manager") and event.agent._session_manager:
            session_id = getattr(event.agent._session_manager, "session_id", "unknown")
            logger.debug(f"Session ID: {session_id}")

        # Log available tools if present
        if hasattr(event.agent, "tool_names") and event.agent.tool_names:
            logger.debug(f"Available tools: {event.agent.tool_names}")

    def invocation_end(self, event: AfterInvocationEvent) -> None:
        """
        End of agent invocation.

        Args:
            event: The after invocation event
        """
        logger.info(f"{self.agent_name} invocation completed")

        # Log conversation state
        if hasattr(event.agent, "conversation_manager") and event.agent.conversation_manager:
            logger.debug(f"Conversation state: {event.agent.conversation_manager.get_state()}")

    def message_added(self, event: MessageAddedEvent) -> None:
        """
        Message is added to the agent conversation.

        Args:
            event: The message added event
        """
        message_type = event.message.get("role", "unknown")
        content = str(event.message.get("content", ""))

        logger.debug(
            f"{self.agent_name} message, type: {message_type}, content: {content[:100]}..."
        )

        # Log tool calls
        for block in event.message.get("content", []):
            tool_use = block.get("toolUse") if isinstance(block, dict) else None
            if tool_use:
                logger.debug(f"Tool: {tool_use.get('name')}, input: {tool_use.get('input')}")

    def tool_invocation_start(self, event: BeforeToolInvocationEvent) -> None:
        """
        Start of a tool invocation.

        Args:
            event: The before tool invocation event
        """
        tool_name = event.tool_use.get("name", "unknown")
        tool_input = event.tool_use.get("input", {})

        logger.info(f"{self.agent_name} invoking tool: {tool_name}")
        logger.debug(f"Tool input: {tool_input}")

    def tool_invocation_end(self, event: AfterToolInvocationEvent) -> None:
        """
        End of a tool invocation.

        Args:
            event: The after tool invocation event
        """
        tool_name = event.tool_use.get("name", "unknown")

        logger.info(f"{self.agent_name} tool '{tool_name}' completed")

        # Log all event attributes for debugging
        logger.debug(f"Tool '{tool_name}' event attributes: {dir(event)}")

        # Log result summary
        result = getattr(event, "result", None)
        if result:
            logger.debug(f"Tool result type: {type(result)}, value: {result}")

        # Check for MCP connection errors and store them to trigger retry after invocation
        # Note: Hooks cannot stop invocation by raising, so we store in state for invoke()
        mcp_error_message = self._detect_mcp_error(tool_name, result)

        if mcp_error_message:
            agent = getattr(event, "agent", None)
            if agent and hasattr(agent, "state"):
                agent.state.set("mcp_connection_error", mcp_error_message)
                logger.debug(f"Stored MCP error in agent state: {mcp_error_message}")

    def _detect_mcp_error(self, tool_name: str, result: Any) -> str | None:
        """
        Detect MCP connection errors from tool result.

        Args:
            tool_name: Name of the tool that was invoked
            result: Result from the tool invocation

        Returns:
            Error message if MCP error detected, None otherwise
        """
        if result:
            result_str = str(result).lower()

            if any(indicator in result_str for indicator in MCP_CONNECTION_ERROR_INDICATORS):
                logger.warning(f"MCP error in tool '{tool_name}' result: {result_str[:200]}")
                return f"MCP connection error in tool '{tool_name}': {result_str}"

        return None
