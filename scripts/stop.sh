#!/bin/bash
set -e

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

FUNCTION_APP_NAME="${AZURE_FUNCTION_APP_NAME:-aetos-orchestrator-func}"
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-aetos-dev-rg}"

echo "⏸️  Stopping function app $FUNCTION_APP_NAME..."

az functionapp stop \
    --resource-group $RESOURCE_GROUP \
    --name $FUNCTION_APP_NAME

echo "✅ Function app stopped!"