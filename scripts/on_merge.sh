#!/bin/bash
set -e

PIPELINE_START=$(date +%s)

echo "========================================="
echo "Deploy Pipeline (simulating .github/workflows/deploy.yml)"
echo "Started at: $(date)"
echo "========================================="

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
echo "Step 3: Deploy to dev..."
STEP_START=$(date +%s)
make deploy
DEPLOY_DURATION=$(($(date +%s) - STEP_START))
echo "  Duration: ${DEPLOY_DURATION}s"

echo ""
echo "Step 4: Get latest version..."
RUNTIME_ID=$(cat cdk-outputs.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['ServerlessDeepAgentStack']['RuntimeId'])")
VERSION=$(uv run python scripts/get_latest_version.py $RUNTIME_ID)
echo "Deployed version: $VERSION"

echo ""
echo "Step 5: Update dev endpoint to version $VERSION..."
aws bedrock-agentcore-control update-agent-runtime-endpoint \
    --agent-runtime-id $RUNTIME_ID \
    --endpoint-name dev \
    --agent-runtime-version $VERSION \
    --region us-east-1

echo ""
echo "Step 6: Run E2E tests on dev endpoint..."
STEP_START=$(date +%s)
make test-e2e
E2E_DURATION=$(($(date +%s) - STEP_START))
echo "  Duration: ${E2E_DURATION}s"

echo ""
echo "Step 7: Promote canary to version $VERSION..."
aws bedrock-agentcore-control update-agent-runtime-endpoint \
    --agent-runtime-id $RUNTIME_ID \
    --endpoint-name canary \
    --agent-runtime-version $VERSION \
    --region us-east-1

echo ""
echo "Step 8: A/B test (mock)..."
echo "A/B test executed here (mock)"
echo "In production, this would:"
echo "  - Monitor canary endpoint for errors"
echo "  - Compare latency/error rates with prod"
echo "  - Run sample traffic through canary"
sleep 2

echo ""
echo "Step 9: Promote prod to version $VERSION..."
aws bedrock-agentcore-control update-agent-runtime-endpoint \
    --agent-runtime-id $RUNTIME_ID \
    --endpoint-name prod \
    --agent-runtime-version $VERSION \
    --region us-east-1

TOTAL_DURATION=$(($(date +%s) - PIPELINE_START))
echo ""
echo "========================================="
echo "Deploy pipeline complete!"
echo "All endpoints now on version $VERSION"
echo "========================================="
echo ""
echo "Summary:"
echo "  Deploy:     ${DEPLOY_DURATION}s"
echo "  E2E tests:  ${E2E_DURATION}s"
echo "  Total:      ${TOTAL_DURATION}s ($(($TOTAL_DURATION / 60))m $(($TOTAL_DURATION % 60))s)"
