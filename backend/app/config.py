"""
Centralized application configuration.

All environment-dependent values are read here and nowhere else, so the
rest of the codebase never touches os.environ directly.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # ------------------------------------------------------------------
    # LLM / Embeddings
    # ------------------------------------------------------------------

    # Keep Gemini settings for compatibility (can remove later)
    google_api_key: str = ""
    gemini_chat_model: str = "gemini-2.0-flash"
    gemini_embedding_model: str = "models/gemini-embedding-001"

    # Groq
    groq_api_key: str = ""
    chat_model: str = "llama-3.1-8b-instant"

    # Local Embeddings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    upload_dir: str = str(BASE_DIR / "data" / "uploads")
    chroma_persist_dir: str = str(BASE_DIR / "data" / "chroma_db")
    hf_cache_dir: str = str(BASE_DIR / "data" / "hf_cache")

    # ------------------------------------------------------------------
    # Chunking
    # ------------------------------------------------------------------

    chunk_size: int = 800
    chunk_overlap: int = 150

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    retrieval_top_k: int = 5

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    max_file_size_mb: int = 50
    allowed_extensions: tuple[str, ...] = (".pdf",)

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------

    cors_allowed_origins: str = "*"

    # ------------------------------------------------------------------
    # App
    # ------------------------------------------------------------------

    environment: str = "development"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance so the .env file is parsed only once."""
    return Settings()