from dataclasses import dataclass
from typing import Any, Callable, List, Optional

from mcp.types import Tool as MCPTool
from strands.tools.mcp.mcp_agent_tool import MCPAgentTool
from strands.tools.mcp.mcp_client import PaginatedList
from strands.types._events import ToolResultEvent


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict
    handler: Callable[[dict], Any]
    tags: Optional[List[str]] = None


class MockToolBuilder:
    def __init__(self):
        self._tool_definitions: List[ToolDefinition] = []
        self._direct_call_handlers: dict[str, Callable[[], str]] = {}

    def add_tool(
        self,
        name: str,
        description: str,
        input_schema: dict,
        handler: Callable[[dict], Any],
        tags: Optional[List[str]] = None,
    ) -> "MockToolBuilder":
        self._tool_definitions.append(
            ToolDefinition(
                name=name,
                description=description,
                input_schema=input_schema,
                handler=handler,
                tags=tags,
            )
        )
        return self

    def add_direct_call_handler(
        self,
        name: str,
        handler: str | Callable[[], str],
    ) -> "MockToolBuilder":
        if callable(handler):
            self._direct_call_handlers[name] = handler
        else:
            self._direct_call_handlers[name] = lambda d=handler: d
        return self

    def get_direct_call_handlers(self) -> dict[str, Callable[[], str]]:
        return self._direct_call_handlers

    def build(self, mock_mcp_client) -> PaginatedList:
        tools = []
        for defn in self._tool_definitions:
            mcp_tool = MCPTool(
                name=defn.name,
                description=defn.description,
                inputSchema=defn.input_schema,
            )

            if defn.tags:
                mcp_tool.meta = {"_fastmcp": {"tags": defn.tags}}

            agent_tool = MCPAgentTool(mcp_tool=mcp_tool, mcp_client=mock_mcp_client)
            agent_tool.stream = self._create_mock_stream(defn.handler)
            tools.append(agent_tool)

        return PaginatedList(tools)

    @staticmethod
    def _create_mock_stream(handler: Callable[[dict], Any]):
        async def mock_stream(tool_use, invocation_state, **kwargs):
            data = handler(tool_use.get("input", {}))
            yield ToolResultEvent(
                {
                    "toolUseId": tool_use["toolUseId"],
                    "status": "success",
                    "content": [{"text": str(data)}],
                }
            )

        return mock_stream
