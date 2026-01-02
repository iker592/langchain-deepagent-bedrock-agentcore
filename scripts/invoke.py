import json
import os
import uuid

import boto3

from agents.dsp.settings import Settings

DEFAULT_SESSION_ID = f"default-session-{uuid.uuid4().hex}"
DEFAULT_USER_ID = "default-user"


def main(
    input: str,
    session_id: str | None = None,
    user_id: str | None = None,
    stream: bool = False,
    stream_agui: bool = False,
    endpoint: str | None = None,
):
    settings = Settings()
    session_id = session_id or DEFAULT_SESSION_ID
    user_id = user_id or DEFAULT_USER_ID

    runtime_arn = os.environ.get("AGENT_RUNTIME_ARN") or settings.agent_runtime_arn
    if not runtime_arn:
        raise ValueError("AGENT_RUNTIME_ARN not set. Deploy first or set manually.")

    endpoint = endpoint or os.environ.get("AGENT_ENDPOINT")

    body = {
        "input": input,
        "user_id": user_id,
        "session_id": session_id,
        "stream": stream,
        "stream_agui": stream_agui,
    }
    client = boto3.client("bedrock-agentcore", region_name=settings.aws_region)

    invoke_params = {
        "agentRuntimeArn": runtime_arn,
        "runtimeSessionId": session_id,
        "payload": json.dumps(body),
    }
    if endpoint:
        invoke_params["qualifier"] = endpoint

    response = client.invoke_agent_runtime(**invoke_params)

    content_type = response.get("contentType", "")

    if "text/event-stream" in content_type:
        if stream_agui:
            print("AG-UI Streaming response:")
            for line in response["response"].iter_lines(chunk_size=10):
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        event_type = data.get("type")
                        if event_type == "TEXT_MESSAGE_CONTENT":
                            print(data.get("delta", ""), end="", flush=True)
                        elif event_type == "RUN_STARTED":
                            print(f"[Run: {data.get('runId')}]")
                        elif event_type == "RUN_FINISHED":
                            print("\n[Run finished]")
                        elif event_type == "TOOL_CALL_START":
                            print(f"\n[Tool: {data.get('toolCallName')}]", end="")
                        elif event_type == "TOOL_CALL_RESULT":
                            print(f" -> {data.get('content', '')[:50]}...")
        else:
            print("Streaming response:")
            for line in response["response"].iter_lines(chunk_size=10):
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if data.get("type") == "chunk":
                            print(data.get("content", ""), end="", flush=True)
                        elif data.get("type") == "start":
                            print(f"[Session: {data.get('session_id')}]")
                        elif data.get("type") == "end":
                            print("\n[Done]")
    else:
        response_body = response["response"].read()
        response_data = json.loads(response_body)
        print("Agent Response:", response_data)


if __name__ == "__main__":
    main(input="Hello!")
