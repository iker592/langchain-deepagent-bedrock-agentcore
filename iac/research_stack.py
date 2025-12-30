from pathlib import Path

from .base_stack import AgentStack


class ResearchAgentStack(AgentStack):
    """CDK Stack for the Research Agent."""

    def __init__(self, scope, construct_id, **kwargs):
        # The Dockerfile context is the project root (contains Dockerfile, pyproject.toml, etc.)
        project_root = str(Path(__file__).parent.parent.resolve())

        super().__init__(
            scope,
            construct_id,
            agent_name="ResearchAgent",
            agent_dockerfile_context=project_root,
            dockerfile="Dockerfile.research",
            **kwargs,
        )

