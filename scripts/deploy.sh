#!/bin/bash
set -e

echo "🚀 Deploying Aetos Orchestrator (Azure Function)..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

FUNCTION_APP_NAME="${AZURE_FUNCTION_APP_NAME:-aetos-orchestrator-func}"
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-aetos-dev-rg}"

echo "📦 Installing dependencies locally..."
pip install -r requirements.txt --target .python_packages/lib/site-packages

echo "📦 Creating deployment package..."
# Use Python to create zip (no external zip command needed)
python3 << 'EOF'
import zipfile
import os
from pathlib import Path

def should_exclude(path):
    exclude_patterns = [
        '.git', 'venv', '.venv', '__pycache__', '.pyc', 
        '.env', '.md', 'tests', 'deployment.zip', '.mypy_cache'
    ]
    return any(pattern in str(path) for pattern in exclude_patterns)

with zipfile.ZipFile('deployment.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk('.'):
        # Filter out excluded directories
        dirs[:] = [d for d in dirs if not should_exclude(os.path.join(root, d))]
        
        for file in files:
            file_path = os.path.join(root, file)
            if not should_exclude(file_path):
                zipf.write(file_path)
                
print("✓ Created deployment.zip")
EOF

echo "🚀 Deploying to Azure Functions via Azure CLI..."
az functionapp deployment source config-zip \
    --resource-group $RESOURCE_GROUP \
    --name $FUNCTION_APP_NAME \
    --src deployment.zip

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
        AZURE_SCRAPER_CONTAINER="$AZURE_SCRAPER_CONTAINER"

echo "🧹 Cleaning up..."
rm -rf deployment.zip .python_packages

echo "✅ Deployment complete!"
echo "🌐 Function App URL: https://${FUNCTION_APP_NAME}.azurewebsites.net"