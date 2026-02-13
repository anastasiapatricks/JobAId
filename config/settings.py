"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Central configuration via environment variables."""

    # OpenAI
    openai_api_key: str = ""
    default_model: str = "gpt-4o-mini"
    quality_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"

    # Adzuna job board API
    adzuna_app_id: str = ""
    adzuna_api_key: str = ""
    adzuna_base_url: str = "https://api.adzuna.com/v1/api"
    adzuna_country: str = "sg"

    # ChromaDB
    chroma_persist_dir: str = "chroma_data"

    # Guardrails
    max_iterations: int = 20
    max_retries_per_stage: int = 2
    max_llm_calls: int = 50

    # Debug
    debug: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


# Singleton instance
settings = Settings()
