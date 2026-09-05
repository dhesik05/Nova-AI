from __future__ import annotations

import os
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized environment configuration.

    Notes:
    - Using env_file=".env" keeps local/dev behavior.
    - The app should still start for non-chat endpoints even if GROQ_API_KEY is missing.
    """

    # Secrets
    groq_api_key: str | None = Field(None, alias="GROQ_API_KEY")
    jwt_secret_key: str = Field("default-insecure-secret-key", alias="JWT_SECRET_KEY")
    google_client_id: str | None = Field(None, alias="GOOGLE_CLIENT_ID")

    # Backend
    port: int = Field(8000, alias="PORT")
    cors_origins: str = Field("*", alias="CORS_ORIGINS")

    # Models
    default_model: str = Field("openai/gpt-oss-120b", alias="DEFAULT_MODEL")

    # RAG / storage
    embedding_model_name: str = Field(
        "sentence-transformers/all-MiniLM-L6-v2",
        alias="EMBEDDING_MODEL_NAME",
    )
    vector_store_dir: str = Field("vector_store", alias="VECTOR_STORE_DIR")

    # Resolve env_file relative to repository root (so uvicorn working directory
    # changes won't break config loading).
    # repo_root = AI-Chatbot/
    _repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    _env_path = os.path.join(_repo_root, ".env")

    # Do not hard-fail if .env is missing; allow endpoints to work in dev mode.
    model_config = SettingsConfigDict(env_file=_env_path, case_sensitive=False, extra="ignore")

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in (self.cors_origins or "").split(",") if o.strip()]


# Keep this for manual validation, but do not raise during import.
def _validate_required(settings: Settings) -> None:
    key = (settings.groq_api_key or "").strip()
    if not key:
        raise RuntimeError(
            "Missing required environment variable GROQ_API_KEY.\n"
            "Create AI-Chatbot/.env (or set it in your environment) with:\n"
            "  GROQ_API_KEY=your_key_here\n"
            "See AI-Chatbot/.env.example for all required variables."
        )


settings = Settings()

