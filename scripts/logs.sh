#!/bin/bash
set -e

if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

FUNCTION_APP_NAME="${AZURE_FUNCTION_APP_NAME:-aetos-orchestrator-func}"
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-aetos-dev-rg}"

echo "📋 Streaming logs from $FUNCTION_APP_NAME..."

func azure functionapp logstream $FUNCTION_APP_NAME