"""Application settings loaded from environment variables and an optional .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DevDigest API"
    app_version: str = "0.4.0"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"

    # Credentials for integrations added in later milestones.
    groq_api_key: str = ""
    github_token: str = ""
    chroma_persist_dir: str = "./data/chroma"
    chroma_collection_name: str = "devdigest_research"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size: int = 1000
    chunk_overlap: int = 150
    rag_top_k: int = 5
    max_pdf_size_mb: int = 15
    groq_model: str = "openai/gpt-oss-120b"

    github_api_base_url: str = "https://api.github.com"
    github_timeout_seconds: float = 20.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
