"""
Configuration management for EchoAI voice chat system.

This module handles environment variable loading, validation, and provides
centralized configuration for all services including API keys, model settings,
and latency optimization parameters.
"""

import os
from typing import Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    HUGGINGFACE_API_KEY: str = Field(..., env="HUGGINGFACE_API_KEY")
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    ELEVENLABS_API_KEY: str = Field(..., env="ELEVENLABS_API_KEY")
    
    # Model Configuration
    DEFAULT_STT_MODEL: str = Field("openai/whisper-large-v3", env="DEFAULT_STT_MODEL")
    FALLBACK_STT_MODEL: str = Field("openai/whisper-1", env="FALLBACK_STT_MODEL")
    DEFAULT_LLM_MODEL: str = Field("mistralai/Mistral-7B-Instruct-v0.2", env="DEFAULT_LLM_MODEL")
    FALLBACK_LLM_MODEL: str = Field("gpt-4o-mini", env="FALLBACK_LLM_MODEL")
    ELEVENLABS_VOICE_ID: str = Field("21m00Tcm4TlvDq8ikWAM", env="ELEVENLABS_VOICE_ID")
    
    # Latency Configuration
    STT_CHUNK_DURATION: float = Field(2.0, env="STT_CHUNK_DURATION")
    LLM_TEMPERATURE: float = Field(0.0, env="LLM_TEMPERATURE")
    TTS_STREAMING: bool = Field(True, env="TTS_STREAMING")
    TTS_CACHE_ENABLED: bool = Field(True, env="TTS_CACHE_ENABLED")
    
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
        settings.HUGGINGFACE_API_KEY,
        settings.OPENAI_API_KEY,
        settings.ELEVENLABS_API_KEY
    ]
    
    return all(key and key != "hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" 
               and key != "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
               and key != "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" 
               for key in required_keys) 