"""Application settings using pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Anthropic API
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    # Google Calendar API
    google_client_id: str = ""
    google_client_secret: str = ""

    # OpenWeatherMap API
    openweathermap_api_key: str = ""

    # Tavily Search API
    tavily_api_key: str = ""

    # DynamoDB
    dynamodb_endpoint_url: str = "http://localhost:8000"
    dynamodb_table_name: str = "skyplanner_sessions"
    aws_region: str = "ap-northeast-2"
    aws_access_key_id: str = "local"
    aws_secret_access_key: str = "local"

    # Application
    debug: bool = False
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()