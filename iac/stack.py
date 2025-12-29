import json
from pathlib import Path

import boto3
from aws_cdk import CfnOutput, Stack
from aws_cdk import aws_bedrockagentcore as agentcore
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk import aws_xray as xray
from aws_cdk.aws_bedrock_agentcore_alpha import AgentRuntimeArtifact, Memory, Runtime
from botocore.exceptions import ClientError
from constructs import Construct


class ServerlessDeepAgentStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        if not self._is_transaction_search_active():
            self._enable_transaction_search()

        deepagent_runtime_artifact = AgentRuntimeArtifact.from_asset(
            str(Path(__file__).parent.parent.resolve())
        )

        memory = Memory(self, "Memory", memory_name="memory")
        runtime = Runtime(
            self,
            "DeepAgent",
            runtime_name="deep_agent",
            agent_runtime_artifact=deepagent_runtime_artifact,
            environment_variables={
                "AWS_REGION": self.region,
                "MEMORY_ID": memory.memory_id,
                "MODEL": "bedrock:global.anthropic.claude-sonnet-4-5-20250929-v1:0",
            },
        )

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
        memory.grant_read_long_term_memory(runtime)
        memory.grant_read_short_term_memory(runtime)
        memory.grant_write(runtime)

        dev_endpoint = agentcore.CfnRuntimeEndpoint(
            self,
            "DevEndpoint",
            agent_runtime_id=runtime.agent_runtime_id,
            name="dev",
            description="Development endpoint - always latest version",
        )
        canary_endpoint = agentcore.CfnRuntimeEndpoint(
            self,
            "CanaryEndpoint",
            agent_runtime_id=runtime.agent_runtime_id,
            name="canary",
            description="Canary endpoint for pre-prod testing",
        )
        prod_endpoint = agentcore.CfnRuntimeEndpoint(
            self,
            "ProdEndpoint",
            agent_runtime_id=runtime.agent_runtime_id,
            name="prod",
            description="Production endpoint",
        )

        CfnOutput(self, "RuntimeArn", value=runtime.agent_runtime_arn)
        CfnOutput(self, "RuntimeId", value=runtime.agent_runtime_id)
        CfnOutput(self, "MemoryId", value=memory.memory_id)
        CfnOutput(
            self, "DevEndpointArn", value=dev_endpoint.attr_agent_runtime_endpoint_arn
        )
        CfnOutput(
            self,
            "CanaryEndpointArn",
            value=canary_endpoint.attr_agent_runtime_endpoint_arn,
        )
        CfnOutput(
            self, "ProdEndpointArn", value=prod_endpoint.attr_agent_runtime_endpoint_arn
        )

    def _is_transaction_search_active(self) -> bool:
        try:
            xray_client = boto3.client("xray", region_name="us-east-1")
            response = xray_client.get_trace_segment_destination()
            is_active = response.get("Status") == "ACTIVE"
            if is_active:
                print("Transaction Search already active, skipping policy creation")
            return is_active
        except ClientError as e:
            print(f"Could not check Transaction Search status: {e}")
            return False

    def _enable_transaction_search(self):
        logs.CfnResourcePolicy(
            self,
            "XRayLogsResourcePolicy",
            policy_name="XRaySpansResourcePolicy",
            policy_document=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "AllowXRayToWriteLogs",
                            "Effect": "Allow",
                            "Principal": {"Service": "xray.amazonaws.com"},
                            "Action": [
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents",
                            ],
                            "Resource": (
                                f"arn:aws:logs:{self.region}:{self.account}:log-group:aws/spans:*"
                            ),
                        }
                    ],
                }
            ),
        )

        xray.CfnResourcePolicy(
            self,
            "TransactionSearchConfig",
            policy_name="AWSTransactionSearchConfiguration",
            policy_document=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "TransactionSearchIndexing",
                            "Effect": "Allow",
                            "Principal": "*",
                            "Action": ["xray:IndexSpans"],
                            "Resource": "*",
                            "Condition": {
                                "StringEquals": {
                                    "xray:IndexingStrategy": "Probabilistic"
                                },
                                "NumericLessThanEquals": {
                                    "xray:ProbabilisticRate": 0.01
                                },
                            },
                        }
                    ],
                }
            ),
        )
