"""
Application configuration using Pydantic Settings.

All configuration is loaded from environment variables (or .env file).
This ensures no secrets are hardcoded and configuration is validated at startup.
"""

import os
from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PLACEHOLDER_JWT_SECRET = "change-this-to-a-random-64-char-hex-string"


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

    # --- LLM (Google AI Studio / Gemini) ---
    GEMINI_API_KEY: str = ""
    DEFAULT_LLM_MODEL: str = "gemini-2.5-flash"
    # Hard ceiling (seconds) on a single LLM call before it is treated as a
    # retryable failure, so a hung request can't stall the pipeline forever.
    LLM_TIMEOUT_SECONDS: float = 90.0
    # An analysis still PROCESSING after this long is presumed dead (the
    # serverless invocation running it was killed) and reported as FAILED so
    # the client stops polling and can retry. Must exceed the longest
    # realistic pipeline run.
    ANALYSIS_TIMEOUT_SECONDS: float = 600.0

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://exyst:exyst_password@localhost:5432/exyst_db"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def convert_postgres_scheme(cls, v: str) -> str:
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # --- JWT Auth ---
    JWT_SECRET_KEY: str = _PLACEHOLDER_JWT_SECRET
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Email (password reset) ---
    # Without RESEND_API_KEY the app does not send mail: in DEBUG the message
    # (including the reset link) is logged instead, so the flow is testable
    # locally. Outside DEBUG a missing key means reset emails silently don't
    # arrive — set it in production.
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "Exyst <onboarding@resend.dev>"
    # Base URL of the frontend, used to build links in emails.
    APP_BASE_URL: str = "http://localhost:3000"
    PASSWORD_RESET_EXPIRE_MINUTES: int = 60

    # --- File Storage ---
    UPLOAD_DIR: str = "/tmp/uploads" if os.environ.get("VERCEL") else "uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.DATABASE_URL

    @model_validator(mode="after")
    def _validate_security(self) -> "Settings":
        """
        Fail fast on insecure production config.

        A wildcard CORS origin combined with credentialed requests is never
        valid, and shipping the placeholder JWT secret outside DEBUG would let
        anyone forge tokens for any user. Both are allowed only in DEBUG so
        local development stays frictionless.
        """
        if "*" in self.CORS_ORIGINS:
            raise ValueError(
                "CORS_ORIGINS must not contain '*' (credentials are enabled); "
                "list explicit origins instead."
            )
        if not self.DEBUG and self.JWT_SECRET_KEY == _PLACEHOLDER_JWT_SECRET:
            raise ValueError(
                "JWT_SECRET_KEY is still the placeholder default. Set a strong "
                "random secret, e.g. `python -c \"import secrets; "
                "print(secrets.token_hex(32))\"`."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings instance.
    Call this instead of creating Settings() directly.
    """
    return Settings()
