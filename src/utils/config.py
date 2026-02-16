"""
Configuration management for EchoAI voice chat system.

This module handles environment variable loading, validation, and provides
centralized configuration for all services including API keys, model settings,
and latency optimization parameters.
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    MISTRAL_API_KEY: str = Field(..., env="MISTRAL_API_KEY")
    
    FALLBACK_STT_MODEL: str = Field("openai/whisper-1", env="FALLBACK_STT_MODEL")
    MISTRAL_MODEL: str = Field("mistral-small", env="MISTRAL_MODEL")
    OPENAI_MODEL: str = Field("gpt-4o-mini", env="OPENAI_MODEL")
   
    
    # Mistral Configuration
    MISTRAL_API_BASE: str = Field("https://api.mistral.ai", env="MISTRAL_API_BASE")
    
    # Edge-TTS Configuration
    EDGE_TTS_VOICE: str = Field("en-IN-PrabhatNeural", env="EDGE_TTS_VOICE")
    
    # Latency Configuration
    STT_CHUNK_DURATION: float = Field(2.0, env="STT_CHUNK_DURATION")
    LLM_TEMPERATURE: float = Field(0.0, env="LLM_TEMPERATURE")
    TTS_STREAMING: bool = Field(True, env="TTS_STREAMING")
    TTS_CACHE_ENABLED: bool = Field(True, env="TTS_CACHE_ENABLED")
    
    # Supabase DB
    SUPABASE_URL: str = Field(..., env="SUPABASE_URL")
    SUPABASE_ANON_KEY: str = Field(..., env="SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(..., env="SUPABASE_SERVICE_ROLE_KEY")
    SUPABASE_DB_PASSWORD: str = Field(..., env="SUPABASE_DB_PASSWORD")
    SUPABASE_DB_URL: str = Field(..., env="SUPABASE_DB_URL")
    
    # Server Configuration
    HOST: str = Field("0.0.0.0", env="HOST")
    PORT: int = Field(8000, env="PORT")
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    DEBUG: bool = Field(False, env="DEBUG")
    
    # Audio Configuration
    SAMPLE_RATE: int = Field(16000, env="SAMPLE_RATE")
    CHANNELS: int = Field(1, env="CHANNELS")
    AUDIO_FORMAT: str = Field("wav", env="AUDIO_FORMAT")
    
    # Latency Thresholds (in seconds)
    STT_TIMEOUT: float = Field(5.0, env="STT_TIMEOUT")
    LLM_TIMEOUT: float = Field(10.0, env="LLM_TIMEOUT")
    TTS_TIMEOUT: float = Field(8.0, env="TTS_TIMEOUT")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


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
        settings.OPENAI_API_KEY,
        settings.MISTRAL_API_KEY
    ]
    
    return all(key and key != "hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" 
               and key != "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
               and key != "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" 
               and key != "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
               for key in required_keys) 