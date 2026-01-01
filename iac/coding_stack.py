from .base_stack import AgentStack


class CodingAgentStack(AgentStack):
    """CDK Stack for the Coding Agent."""

    def __init__(self, scope, construct_id, **kwargs):
        super().__init__(
            scope,
            construct_id,
            agent_name="CodingAgent",
            agent_path="./agents/coding",
            **kwargs,
        )
