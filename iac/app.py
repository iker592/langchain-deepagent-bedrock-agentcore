from aws_cdk import App

from .coding_stack import CodingAgentStack
from .research_stack import ResearchAgentStack
from .stack import ServerlessDeepAgentStack

app = App()

# Original deep agent stack (kept for backwards compatibility)
ServerlessDeepAgentStack(app, "ServerlessDeepAgentStack")

# Multi-agent stacks with HTTP + A2A protocols
ResearchAgentStack(app, "ResearchAgentStack")
CodingAgentStack(app, "CodingAgentStack")

app.synth()
