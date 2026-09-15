from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Runtime configuration. Every value can be overridden via environment variables
    or a `backend/.env` file (see `.env.example`)."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "PaperAI"
    debug: bool = False
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    # Also accept browsers on the local network (http://192.168.x.x:3000 etc.)
    # so other devices can use a dev instance started with --host 0.0.0.0.
    cors_allow_private_network: bool = True

    # --- Database -----------------------------------------------------------
    # SQLite (default, zero-setup) or PostgreSQL + pgvector, e.g.
    #   postgresql+psycopg://paperai:paperai@localhost:5432/paperai
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'paperai.db').as_posix()}"

    # --- Storage ------------------------------------------------------------
    storage_backend: Literal["local", "s3"] = "local"
    storage_local_dir: Path = BACKEND_DIR / "data" / "uploads"
    s3_bucket: str | None = None
    s3_endpoint_url: str | None = None
    s3_region: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None

    # --- AI providers -------------------------------------------------------
    # "mock" runs the whole pipeline offline (no API keys needed).
    llm_provider: Literal["openai", "anthropic", "mock"] = "mock"
    embedding_provider: Literal["openai", "mock"] = "mock"
    translation_provider: Literal["openai", "anthropic", "mock"] = "mock"

    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_chat_model: str = "gpt-4o-mini"
    openai_translation_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 1536

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-5"
    # Thinking effort (low | medium | high | xhigh | max). Chat keeps the default;
    # translation is a well-specified task, so a lower effort is faster and cheaper.
    anthropic_effort: str | None = None
    anthropic_translation_effort: str | None = "medium"

    mock_embedding_dimensions: int = 256

    # --- Pipeline -----------------------------------------------------------
    max_upload_mb: int = 50
    translation_batch_size: int = 8
    chunk_target_chars: int = 1200
    chunk_overlap_paragraphs: int = 1
    retrieval_top_k: int = 6

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")

    @property
    def embedding_dimensions(self) -> int:
        if self.embedding_provider == "openai":
            return self.openai_embedding_dimensions
        return self.mock_embedding_dimensions


@lru_cache
def get_settings() -> Settings:
    return Settings()
