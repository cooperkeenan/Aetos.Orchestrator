#!/bin/bash
set -e

if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

FUNCTION_APP_NAME="${AZURE_FUNCTION_APP_NAME:-aetos-orchestrator-func}"
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-aetos-dev-rg}"

echo "🔧 Enabling filesystem logging for $FUNCTION_APP_NAME..."
az webapp log config \
    --name $FUNCTION_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --application-logging filesystem \
    --level information \
    --web-server-logging filesystem

echo ""
echo "📋 Streaming logs from $FUNCTION_APP_NAME..."
echo "Press Ctrl+C to stop"
echo ""

# Function apps use 'az webapp log tail', NOT 'az functionapp log tail'
az webapp log tail \
    --name $FUNCTION_APP_NAME \
    --resource-group $RESOURCE_GROUP