from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Orchestrator database (Neon Postgres - Aetos-Orchestrator)
    database_url: str = (
        "postgresql+asyncpg://neondb_owner:npg_DOPcraBq2du0@ep-twilight-cake-a8f7z35t-pooler.eastus2.azure.neon.tech/neondb?ssl=require"
    )

    # Products database (existing - Aetos-Products)
    products_database_url: str = (
        "postgresql+asyncpg://neondb_owner:npg_MXEm6PaRCbu7@ep-broad-fire-a8ngftkc-pooler.eastus2.azure.neon.tech/neondb?ssl=require"
    )

    rabbitmq_url: str = (
        "amqps://dvjiveii:nvd9huQBDRIm4tbljYz0-JoFEHIG0Ao5@goose.rmq2.cloudamqp.com/dvjiveii"
    )

    # Scraper service
    scraper_api_url: str = "http://aetos-scraper.eastus.azurecontainer.io:8000"
    scraper_api_key: str = "aetos-production-key-2024"  # ← ADD THIS LINE

    chatterbot_api_url: str = "http://chatterbot:8000"
    ebay_api_url: str = "http://ebaylister:8000"
    log_level: str = "INFO"

    # Azure Container Instance settings
    azure_subscription_id: str = "37035190-2489-46aa-bc55-ccc9fc751ead"
    azure_resource_group: str = "aetos-dev-rg"
    azure_scraper_container: str = "aetos-scraper"
    azure_chatterbot_container: str = "chatterbot"
    azure_function_app_name: str = "aetos-orchestrator-func"


settings = Settings()
