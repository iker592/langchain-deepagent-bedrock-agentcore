from aws_cdk import App

from .stack import DSPAgentStack

app = App()
DSPAgentStack(app, "DSPAgentStack")
app.synth()
