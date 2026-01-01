import ssl
import time
from typing import Callable, List, Optional

import httpx
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPAgentTool, MCPClient
from strands.types.exceptions import MCPClientInitializationError

from .exceptions import AgentExecutionError, MCPConnectionError
from .logger import get_logger

logger = get_logger(__name__)

# Consolidated list of MCP connection error indicators for retry detection
MCP_CONNECTION_ERROR_INDICATORS = [
    "connection closed",
    "connection refused",
    "peer closed connection",
    "incomplete chunked read",
    "client session is not running",
    "unable to connect",
    "all connection attempts failed",
    "connecterror",
    "client initialization failed",
    "mcp error",
    "mcpconnectionerror",
    "mcperror",
    "remote protocol error",
    "connection to the mcp server was closed",
]


def setup_stremeable_mcp_client(
    gateway_url: str,
    headers: Optional[dict[str, str]] = None,
    ssl_context: Optional[ssl.SSLContext] = None,
) -> MCPClient:
    """
    Setup the streamable HTTP MCP client with request headers and SSL verification.

    Args:
        gateway_url: URL of the MCP gateway server
        headers: Optional headers to pass to the MCP client
        ssl_context: Optional SSL context for SSL verification
    Returns:
        Initialized MCPClient instance
    """
    logger.info(f"Gateway Endpoint - MCP URL: {gateway_url}")

    if headers:
        logger.info(f"Using headers: {list(headers.keys())}")
    else:
        logger.warning("No headers provided")

    if ssl_context:
        logger.info("Using SSL context with CA verification for MCP connection")
    else:
        logger.info("No SSL context provided, using default verification")

    try:

        def create_httpx_client_with_ssl(
            headers: Optional[dict[str, str]] = None,
            timeout: Optional[httpx.Timeout] = None,
            auth: Optional[httpx.Auth] = None,
        ) -> httpx.AsyncClient:
            return httpx.AsyncClient(
                headers=headers,
                timeout=timeout,
                auth=auth,
                verify=ssl_context if ssl_context else True,
            )

        gateway_client = MCPClient(
            lambda: streamablehttp_client(
                gateway_url, headers=headers, httpx_client_factory=create_httpx_client_with_ssl
            )
        )

        gateway_client.start()
        logger.info("MCP client initialized successfully")
    except MCPClientInitializationError as e:
        raise MCPConnectionError(f"Error initializing streamable HTTP MCP client: {str(e)}")
    except Exception as e:
        logger.error(f"Error initializing streamable HTTP MCP client: {str(e)}")
        raise AgentExecutionError(f"Error initializing streamable HTTP MCP client: {str(e)}")

    return gateway_client


def setup_local_mcp_client(mcp_server_path: str) -> MCPClient:
    """
    Setup the local MCP client using stdio transport.
    Points to the demo MCP server for local development.

    Args:
        mcp_server_path: Path to the MCP server Python file

    Returns:
        Initialized MCPClient instance
    """
    try:
        mcp_client = MCPClient(
            lambda: stdio_client(
                StdioServerParameters(
                    command="python",
                    args=[mcp_server_path],
                )
            )
        )
        mcp_client.start()
    except MCPClientInitializationError as e:
        raise MCPConnectionError(f"Error initializing stdio MCP client: {str(e)}")
    except Exception as e:
        raise AgentExecutionError(f"Error initializing stdio MCP client: {str(e)}")

    return mcp_client


def call_mcp_tool(
    mcp_client: MCPClient,
    tool_name: str,
    tool_use_id: str,
    arguments: Optional[dict] = None,
) -> str:
    """
    Call an MCP tool.

    Args:
        mcp_client: MCP client instance
        tool_name: Name of the MCP tool to call
        tool_use_id: Use ID of the MCP tool to call
        arguments: Optional arguments to pass to the tool

    Returns:
        Result of the MCP tool call
    """
    try:
        logger.info(f"Calling MCP tool '{tool_name}'")
        result = mcp_client.call_tool_sync(
            tool_use_id=tool_use_id,
            name=tool_name,
            arguments=arguments if arguments is not None else {},
        )
        if (
            isinstance(result, dict)
            and result.get("status") == "error"
            and "content" in result
            and any(
                indicator in str(result["content"]).lower()
                for indicator in MCP_CONNECTION_ERROR_INDICATORS
            )
        ):
            raise MCPConnectionError(f"MCP connection error: {result}")

        if (
            isinstance(result, dict)
            and result.get("status") == "success"
            and "structuredContent" in result
            and "result" in result["structuredContent"]
        ):
            data = result["structuredContent"]["result"]
            logger.info(f"Successfully called MCP tool: {len(data)} bytes")
            return data

        raise AgentExecutionError("MCP tool returned unexpected structure")

    except MCPConnectionError as e:
        raise e
    except Exception as e:
        raise AgentExecutionError(f"Error calling MCP tool: {str(e)}")


def filter_tools(tools: List[MCPAgentTool], tags: List[str]) -> List[MCPAgentTool]:
    """
    Filter tools by tags.

    Args:
        tools: List of MCP tools to filter
        tags: List of tags to filter by (e.g., ["line", "deal"])

    Returns:
        Filtered list of tools matching any of the provided tags
    """
    filtered_tools = [
        tool
        for tool in tools
        if hasattr(tool.mcp_tool, "meta")
        and tool.mcp_tool.meta
        and tool.mcp_tool.meta.get("_fastmcp", {})
        and any(tag in tool.mcp_tool.meta.get("_fastmcp", {}).get("tags", []) for tag in tags)
    ]
    logger.info(f"Filtered {len(filtered_tools)} tools with tags {tags}")
    return filtered_tools


class MCPManager:
    """
    Manages MCP client lifecycle and provides reconnection capabilities.
    Handles both stdio and streamable-http transports.
    """

    def __init__(
        self,
        use_stdio: bool = False,
        mcp_server_path: Optional[str] = None,
        gateway_url: Optional[str] = None,
        headers_factory: Optional[Callable[[], dict[str, str]]] = None,
        ssl_context: Optional[ssl.SSLContext] = None,
        tool_filter_tags: Optional[List[str]] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize MCPManager with factory configuration.

        Args:
            use_stdio: Whether to use stdio transport (True) or streamable-http (False)
            mcp_server_path: Path to MCP server Python file (for stdio)
            gateway_url: URL of MCP gateway server (for streamable-http)
            headers_factory: Optional callable that returns headers dict (called on each connection)
            ssl_context: Optional SSL context for SSL verification
            tool_filter_tags: Optional list of tags to filter tools by
            max_retries: Maximum number of retry attempts for MCP connection errors (default: 3)
            retry_delay: Base delay in seconds for exponential backoff (default: 1.0)
        """
        self.use_stdio = use_stdio
        self.mcp_server_path = mcp_server_path
        self.gateway_url = gateway_url
        self.headers_factory = headers_factory
        self.ssl_context = ssl_context
        self.tool_tags = tool_filter_tags or []
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client: Optional[MCPClient] = None

    def create_client(self) -> MCPClient:
        """
        Create and start MCP client.
        Uses retry logic if server isn't ready.

        Returns:
            Initialized MCPClient instance
        """
        if self._client is None:
            self._create_client_with_retry()
        return self._client

    def _create_client_internal(self) -> MCPClient:
        """
        Internal method to create MCP client (without retry logic).
        Extracted from create_client() for reuse.

        Returns:
            Initialized MCPClient instance
        """
        if self.use_stdio:
            if not self.mcp_server_path:
                raise AgentExecutionError("mcp_server_path is required for stdio transport")
            return setup_local_mcp_client(self.mcp_server_path)
        else:
            if not self.gateway_url:
                raise AgentExecutionError("gateway_url is required for streamable-http transport")
            headers = self.headers_factory() if self.headers_factory else None
            return setup_stremeable_mcp_client(self.gateway_url, headers, self.ssl_context)

    def _create_client_with_retry(self) -> None:
        """
        Create MCP client with retry logic for when server isn't ready.
        Uses self.max_retries and self.retry_delay for configuration.
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                self._client = self._create_client_internal()
                logger.info(f"MCP client initialized successfully on attempt {attempt + 1}")
                return
            except MCPConnectionError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2**attempt)
                    logger.warning(
                        f"MCP server not ready on attempt {attempt + 1}/{self.max_retries}, "
                        f"retrying in {delay:.1f}s: {str(e)[:200]}"
                    )
                    time.sleep(delay)
                    continue
                else:
                    logger.error(
                        f"Failed to initialize MCP client after {attempt + 1} attempts: {str(e)}"
                    )
                    raise AgentExecutionError(
                        f"Error initializing MCP client after {self.max_retries} attempts: "
                        f"{str(last_error)}"
                    )

        # Should never reach here, but just in case
        raise AgentExecutionError(
            f"Failed to initialize MCP client after {self.max_retries} attempts: {str(last_error)}"
        )

    def reconnect_all(self) -> None:
        """
        Stop old client and create new one with retry.
        """
        self._client = None
        self._create_client_with_retry()
        logger.info("MCP client reconnected successfully")

    def get_tools(self) -> List[MCPAgentTool]:
        """
        Get all tools from current MCP client.

        Returns:
            List of MCP tools
        """
        if self._client is None:
            self.create_client()

        return self._client.list_tools_sync()

    def get_filtered_tools(self, tags: Optional[List[str]] = None) -> List[MCPAgentTool]:
        """
        Get filtered tools from current MCP client.

        Args:
            tags: Optional list of tags to filter by. If None, uses self.tool_tags.

        Returns:
            Filtered list of MCP tools
        """
        tools = self.get_tools()
        filter_tags = tags if tags is not None else self.tool_tags
        if filter_tags:
            return filter_tools(tools, filter_tags)
        return tools

    def call_tool(
        self,
        tool_name: str,
        tool_use_id: str,
        arguments: Optional[dict] = None,
    ) -> str:
        """
        Call an MCP tool using the managed client.

        Args:
            tool_name: Name of the MCP tool to call
            tool_use_id: Use ID of the MCP tool to call
            arguments: Optional arguments to pass to the tool

        Returns:
            Result of the MCP tool call as string
        """
        if self._client is None:
            self.create_client()

        try:
            return call_mcp_tool(self._client, tool_name, tool_use_id, arguments)
        except MCPConnectionError:
            self.reconnect_all()
            return call_mcp_tool(self._client, tool_name, tool_use_id, arguments)

    def stop(self) -> None:
        """
        Stop and cleanup MCP client.
        """
        self._client = None
