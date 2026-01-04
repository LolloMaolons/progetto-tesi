#!/bin/bash
# Run MCP host once (one-shot execution)
# Usage: ./scripts/run-mcp-once.sh

set -e

REST_BASE_URL="${REST_BASE_URL:-http://localhost:8080}"
REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"

echo "Running MCP host (one-shot)..."
echo "REST_BASE_URL: $REST_BASE_URL"
echo "REDIS_URL: $REDIS_URL"
echo ""

cd "$(dirname "$0")/../mcp-host"

export REST_BASE_URL
export REDIS_URL

if [ -f "requirements.txt" ]; then
    # Check if dependencies are installed
    if ! python3 -c "import requests, redis" 2>/dev/null; then
        echo "Installing dependencies..."
        pip install -r requirements.txt
    fi
fi

python3 main.py
