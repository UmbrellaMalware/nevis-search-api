from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from environment variables (and `.env` if present)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://nevis:nevis@localhost:5432/nevis"
    api_key: str | None = None
    openai_api_key: str | None = None
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Search tuning. The similarity floor was calibrated for all-MiniLM-L6-v2: relevant matches
    # score ~0.4-0.7, unrelated queries stay below ~0.3 (see README, "Search quality").
    search_min_similarity: float = 0.35
    search_result_limit: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()
