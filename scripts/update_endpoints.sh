#!/bin/bash
# Updates dev endpoints for all stacks to the latest version
set -e

echo "Updating dev endpoints to latest versions..."

for stack in ServerlessDeepAgentStack ResearchAgentStack CodingAgentStack; do
    RUNTIME_ID=$(cat cdk-outputs.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$stack', {}).get('RuntimeId', ''))" 2>/dev/null)
    
    if [ -n "$RUNTIME_ID" ]; then
        VERSION=$(uv run python scripts/get_latest_version.py $RUNTIME_ID 2>/dev/null)
        if [ -n "$VERSION" ]; then
            echo "  $stack: updating dev endpoint to version $VERSION"
            aws bedrock-agentcore-control update-agent-runtime-endpoint \
                --agent-runtime-id $RUNTIME_ID \
                --endpoint-name dev \
                --agent-runtime-version $VERSION \
                --region us-east-1 > /dev/null 2>&1 || true
        fi
    fi
done

echo "Done!"

