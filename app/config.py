from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from environment variables (and `.env` if present)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://nevis:nevis@localhost:5432/nevis"
    api_key: str | None = None
    openai_api_key: str | None = None
    # all-MiniLM-L6-v2 fine-tuned for wealth-management search (see README, "Search quality").
    # Pinned to a commit of the Hugging Face repo so builds are reproducible.
    embedding_model: str = "UmbrellaMalware/all-MiniLM-L6-v2-wealth"
    embedding_model_revision: str | None = "68e3018b96bc14bb1aed8ecd0623688123f0e41d"

    # Search tuning. The similarity floor is calibrated for the model above on the benchmark
    # (scripts/benchmark_search.py): it maximises F1 when combined with the synonym glossary.
    search_min_similarity: float = 0.30
    search_result_limit: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()
