import json
import uuid

import boto3

from agent.settings import Settings

DEFAULT_SESSION_ID = f"default-session-{uuid.uuid4().hex}"
DEFAULT_USER_ID = "default-user"


def main(input: str, session_id: str | None = None, user_id: str | None = None):
    settings = Settings()
    session_id = session_id or DEFAULT_SESSION_ID
    user_id = user_id or DEFAULT_USER_ID

    body = {"input": input, "user_id": user_id, "session_id": session_id}
    client = boto3.client("bedrock-agentcore", region_name=settings.aws_region)
    response = client.invoke_agent_runtime(
        agentRuntimeArn=settings.agent_runtime_arn,
        runtimeSessionId=session_id,
        payload=json.dumps(body),
    )

    response_body = response["response"].read()
    response_data = json.loads(response_body)
    print("Agent Response:", response_data)


if __name__ == "__main__":
    main(input="Hello!")
