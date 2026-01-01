import pytest
from src.exceptions import AgentExecutionError
from src.mcps import (
    call_mcp_tool,
    filter_tools,
    setup_local_mcp_client,
    setup_stremeable_mcp_client,
)
from strands.tools.mcp.mcp_agent_tool import MCPAgentTool
from strands.tools.mcp.mcp_client import MCPClient


@pytest.fixture
def mock_mcp_client(mocker):
    client = mocker.Mock(spec=MCPClient)
    return client


@pytest.fixture
def mock_mcp_tools(mocker):
    tool1 = mocker.Mock(spec=MCPAgentTool)
    tool1.mcp_tool = mocker.Mock()
    tool1.mcp_tool.meta = {"_fastmcp": {"tags": ["line"]}}
    tool1.mcp_tool.name = "test_tool_line"

    tool2 = mocker.Mock(spec=MCPAgentTool)
    tool2.mcp_tool = mocker.Mock()
    tool2.mcp_tool.meta = {"_fastmcp": {"tags": ["deal"]}}
    tool2.mcp_tool.name = "test_tool_deal"

    tool3 = mocker.Mock(spec=MCPAgentTool)
    tool3.mcp_tool = mocker.Mock()
    tool3.mcp_tool.meta = {"_fastmcp": {"tags": ["line", "deal"]}}
    tool3.mcp_tool.name = "test_tool_both"

    return [tool1, tool2, tool3]


@pytest.fixture
def mock_ssl_context(mocker):
    return mocker.MagicMock()


class TestFilterTools:
    def test_filter_tools_by_single_tag_line(self, mock_mcp_tools):
        filtered = filter_tools(mock_mcp_tools, ["line"])

        assert len(filtered) == 2
        assert all("line" in tool.mcp_tool.meta["_fastmcp"]["tags"] for tool in filtered)

    def test_filter_tools_by_single_tag_deal(self, mock_mcp_tools):
        filtered = filter_tools(mock_mcp_tools, ["deal"])

        assert len(filtered) == 2
        assert all("deal" in tool.mcp_tool.meta["_fastmcp"]["tags"] for tool in filtered)

    def test_filter_tools_by_multiple_tags(self, mock_mcp_tools):
        filtered = filter_tools(mock_mcp_tools, ["line", "deal"])

        assert len(filtered) == 3
        assert any("line" in tool.mcp_tool.meta["_fastmcp"]["tags"] for tool in filtered)
        assert any("deal" in tool.mcp_tool.meta["_fastmcp"]["tags"] for tool in filtered)

    def test_filter_tools_no_matches(self, mock_mcp_tools):
        filtered = filter_tools(mock_mcp_tools, ["nonexistent_tag"])

        assert len(filtered) == 0

    def test_filter_tools_with_missing_meta(self, mocker):
        tool_no_meta = mocker.Mock(spec=MCPAgentTool)
        tool_no_meta.mcp_tool = mocker.Mock()
        delattr(tool_no_meta.mcp_tool, "meta")

        tools = [tool_no_meta]
        filtered = filter_tools(tools, ["line"])

        assert len(filtered) == 0

    def test_filter_tools_with_none_meta(self, mocker):
        tool_none_meta = mocker.Mock(spec=MCPAgentTool)
        tool_none_meta.mcp_tool = mocker.Mock()
        tool_none_meta.mcp_tool.meta = None

        tools = [tool_none_meta]
        filtered = filter_tools(tools, ["line"])

        assert len(filtered) == 0

    def test_filter_tools_with_missing_fastmcp(self, mocker):
        tool_no_fastmcp = mocker.Mock(spec=MCPAgentTool)
        tool_no_fastmcp.mcp_tool = mocker.Mock()
        tool_no_fastmcp.mcp_tool.meta = {"other": "data"}

        tools = [tool_no_fastmcp]
        filtered = filter_tools(tools, ["line"])

        assert len(filtered) == 0

    def test_filter_tools_empty_tag_list(self, mock_mcp_tools):
        filtered = filter_tools(mock_mcp_tools, [])

        assert len(filtered) == 0


class TestCallMCPTool:
    def test_successful_mcp_tool_call(self, mock_mcp_client):
        mock_result = {
            "status": "success",
            "structuredContent": {"result": "mock_tool_data"},
        }
        mock_mcp_client.call_tool_sync.return_value = mock_result

        result = call_mcp_tool(mock_mcp_client, "test_tool", "test_id")

        assert result == "mock_tool_data"
        mock_mcp_client.call_tool_sync.assert_called_once_with(
            tool_use_id="test_id", name="test_tool", arguments={}
        )

    def test_successful_mcp_tool_call_with_arguments(self, mock_mcp_client):
        mock_result = {
            "status": "success",
            "structuredContent": {"result": "mock_tool_data_with_args"},
        }
        mock_mcp_client.call_tool_sync.return_value = mock_result

        arguments = {"param1": "value1", "param2": 42}
        result = call_mcp_tool(mock_mcp_client, "test_tool", "test_id", arguments)

        assert result == "mock_tool_data_with_args"
        mock_mcp_client.call_tool_sync.assert_called_once_with(
            tool_use_id="test_id", name="test_tool", arguments=arguments
        )

    def test_successful_mcp_tool_call_with_none_arguments(self, mock_mcp_client):
        mock_result = {
            "status": "success",
            "structuredContent": {"result": "mock_tool_data"},
        }
        mock_mcp_client.call_tool_sync.return_value = mock_result

        result = call_mcp_tool(mock_mcp_client, "test_tool", "test_id", None)

        assert result == "mock_tool_data"
        mock_mcp_client.call_tool_sync.assert_called_once_with(
            tool_use_id="test_id", name="test_tool", arguments={}
        )

    def test_call_mcp_tool_raises_on_unexpected_structure(self, mock_mcp_client):
        mock_result = {"status": "success", "wrongField": "data"}
        mock_mcp_client.call_tool_sync.return_value = mock_result

        with pytest.raises(
            AgentExecutionError,
            match="MCP tool returned unexpected structure",
        ):
            call_mcp_tool(mock_mcp_client, "test_tool", "test_id")

    def test_call_mcp_tool_raises_on_exception(self, mock_mcp_client):
        mock_mcp_client.call_tool_sync.side_effect = Exception("MCP call failed")

        with pytest.raises(AgentExecutionError, match="Error calling MCP tool"):
            call_mcp_tool(mock_mcp_client, "test_tool", "test_id")

    def test_call_mcp_tool_with_missing_status(self, mock_mcp_client):
        mock_result = {"structuredContent": {"result": "data"}}
        mock_mcp_client.call_tool_sync.return_value = mock_result

        with pytest.raises(
            AgentExecutionError,
            match="MCP tool returned unexpected structure",
        ):
            call_mcp_tool(mock_mcp_client, "test_tool", "test_id")

    def test_call_mcp_tool_with_non_dict_result(self, mock_mcp_client):
        mock_mcp_client.call_tool_sync.return_value = "not a dict"

        with pytest.raises(
            AgentExecutionError,
            match="MCP tool returned unexpected structure",
        ):
            call_mcp_tool(mock_mcp_client, "test_tool", "test_id")


class TestSetupLocalMCPClient:
    def test_setup_local_mcp_client_success(self, monkeypatch, mocker, mock_mcp_client):
        mock_mcp_class = mocker.Mock(return_value=mock_mcp_client)
        monkeypatch.setattr("src.mcps.MCPClient", mock_mcp_class)

        client = setup_local_mcp_client("/path/to/mcp_server.py")

        assert client == mock_mcp_client
        mock_mcp_client.start.assert_called_once()

    def test_setup_local_mcp_client_raises_on_error(self, monkeypatch, mocker):
        mock_mcp_class = mocker.Mock(side_effect=Exception("Connection failed"))
        monkeypatch.setattr("src.mcps.MCPClient", mock_mcp_class)

        with pytest.raises(AgentExecutionError, match="Error initializing stdio MCP client"):
            setup_local_mcp_client("/path/to/mcp_server.py")


class TestSetupStreameableMCPClient:
    def test_setup_stremeable_mcp_client_success(self, monkeypatch, mocker, mock_mcp_client):
        mock_mcp_class = mocker.Mock(return_value=mock_mcp_client)
        monkeypatch.setattr("src.mcps.MCPClient", mock_mcp_class)

        headers = {"Authorization": "Bearer token"}
        client = setup_stremeable_mcp_client("http://test-gateway.com", headers, None)

        assert client == mock_mcp_client
        mock_mcp_client.start.assert_called_once()

    def test_setup_stremeable_mcp_client_with_ssl_context(
        self, monkeypatch, mocker, mock_mcp_client, mock_ssl_context
    ):
        mock_mcp_class = mocker.Mock(return_value=mock_mcp_client)
        monkeypatch.setattr("src.mcps.MCPClient", mock_mcp_class)

        headers = {"Authorization": "Bearer token"}
        client = setup_stremeable_mcp_client("http://test-gateway.com", headers, mock_ssl_context)

        assert client == mock_mcp_client
        mock_mcp_client.start.assert_called_once()

    def test_setup_stremeable_mcp_client_without_headers(
        self, monkeypatch, mocker, mock_mcp_client
    ):
        mock_mcp_class = mocker.Mock(return_value=mock_mcp_client)
        monkeypatch.setattr("src.mcps.MCPClient", mock_mcp_class)

        client = setup_stremeable_mcp_client("http://test-gateway.com", None, None)

        assert client == mock_mcp_client
        mock_mcp_client.start.assert_called_once()

    def test_setup_stremeable_mcp_client_raises_on_error(self, monkeypatch, mocker):
        mock_mcp_class = mocker.Mock(side_effect=Exception("Connection failed"))
        monkeypatch.setattr("src.mcps.MCPClient", mock_mcp_class)

        with pytest.raises(
            AgentExecutionError, match="Error initializing streamable HTTP MCP client"
        ):
            setup_stremeable_mcp_client("http://test-gateway.com", {}, None)
