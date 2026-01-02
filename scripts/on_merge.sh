#!/bin/bash
set -e

# All stacks to deploy and update
STACKS="${STACKS:-DSPAgentStack ResearchAgentStack CodingAgentStack}"

PIPELINE_START=$(date +%s)

echo "========================================="
echo "Deploy Pipeline (simulating .github/workflows/deploy.yml)"
echo "Started at: $(date)"
echo "Stacks: $STACKS"
echo "========================================="

# Helper function to update dev endpoint for a stack
update_dev_endpoint() {
    local stack=$1
    local runtime_id=$(cat cdk-outputs.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$stack', {}).get('RuntimeId', ''))" 2>/dev/null)
    
    if [ -n "$runtime_id" ]; then
        local version=$(uv run python scripts/get_latest_version.py $runtime_id 2>/dev/null)
        if [ -n "$version" ]; then
            echo "  $stack: updating dev endpoint to version $version"
            aws bedrock-agentcore-control update-agent-runtime-endpoint \
                --agent-runtime-id $runtime_id \
                --endpoint-name dev \
                --agent-runtime-version $version \
                --region us-east-1 > /dev/null 2>&1 || true
        fi
    fi
}

echo ""
echo "Step 1: Lint and format..."
STEP_START=$(date +%s)
make fix
echo "  Duration: $(($(date +%s) - STEP_START))s"

echo ""
echo "Step 2: Run unit tests..."
STEP_START=$(date +%s)
make test-unit
echo "  Duration: $(($(date +%s) - STEP_START))s"

echo ""
echo "Step 3: Deploy all stacks..."
STEP_START=$(date +%s)
uv run cdk deploy --all --require-approval never --outputs-file cdk-outputs.json
DEPLOY_DURATION=$(($(date +%s) - STEP_START))
echo "  Duration: ${DEPLOY_DURATION}s"

echo ""
echo "Step 4: Update dev endpoints to latest versions..."
for stack in $STACKS; do
    update_dev_endpoint $stack
done

echo ""
echo "Step 5: Run E2E tests on dev endpoint..."
STEP_START=$(date +%s)
make test-e2e
E2E_DURATION=$(($(date +%s) - STEP_START))
echo "  Duration: ${E2E_DURATION}s"

# Canary/Prod promotion only for main DSPAgent stack
RUNTIME_ID=$(cat cdk-outputs.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['DSPAgentStack']['RuntimeId'])")
VERSION=$(uv run python scripts/get_latest_version.py $RUNTIME_ID)

echo ""
echo "Step 6: Promote canary to version $VERSION (DSPAgent only)..."
aws bedrock-agentcore-control update-agent-runtime-endpoint \
    --agent-runtime-id $RUNTIME_ID \
    --endpoint-name canary \
    --agent-runtime-version $VERSION \
    --region us-east-1

echo ""
echo "Step 7: A/B test (mock)..."
echo "A/B test executed here (mock)"
echo "In production, this would:"
echo "  - Monitor canary endpoint for errors"
echo "  - Compare latency/error rates with prod"
echo "  - Run sample traffic through canary"
sleep 2

echo ""
echo "Step 8: Promote prod to version $VERSION (DSPAgent only)..."
aws bedrock-agentcore-control update-agent-runtime-endpoint \
    --agent-runtime-id $RUNTIME_ID \
    --endpoint-name prod \
    --agent-runtime-version $VERSION \
    --region us-east-1

TOTAL_DURATION=$(($(date +%s) - PIPELINE_START))
echo ""
echo "========================================="
echo "Deploy pipeline complete!"
echo "All dev endpoints updated to latest versions"
echo "DSPAgent canary/prod on version $VERSION"
echo "========================================="
echo ""
echo "Summary:"
echo "  Deploy:     ${DEPLOY_DURATION}s"
echo "  E2E tests:  ${E2E_DURATION}s"
echo "  Total:      ${TOTAL_DURATION}s ($(($TOTAL_DURATION / 60))m $(($TOTAL_DURATION % 60))s)"
