#!/bin/bash
set -e

echo "========================================="
echo "PR Checks (simulating .github/workflows/pr.yml)"
echo "========================================="

echo ""
echo "Step 1: Lint and format..."
make fix

echo ""
echo "Step 2: Run unit tests..."
make test-unit

echo ""
echo "========================================="
echo "All PR checks passed!"
echo "========================================="

