#!/bin/bash
set -e

echo "🚀 Deploying Aetos Orchestrator (Azure Function)..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

FUNCTION_APP_NAME="${AZURE_FUNCTION_APP_NAME:-aetos-orchestrator-func}"
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-aetos-dev-rg}"

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "🚀 Deploying to Azure Functions..."
func azure functionapp publish $FUNCTION_APP_NAME

echo "🔧 Setting application settings..."
az functionapp config appsettings set \
    --name $FUNCTION_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --settings \
        DATABASE_URL="$DATABASE_URL" \
        RABBITMQ_URL="$RABBITMQ_URL" \
        SCRAPER_API_URL="$SCRAPER_API_URL" \
        CHATTERBOT_API_URL="$CHATTERBOT_API_URL" \
        EBAY_API_URL="$EBAY_API_URL" \
        LOG_LEVEL="$LOG_LEVEL" \
        AZURE_SUBSCRIPTION_ID="$AZURE_SUBSCRIPTION_ID" \
        AZURE_RESOURCE_GROUP="$AZURE_RESOURCE_GROUP" \
        AZURE_CONTAINER_NAME="scraperv2"

echo "✅ Deployment complete!"
echo "🌐 Function App URL: https://${FUNCTION_APP_NAME}.azurewebsites.net"