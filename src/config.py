from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql://aetos:aetos@localhost:5432/aetos_orchestrator"
    rabbitmq_url: str = "amqp://aetos:aetos@localhost:5672/"
    scraper_api_url: str = "http://scraperv2:8000"
    chatterbot_api_url: str = "http://chatterbot:8000"
    ebay_api_url: str = "http://ebaylister:8000"
    log_level: str = "INFO"


settings = Settings()
