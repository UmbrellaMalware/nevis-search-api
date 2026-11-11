from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from environment variables (and `.env` if present)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://nevis:nevis@localhost:5432/nevis"
    api_key: str | None = None
    openai_api_key: str | None = None
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache
def get_settings() -> Settings:
    return Settings()
