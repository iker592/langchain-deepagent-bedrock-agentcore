import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Type, Union

from ag_ui.encoder import EventEncoder
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel

from .agui_bridge import LangChainToAGUIBridge
from .exceptions import AgentExecutionError
from .logger import get_logger

logger = get_logger(__name__)


class AgentLangchain:
    """LangChain v1 agent with AG-UI protocol streaming support."""

    def __init__(
        self,
        model: Union[str, BaseChatModel],
        system_prompt: str,
        tools: List[Any],
        agent_id: Optional[str] = None,
        structured_output_schema: Optional[Type[BaseModel]] = None,
        model_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the LangChain agent.

        Args:
            model: Model identifier string or BaseChatModel instance
            system_prompt: System prompt for the agent
            tools: List of tools available to the agent
            agent_id: Optional custom agent ID
            structured_output_schema: Optional Pydantic model for structured output
            model_kwargs: Optional kwargs for model initialization
        """
        self.agent_id = agent_id or f"{self.__class__.__name__}_{uuid.uuid4()}"
        self.system_prompt = system_prompt
        self.structured_output_schema = structured_output_schema

        self.chat_model = self._initialize_model(model, model_kwargs)
        self.agent = self._create_agent(tools, system_prompt, structured_output_schema)

        logger.debug(f"AgentLangchain {self.agent_id} initialized")

    def _initialize_model(
        self, model: Union[str, BaseChatModel], model_kwargs: Optional[Dict[str, Any]]
    ) -> BaseChatModel:
        """Initialize the chat model from string or instance."""
        if isinstance(model, str):
            return init_chat_model(model, **(model_kwargs or {}))
        elif isinstance(model, BaseChatModel):
            return model
        raise ValueError(
            "model must be either a string model identifier or a BaseChatModel instance"
        )

    def _create_agent(
        self,
        tools: List[Any],
        system_prompt: str,
        structured_output_schema: Optional[Type[BaseModel]],
    ):
        """Create the LangChain agent with optional structured output."""
        agent_kwargs = {
            "model": self.chat_model,
            "tools": tools,
            "system_prompt": system_prompt,
        }

        if structured_output_schema:
            agent_kwargs["response_format"] = ToolStrategy(structured_output_schema)

        return create_agent(**agent_kwargs)

    @staticmethod
    def _build_messages(query: str) -> List[Dict[str, str]]:
        """Build message input for LangChain agent."""
        return [{"role": "user", "content": query}]

    @staticmethod
    def _extract_config_value(config: Optional[Dict[str, Any]], key: str, default: str) -> str:
        """Extract configuration value with fallback."""
        return config.get(key, default) if config else default

    @staticmethod
    def _generate_run_id(thread_id: str, user_id: str) -> str:
        """Generate a run ID from thread and user IDs."""
        return f"{thread_id}_{user_id}"

    def invoke(
        self, query: str, config: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[Dict], Any]:
        """Invoke the agent with a query and return structured output and full result.

        Args:
            query: The user query
            config: Optional configuration dict

        Returns:
            Tuple of (structured_output_dict, full_result)

        Raises:
            AgentExecutionError: If invocation fails
        """
        try:
            invoke_input = {"messages": self._build_messages(query)}
            result = self.agent.invoke(invoke_input, config=config)

            structured_response = None
            if self.structured_output_schema and "structured_response" in result:
                structured_response = result["structured_response"]
                if isinstance(structured_response, BaseModel):
                    structured_response = structured_response.model_dump()

            return structured_response, result

        except Exception as e:
            logger.error(f"Error in AgentLangchain invoke: {str(e)}")
            raise AgentExecutionError(f"Error in AgentLangchain invoke: {str(e)}")

    async def stream_plain_text(
        self, query: str, config: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """Stream plain text responses from the agent.

        Args:
            query: The user query
            config: Optional configuration dict

        Yields:
            Text chunks as they are generated
        """
        try:
            stream_input = {"messages": self._build_messages(query)}

            async for chunk in self.agent.astream(stream_input, config=config):
                if isinstance(chunk, dict) and "model" in chunk and "messages" in chunk["model"]:
                    for message in chunk["model"]["messages"]:
                        if hasattr(message, "content") and message.content:
                            if isinstance(message.content, str):
                                yield message.content

        except Exception as e:
            yield f"Error: {str(e)}"

    async def stream_with_agui_bridge(
        self, query: str, config: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[bytes, None]:
        """Stream responses with AG-UI protocol events.

        Args:
            query: The user query
            config: Optional configuration dict (should include thread_id and userId)

        Yields:
            Server-Sent Event formatted bytes
        """
        encoder = EventEncoder()
        bridge = LangChainToAGUIBridge()

        thread_id = self._extract_config_value(config, "thread_id", "default")
        user_id = self._extract_config_value(config, "userId", "default")
        run_id = self._generate_run_id(thread_id, user_id)

        try:
            yield encoder.encode(bridge.start_run(thread_id, run_id))
            yield encoder.encode(bridge.start_message())

            stream_input = {"messages": self._build_messages(query)}

            async for event in self.agent.astream_events(stream_input, version="v2", config=config):
                for agui_event in bridge.process_stream_event(event):
                    yield encoder.encode(agui_event)

            if bridge.current_tool_call_id:
                for event in bridge.end_tool_call():
                    yield encoder.encode(event)

            yield encoder.encode(bridge.end_message())
            yield encoder.encode(bridge.finish_run(thread_id, run_id))

        except Exception as e:
            logger.error(f"Error in streaming: {str(e)}")
            yield encoder.encode(bridge.error_event(str(e)))
