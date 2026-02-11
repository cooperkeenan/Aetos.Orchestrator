#!/bin/bash
set -e

echo "🔧 Running fix script for Aetos Orchestrator..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

FUNCTION_APP_NAME="${AZURE_FUNCTION_APP_NAME:-aetos-orchestrator-func}"
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-aetos-dev-rg}"

echo "📋 Current environment variables:"
az functionapp config appsettings list \
    --name $FUNCTION_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --output table

echo ""
echo "🔄 Restarting function app..."
az functionapp restart \
    --name $FUNCTION_APP_NAME \
    --resource-group $RESOURCE_GROUP

echo ""
echo "✅ Fix complete!"
echo ""
echo "Common fixes applied:"
echo "  - Listed current app settings"
echo "  - Restarted function app"
echo ""
echo "If issues persist, check Application Insights logs or run:"
echo "  az functionapp log tail --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP"