"""
Configuration settings for the DigiPlus AI Service.

Loads configuration from environment variables or .env/.env.local files
using pydantic-settings.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable overrides."""
    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database Configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/support_desk"
    )

    # Gemini & Embedding Model Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    EMBED_MODEL: str = os.getenv("EMBED_MODEL", "gemini-embedding-001")
    EMBED_DIM: int = 768  # Single constant pinned to match pgvector schema

    # AI Service Configuration
    AI_SERVICE_URL: str = os.getenv("AI_SERVICE_URL", "http://localhost:8000")
    APP_VERSION: str = "1.0.0"

    # Feature Flags
    USE_HYBRID: bool = True
    USE_RERANK: bool = True


# Global settings instance
settings = Settings()
