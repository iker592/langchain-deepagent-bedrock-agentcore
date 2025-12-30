from pathlib import Path

from aws_cdk import CfnOutput, Stack
from aws_cdk import aws_bedrockagentcore as agentcore
from aws_cdk import aws_iam as iam
from aws_cdk.aws_bedrock_agentcore_alpha import AgentRuntimeArtifact, Memory, Runtime
from constructs import Construct


class AgentStack(Stack):
    """Reusable CDK stack for deploying agents with HTTP and A2A protocols."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        agent_name: str,
        agent_dockerfile_context: str,
        dockerfile: str = "Dockerfile",
        model: str = "bedrock:global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        **kwargs,
    ) -> None:
        """
        Initialize an agent stack.

        Args:
            scope: CDK scope
            construct_id: Stack ID
            agent_name: Name of the agent (used for resource naming)
            agent_dockerfile_context: Path to directory containing Dockerfile
            dockerfile: Name of the Dockerfile to use
            model: Bedrock model ID to use
        """
        super().__init__(scope, construct_id, **kwargs)

        # Create artifact from the agent's Dockerfile context
        artifact = AgentRuntimeArtifact.from_asset(
            agent_dockerfile_context,
            file=dockerfile,
        )

        # Create memory for this agent (name must match pattern: ^[a-zA-Z][a-zA-Z0-9_]{0,47}$)
        memory = Memory(
            self,
            "Memory",
            memory_name=f"{agent_name.lower().replace(' ', '_')}_memory",
        )

        # Create runtime
        runtime = Runtime(
            self,
            f"{agent_name}Runtime",
            runtime_name=agent_name.lower().replace(" ", "_"),
            agent_runtime_artifact=artifact,
            environment_variables={
                "AWS_REGION": self.region,
                "MEMORY_ID": memory.memory_id,
                "MODEL": model,
                "AGENT_NAME": agent_name,
            },
        )

        # IAM permissions for Bedrock model invocation
        runtime.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel*"],
                resources=[
                    "arn:aws:bedrock:*::foundation-model/*",
                    "arn:aws:bedrock:*:*:inference-profile/*",
                ],
            )
        )
        runtime.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "logs:DescribeLogStreams",
                    "logs:CreateLogGroup",
                    "logs:DescribeLogGroups",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=["*"],
            )
        )

        # Memory permissions
        memory.grant_read_long_term_memory(runtime)
        memory.grant_read_short_term_memory(runtime)
        memory.grant_write(runtime)

        # Create endpoints
        dev_endpoint = agentcore.CfnRuntimeEndpoint(
            self,
            "DevEndpoint",
            agent_runtime_id=runtime.agent_runtime_id,
            name="dev",
            description=f"{agent_name} - Development endpoint",
        )

        # Outputs
        CfnOutput(self, "RuntimeArn", value=runtime.agent_runtime_arn)
        CfnOutput(self, "RuntimeId", value=runtime.agent_runtime_id)
        CfnOutput(self, "RuntimeName", value=agent_name)
        CfnOutput(self, "MemoryId", value=memory.memory_id)
        CfnOutput(
            self, "DevEndpointArn", value=dev_endpoint.attr_agent_runtime_endpoint_arn
        )

        # Store references for potential cross-stack usage
        self.runtime = runtime
        self.memory = memory
        self.dev_endpoint = dev_endpoint

