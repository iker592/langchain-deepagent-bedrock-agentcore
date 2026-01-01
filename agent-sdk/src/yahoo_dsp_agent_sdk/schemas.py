from pydantic import BaseModel, Field


class AgentResponse(BaseModel):
    """Agent response"""

    response: str = Field(
        description="Response from the AI Agent. Don't include the tool call data here"
    )
    tool_call_response: str = Field(description="The data returned from the tool call")
    successful_tool_call: bool = Field(description="Whether the tool call was successful")
    tool_name: str = Field(description="The name of the last successful tool that was called")
