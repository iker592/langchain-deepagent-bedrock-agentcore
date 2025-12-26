import sys

import boto3


def get_latest_version(runtime_id: str, region: str = "us-east-1") -> str:
    client = boto3.client("bedrock-agentcore", region_name=region)
    response = client.list_agent_runtime_versions(agentRuntimeId=runtime_id)
    versions = response.get("agentRuntimeVersions", [])
    if not versions:
        raise ValueError(f"No versions found for runtime {runtime_id}")
    return versions[0]["agentRuntimeVersion"]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: python get_latest_version.py <runtime_id> [region]", file=sys.stderr
        )
        sys.exit(1)

    runtime_id = sys.argv[1]
    region = sys.argv[2] if len(sys.argv) > 2 else "us-east-1"
    print(get_latest_version(runtime_id, region))
