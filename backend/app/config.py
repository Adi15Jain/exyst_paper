"""
Application configuration using Pydantic Settings.

All configuration is loaded from environment variables (or .env file).
This ensures no secrets are hardcoded and configuration is validated at startup.
"""

import os
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration for the Exyst backend.
    Values are loaded from environment variables or .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    APP_NAME: str = "Exyst"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # --- LLM Providers ---
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    HF_TOKEN: str = ""
    DEFAULT_LLM_MODEL: str = "gemini/gemini-2.5-flash"

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://exyst:exyst_password@localhost:5432/exyst_db"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def convert_postgres_scheme(cls, v: str) -> str:
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # --- JWT Auth ---
    JWT_SECRET_KEY: str = "change-this-to-a-random-64-char-hex-string"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- File Storage ---
    UPLOAD_DIR: str = "/tmp/uploads" if os.environ.get("VERCEL") else "uploads"
    OUTPUTS_DIR: str = "/tmp/outputs" if os.environ.get("VERCEL") else "outputs"
    MAX_UPLOAD_SIZE_MB: int = 50

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.DATABASE_URL

    @property
    def database_url_sync(self) -> str:
        """Sync database URL for Alembic migrations."""
        return self.DATABASE_URL.replace("+asyncpg", "+psycopg2")


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings instance.
    Call this instead of creating Settings() directly.
    """
    return Settings()
