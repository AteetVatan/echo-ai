"""
Configuration management for EchoAI voice chat system.

This module handles environment variable loading, validation, and provides
centralized configuration for all services including API keys, model settings,
and latency optimization parameters.
"""

import os
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _REPO_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), case_sensitive=True)

    DEEPSEEK_API_KEY: str = Field(...)
    OPENAI_API_KEY: str = Field(...)
    MISTRAL_API_KEY: str = Field(...)

    FALLBACK_STT_MODEL: str = Field("openai/whisper-1")
    DEEPSEEK_MODEL: str = Field("deepseek-chat")
    MISTRAL_MODEL: str = Field("mistral-small")
    OPENAI_MODEL: str = Field("gpt-4o-mini")

    # DeepSeek Configuration (Primary LLM)
    DEEPSEEK_API_BASE: str = Field("https://api.deepseek.com")

    # Mistral Configuration (Fallback LLM)
    MISTRAL_API_BASE: str = Field("https://api.mistral.ai")

    # Edge-TTS Configuration
    EDGE_TTS_VOICE: str = Field("en-US-AndrewMultilingualNeural")

    # Latency Configuration
    STT_CHUNK_DURATION: float = Field(2.0)
    LLM_TEMPERATURE: float = Field(0.0)
    TTS_STREAMING: bool = Field(True)
    TTS_CACHE_ENABLED: bool = Field(True)

    # Self-Info RAG Knowledge Base
    EMBEDDING_MODEL: str = Field("all-MiniLM-L6-v2")
    SELF_INFO_JSON_PATH: str = Field("backend/documents/self_info.json")
    SELF_INFO_REBUILD: bool = Field(False)
    EVIDENCE_DOCS_DIR: str = Field("rag_persona_db/document")

    # Supabase DB (Required — all storage uses Supabase)
    SUPABASE_URL: str = Field("")
    SUPABASE_ANON_KEY: str = Field("")
    SUPABASE_SERVICE_ROLE_KEY: str = Field("")
    SUPABASE_DB_PASSWORD: str = Field("")
    SUPABASE_DB_URL: str = Field("")

    # HuggingFace Configuration
    HF_TOKEN: str = Field("")

    # Server Configuration
    HOST: str = Field("0.0.0.0")
    PORT: int = Field(8000)
    FRONTEND_URL: str = Field("http://localhost:3000")
    LOG_LEVEL: str = Field("INFO")
    DEBUG: bool = Field(False)

    # Audio Configuration
    SAMPLE_RATE: int = Field(16000)
    CHANNELS: int = Field(1)
    AUDIO_FORMAT: str = Field("wav")

    # Latency Thresholds (in seconds)
    STT_TIMEOUT: float = Field(5.0)
    LLM_TIMEOUT: float = Field(10.0)
    TTS_TIMEOUT: float = Field(8.0)

    # Security Configuration
    ECHOAI_API_KEY: str = Field("")
    ALLOWED_ORIGINS: str = Field("http://localhost:3000,http://localhost:8000")
    RATE_LIMIT_PER_MINUTE: int = Field(30)
    WS_MSG_RATE_LIMIT: int = Field(20)
    MAX_WS_CONNECTIONS_PER_IP: int = Field(5)
    MAX_TEXT_LENGTH: int = Field(2000)

    # Serverless Optimization
    SKIP_TTS_WARMUP: bool = Field(False)

    @field_validator(
        "DEBUG",
        "TTS_STREAMING",
        "TTS_CACHE_ENABLED",
        "SELF_INFO_REBUILD",
        "SKIP_TTS_WARMUP",
        mode="before",
    )
    @classmethod
    def _parse_bool_env(cls, value: Any) -> Any:
        """Accept common deployment strings for boolean env vars."""
        if not isinstance(value, str):
            return value
        normalized = value.strip().lower()
        if normalized in {"release", "prod", "production", "false", "0", "no", "off"}:
            return False
        if normalized in {"debug", "dev", "development", "true", "1", "yes", "on"}:
            return True
        return value

    def model_post_init(self, __context: Any) -> None:
        """Inject HF_TOKEN into os.environ so HuggingFace libraries can find it."""
        if self.HF_TOKEN:
            os.environ["HF_TOKEN"] = self.HF_TOKEN


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings instance."""
    return settings


def validate_api_keys() -> bool:
    """
    Validate that all required API keys are present.

    Returns:
        bool: True if all keys are present, False otherwise
    """
    required_keys = [
        settings.DEEPSEEK_API_KEY,
        settings.OPENAI_API_KEY,
        settings.MISTRAL_API_KEY,
    ]

    return all(
        key
        and key != "hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        and key != "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        and key != "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        and key != "your-deepseek-api-key-here"
        for key in required_keys
    )
