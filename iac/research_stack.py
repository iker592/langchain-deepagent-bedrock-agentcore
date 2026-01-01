from .base_stack import AgentStack


class ResearchAgentStack(AgentStack):
    """CDK Stack for the Research Agent."""

    def __init__(self, scope, construct_id, **kwargs):
        super().__init__(
            scope,
            construct_id,
            agent_name="ResearchAgent",
            agent_path="./agents/research",
            **kwargs,
        )
