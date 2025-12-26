import json
import os
import uuid

import boto3
import pytest


@pytest.mark.e2e
class TestDeployedAgent:
    @pytest.fixture(autouse=True)
    def setup(self, deployed_runtime_arn):
        self.runtime_arn = deployed_runtime_arn
        self.region = os.environ.get("AWS_REGION", "us-east-1")
        self.client = boto3.client("bedrock-agentcore", region_name=self.region)
        self.session_id = f"e2e-test-{uuid.uuid4().hex}"

    def test_agent_responds_to_simple_query(self):
        response = self._invoke("Hello, who are you?")

        assert response is not None
        content = response.get("content", "")
        assert len(content) > 0
        print(f"✅ Agent response: {content[:100]}...")

    def test_agent_performs_calculation(self):
        response = self._invoke("What is 25 * 4?")

        content = response.get("content", "")
        assert "100" in content
        print(f"✅ Calculation response: {content}")

    def test_agent_handles_complex_query(self):
        response = self._invoke(
            "If a campaign had 1000 impressions yesterday and 1500 today, "
            "what is the percentage increase?"
        )

        content = response.get("content", "")
        assert "50" in content or "percent" in content.lower()
        print(f"✅ Complex query response: {content[:150]}...")

    def _invoke(self, message: str) -> dict:
        body = {
            "input": message,
            "user_id": "e2e-test-user",
            "session_id": self.session_id,
        }

        response = self.client.invoke_agent_runtime(
            agentRuntimeArn=self.runtime_arn,
            runtimeSessionId=self.session_id,
            payload=json.dumps(body),
        )

        response_body = response["response"].read()
        return json.loads(response_body)


@pytest.mark.e2e
class TestDeployedAgentStreaming:
    @pytest.fixture(autouse=True)
    def setup(self, deployed_runtime_arn):
        self.runtime_arn = deployed_runtime_arn
        self.region = os.environ.get("AWS_REGION", "us-east-1")
        self.client = boto3.client("bedrock-agentcore", region_name=self.region)
        self.session_id = f"e2e-stream-{uuid.uuid4().hex}"

    def test_agent_streams_agui_response(self):
        body = {
            "input": "What is 7 * 8?",
            "user_id": "e2e-test-user",
            "session_id": self.session_id,
            "stream_agui": True,
        }

        response = self.client.invoke_agent_runtime(
            agentRuntimeArn=self.runtime_arn,
            runtimeSessionId=self.session_id,
            payload=json.dumps(body),
        )

        content_type = response.get("contentType", "")
        assert "text/event-stream" in content_type

        events = []
        for line in response["response"].iter_lines(chunk_size=10):
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    events.append(data)

        event_types = [e.get("type") for e in events]
        assert "RUN_STARTED" in event_types
        assert "RUN_FINISHED" in event_types
        print(f"✅ Received {len(events)} AG-UI events: {event_types}")
