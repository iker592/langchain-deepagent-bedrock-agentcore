import ast
import json
import time
import uuid
from abc import ABC
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Type, cast

from ag_ui.encoder import EventEncoder
from pydantic import BaseModel
from strands import Agent as StrandsAgent
from strands.agent.agent_result import AgentResult
from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands.hooks import HookProvider
from strands.models.bedrock import BedrockModel
from strands.session import SessionManager

from .agui_bridge import StrandsToAGUIBridge
from .exceptions import AgentExecutionError, MCPConnectionError
from .logger import get_logger
from .mcps import MCPManager

logger = get_logger(__name__)


class Agent(ABC):
    """
    Abstract base class for all agents in the system.

    Provides a standard interface that all agent implementations must follow
    to ensure consistent behavior and integration between agents.

    Agents can override the stream method for specific streaming responses:
    - stream: Asynchronous method for streaming responses
    """

    _conversation_manager = SlidingWindowConversationManager(
        window_size=20, should_truncate_results=False
    )

    def __init__(
        self,
        model: BedrockModel,
        system_prompt: str,
        tools: List[Any],
        hooks: List[HookProvider] = None,
        agent_id: str = None,
        description: str = None,
        structured_output_schema: Type[BaseModel] = None,
        structured_output_prompt: str = None,
        mcp_manager: Optional[MCPManager] = None,
        session_manager: Optional[SessionManager] = None,
    ) -> None:
        """
        Initialize the Agent.

        Args:
            model: Model to use for the agent
            system_prompt: System prompt for the agent
            tools: List of tools for the agent
            hooks: Optional hooks
            agent_id: Optional agent ID
            description: Optional description for A2A protocol
            structured_output_schema: Optional Pydantic model schema for structured output
            structured_output_prompt: Optional prompt string for structured output
            mcp_manager: Optional MCPManager for MCP lifecycle and retry configuration
            session_manager: Optional SessionManager for persistent memory (e.g., AgentCore)
        """
        if not agent_id:
            agent_id = f"{self.__class__.__name__}_{uuid.uuid4()}"

        self._mcp_manager = mcp_manager
        self._session_manager = session_manager
        self._agent_id_base = agent_id
        self._current_agent_id = agent_id
        self._model = model
        self._system_prompt = system_prompt
        self._hooks = hooks or []
        self._conversation_manager_instance = self._conversation_manager

        self.agent = StrandsAgent(
            model=model,
            system_prompt=system_prompt,
            tools=tools,
            conversation_manager=self._conversation_manager,
            session_manager=self._session_manager,
            hooks=self._hooks,
            callback_handler=None,
            agent_id=self._current_agent_id,
            description=description
            or system_prompt[:200],  # Use first 200 chars of system prompt as default
        )

        if structured_output_schema:
            self.structured_output_config = {
                "prompt": structured_output_prompt,
                "schema": structured_output_schema,
            }

        logger.debug(f"Agent {self._current_agent_id} initialized")

    def invoke(self, query: str, config: Dict[str, Any] = None) -> Tuple[BaseModel, AgentResult]:
        """
        Process a query synchronously. If mcp_manager is set, retries on MCP errors.

        Args:
            query: The user query to process
            config: Optional configuration dictionary

        Returns:
            Tuple of (structured_response, response)
        """
        if not self._mcp_manager:
            # Invocation without retry
            return self._do_invoke(query)

        max_retries = self._mcp_manager.max_retries
        retry_delay = self._mcp_manager.retry_delay
        last_error = None

        logger.info(f"Agent invoke started (max_retries={max_retries}, retry_delay={retry_delay}s)")

        for attempt in range(max_retries):
            try:
                logger.info(f"Agent invoke attempt {attempt + 1}/{max_retries}")
                result = self._do_invoke(query)
                if attempt > 0:
                    logger.info(f"Agent invoke succeeded after {attempt} retries")
                return result
            except MCPConnectionError as e:
                last_error = e
                if attempt < max_retries - 1:
                    self._wait_and_reconnect(attempt, retry_delay, e)
                    continue
                else:
                    logger.error(f"MCP error after {max_retries} attempts: {str(e)}")
                    raise AgentExecutionError(f"Agent failed after {max_retries} attempts: {e}")

        raise AgentExecutionError(f"Agent failed after {max_retries} attempts: {last_error}")

    def _do_invoke(self, query: str) -> Tuple[BaseModel, AgentResult]:
        """
        Execute a single agent invocation. Raises MCPConnectionError if detected.

        Args:
            query: The user query to process

        Returns:
            Tuple of (structured_response, response)
        """
        try:
            # Clear any previous MCP error state
            if hasattr(self.agent, "state"):
                self.agent.state.set("mcp_connection_error", None)

            response = self.agent(query)

            # Check if MCP error was detected during tool execution (via hooks)
            if hasattr(self.agent, "state"):
                mcp_error = self.agent.state.get("mcp_connection_error")
                if mcp_error:
                    raise MCPConnectionError(mcp_error)

            return self.get_structured_output(), response
        except MCPConnectionError:
            raise  # Re-raise for retry handling
        except Exception as e:
            logger.error(f"Error in agent invocation: {str(e)}")
            raise AgentExecutionError(f"Error in agent invocation: {str(e)}")

    async def stream_plain_text(
        self, query: str, config: Dict[str, Any] = None
    ) -> AsyncGenerator[str, None]:
        """
        Process a query with streaming response.

        Args:
            query: The user query to process
            config: Optional configuration dictionary

        Yields:
            Streaming response chunks as strings
        """
        try:
            async for event in self.agent.stream_async(query):
                if "data" in event and event["data"] is not None:
                    yield event["data"]
        except Exception as e:
            yield f"Error: {str(e)}"

    async def stream_with_agui_bridge(
        self, query: str, config: Dict[str, Any] = None
    ) -> AsyncGenerator[bytes, None]:
        """
        Process a query with streaming response using AG-UI protocol.

        Args:
            query: The user query to process
            config: Optional configuration dictionary

        Yields:
            Encoded AG-UI events as bytes (default: text/event-stream)
        """
        # Setup AG-UI event encoding (defaults to text/event-stream)
        encoder = EventEncoder()
        bridge = StrandsToAGUIBridge()

        # Get thread_id and user_id from config
        thread_id = config.get("thread_id", "default") if config else "default"
        user_id = config.get("user_id", config.get("userId", "default")) if config else "default"
        structured_result = None

        try:
            # Start AG-UI event sequence
            yield encoder.encode(bridge.start_run(thread_id, thread_id + "_" + user_id))
            yield encoder.encode(bridge.start_message())

            # Stream raw events from the Strands agent
            async for strands_event in self.agent.stream_async(query):
                # Convert Strands events to AG-UI events using bridge
                for agui_event in bridge.convert_strands_event(strands_event):
                    yield encoder.encode(agui_event)

            # After streaming completes, get structured output if available
            structured_result = await self.get_structured_output_async()

            # End AG-UI event sequence
            yield encoder.encode(bridge.end_message())
            yield encoder.encode(
                bridge.finish_run(thread_id, thread_id + "_" + user_id, result=structured_result)
            )

        except Exception as e:
            logger.error(f"Error in streaming: {str(e)}")
            yield encoder.encode(bridge.error_event(str(e)))

    def get_structured_output(self) -> Dict[str, Any] | None:
        """
        Get structured output synchronously after agent loop completes.
        Default implementation uses structured_output_config attribute if defined.

        Returns:
            Dictionary with structured output, or None if not applicable
        """
        if not (config := getattr(self, "structured_output_config", None)):
            return None

        try:
            # Get structured response from the agent
            structured_response: BaseModel = self.agent.structured_output(
                output_model=config["schema"],
                prompt=config.get("prompt"),
            )

            return structured_response.model_dump()
        except Exception as e:
            logger.error(f"Error getting structured output: {str(e)}")
            return None

    async def get_structured_output_async(self) -> Dict[str, Any] | None:
        """
        Get structured output asynchronously after agent loop completes.
        Default implementation uses structured_output_config attribute if defined.

        Returns:
            Dictionary with structured output, or None if not applicable
        """
        if not (config := getattr(self, "structured_output_config", None)):
            return None

        try:
            # Get structured response from the agent (async version)
            structured_response: BaseModel = await self.agent.structured_output_async(
                output_model=config["schema"],
                prompt=config.get("prompt"),
            )

            return structured_response.model_dump()
        except Exception as e:
            logger.error(f"Error getting structured output: {str(e)}")
            return None

    def _store_structured_response_in_state(self, structured_response: Any) -> None:
        """
        Process structured response and store results in agent state.

        Args:
            structured_response: The structured response from the agent
        """
        final_json_response = None
        tool_name = getattr(structured_response, "tool_name", None)

        if (
            hasattr(structured_response, "tool_call_response")
            and structured_response.tool_call_response
        ):
            try:
                # Convert Pydantic model to Python object then to JSON string
                python_obj = ast.literal_eval(structured_response.tool_call_response)
                final_json_response = json.dumps(python_obj)
            except (ValueError, SyntaxError):
                # If parsing fails, save as string
                final_json_response = str(structured_response.tool_call_response)

        # Store the final results in state
        self.agent = cast(StrandsAgent, self.agent)
        self.agent.state.set("structured_response", final_json_response)
        self.agent.state.set("tool_name", tool_name)

    def _extract_aggregated_structured_data(self, priority_agent: str) -> tuple[Any, Any]:
        """
        Extract aggregated structured data from agents' states and clear them.
        Automatically discovers all agents ending with "_agent".

        Args:
            priority_agent: The agent to prioritize in the extraction of aggregated structured data

        Returns:
            Tuple of (structured_response, tool_name)
        """
        # Automatically discover all agent attributes
        agents = []
        for attr_name in dir(self):
            if attr_name.endswith("_agent") and not attr_name.startswith("_"):
                agent_obj = getattr(self, attr_name)
                # Ensure the agent has the expected structure (agent.state)
                if hasattr(agent_obj, "agent") and hasattr(agent_obj.agent, "state"):
                    agents.append((attr_name, agent_obj.agent))

        # Check each agent for structured response data
        # Prioritize priority agent if found, otherwise return first available
        priority_agent_data = None
        first_available_data = None

        for agent_name, agent in agents:
            agent = cast(StrandsAgent, agent)
            structured_response = agent.state.get("structured_response")
            tool_name = agent.state.get("tool_name")

            if structured_response is not None:
                if first_available_data is None:
                    first_available_data = (structured_response, tool_name, agent_name, agent)

                # Prioritize priority agent data if found
                if priority_agent in agent_name:
                    priority_agent_data = (structured_response, tool_name, agent_name, agent)

        # Use priority agent data if available, otherwise use first available
        aggregated_data = priority_agent_data if priority_agent_data else first_available_data

        if aggregated_data:
            structured_response, tool_name, agent_name, agent = aggregated_data
            # Clear the agent's state
            agent.state.set("structured_response", None)
            agent.state.set("tool_name", None)
            logger.debug(f"Found structured response from {agent_name}")
            return structured_response, tool_name

        logger.debug("No structured response found from any agent")
        return None, None

    def _wait_and_reconnect(self, attempt: int, retry_delay: float, error: Exception) -> None:
        """
        Wait with exponential backoff and reconnect MCP.

        Args:
            attempt: Current retry attempt number (0-indexed)
            retry_delay: Base delay in seconds for exponential backoff
            error: The exception that triggered the retry
        """
        delay = retry_delay * (2**attempt)
        logger.warning(f"MCP error on attempt {attempt + 1}, retrying in {delay:.1f}s: {error}")
        time.sleep(delay)
        self._reconnect_mcp_and_recreate_agent()

    def _reconnect_mcp_and_recreate_agent(self) -> None:
        """
        Reconnect MCP clients and recreate agent with fresh tools.
        """
        if not self._mcp_manager:
            logger.warning("No MCP manager available, cannot reconnect")
            return

        logger.info("Reconnecting MCP and recreating agent with fresh tools")
        self._mcp_manager.reconnect_all()
        tools = self._mcp_manager.get_filtered_tools()
        self._create_strands_agent(tools)
        logger.info("Agent recreated successfully with fresh MCP connection")

    def _create_strands_agent(self, tools: List[Any]) -> None:
        """
        Create or recreate the internal Strands agent with the given tools.

        Args:
            tools: List of tools to use for the agent
        """
        self._current_agent_id = f"{self._agent_id_base}_{uuid.uuid4()}"
        self.agent = StrandsAgent(
            model=self._model,
            system_prompt=self._system_prompt,
            tools=tools,
            conversation_manager=self._conversation_manager_instance,
            session_manager=self._session_manager,
            hooks=self._hooks,
            callback_handler=None,
            agent_id=self._current_agent_id,
        )
        logger.debug(f"Strands agent recreated with ID: {self._current_agent_id}")
