#!/bin/bash
set -e

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-aetos-dev-rg}"
CONTAINER_NAME="${AZURE_CONTAINER_NAME:-aetos-orchestrator}"

echo "▶️  Starting container $CONTAINER_NAME..."

az container start \
    --resource-group $RESOURCE_GROUP \
    --name $CONTAINER_NAME

echo "✅ Container started!"
echo ""
echo "Run './run.sh' and select 'Stream logs' to view container output"