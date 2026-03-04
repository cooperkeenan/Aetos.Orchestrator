#!/bin/bash
set -e

echo "🚀 Deploying Aetos Orchestrator (Azure Function)..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

FUNCTION_APP_NAME="${AZURE_FUNCTION_APP_NAME:-aetos-orchestrator-func}"
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-aetos-dev-rg}"

echo "📦 Creating deployment package..."
# Flex Consumption requires source-only zip + remote build.
# Do NOT pip install locally — Azure builds on Linux server-side.
python3 << 'EOF'
import zipfile
import os

def should_exclude(path):
    exclude_patterns = [
        '.git', 'venv', '.venv', '__pycache__', '.pyc',
        '.env', 'tests', 'deployment.zip', '.mypy_cache',
        '.python_packages', 'node_modules', '.ruff_cache',
        '__azurite_db', 'AzuriteConfig'
    ]
    return any(pattern in str(path) for pattern in exclude_patterns)

with zipfile.ZipFile('deployment.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if not should_exclude(os.path.join(root, d))]
        for file in files:
            file_path = os.path.join(root, file)
            if not should_exclude(file_path):
                zipf.write(file_path)

print("✓ Created deployment.zip")
EOF

echo "🚀 Deploying to Azure Functions (remote build)..."
az functionapp deployment source config-zip \
    --resource-group $RESOURCE_GROUP \
    --name $FUNCTION_APP_NAME \
    --src deployment.zip \
    --build-remote true

echo "🔧 Setting application settings..."
az functionapp config appsettings set \
    --name $FUNCTION_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --settings \
        DATABASE_URL="$DATABASE_URL" \
        PRODUCTS_DATABASE_URL="$PRODUCTS_DATABASE_URL" \
        RABBITMQ_URL="$RABBITMQ_URL" \
        SCRAPER_API_URL="$SCRAPER_API_URL" \
        SCRAPER_API_KEY="$SCRAPER_API_KEY" \
        CHATTERBOT_API_URL="$CHATTERBOT_API_URL" \
        EBAY_API_URL="$EBAY_API_URL" \
        LOG_LEVEL="$LOG_LEVEL" \
        AZURE_SUBSCRIPTION_ID="$AZURE_SUBSCRIPTION_ID" \
        AZURE_RESOURCE_GROUP="$AZURE_RESOURCE_GROUP" \
        AZURE_SCRAPER_CONTAINER="$AZURE_SCRAPER_CONTAINER" \
        AzureWebJobsFeatureFlags="EnableWorkerIndexing" \
        TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN" \
        TELEGRAM_CHAT_ID="$TELEGRAM_CHAT_ID"

echo "🧹 Cleaning up..."
rm -f deployment.zip

echo "✅ Deployment complete!"
echo "🌐 Function App URL: https://${FUNCTION_APP_NAME}.azurewebsites.net"