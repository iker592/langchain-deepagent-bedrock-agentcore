class AgentExecutionError(Exception):
    """
    Exception raised when the agent execution fails.
    """

    def __init__(self, detail: str, status_code: int = 500):
        self.detail = detail
        self.status_code = status_code
        super().__init__(self.detail, self.status_code)


class MCPConnectionError(AgentExecutionError):
    """
    Exception raised when MCP connection fails and retry is needed.
    Inherits from AgentExecutionError to be caught by existing error handlers.
    """

    def __init__(self, detail: str, original_error: Exception = None):
        self.original_error = original_error
        super().__init__(detail=detail, status_code=500)
