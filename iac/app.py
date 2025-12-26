from aws_cdk import App

from .stack import Environment, ServerlessDeepAgentStack

app = App()

environment: Environment = app.node.try_get_context("env") or "dev"

stack_name = f"DeepAgent-{environment.capitalize()}"
ServerlessDeepAgentStack(app, stack_name, environment=environment)

app.synth()
