from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Orchestrator database (Neon Postgres - Aetos-Orchestrator)
    database_url: str = "postgresql://aetos:aetos@localhost:5432/aetos_orchestrator"
    
    # Products database (existing - Aetos-Products)
    products_database_url: str = "postgresql://aetos:aetos@localhost:5432/aetos_products"
    
    rabbitmq_url: str = "amqp://aetos:aetos@localhost:5672/"
    scraper_api_url: str = "http://scraperv2:8000"
    chatterbot_api_url: str = "http://chatterbot:8000"
    ebay_api_url: str = "http://ebaylister:8000"
    log_level: str = "INFO"
    
    # Azure Container Instance settings
    azure_subscription_id: str = "37035190-2489-46aa-bc55-ccc9fc751ead"
    azure_resource_group: str = "aetos-dev-rg"
    azure_scraper_container: str = "scraperv2"
    azure_chatterbot_container: str = "chatterbot"
    azure_function_app_name: str = "aetos-orchestrator-func"


settings = Settings()