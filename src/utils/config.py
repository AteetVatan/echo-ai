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
    huggingface_api_key: str = Field(..., env="HUGGINGFACE_API_KEY")
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    elevenlabs_api_key: str = Field(..., env="ELEVENLABS_API_KEY")
    
    # Model Configuration
    default_stt_model: str = Field("openai/whisper-large-v3", env="DEFAULT_STT_MODEL")
    fallback_stt_model: str = Field("openai/whisper-1", env="FALLBACK_STT_MODEL")
    default_llm_model: str = Field("mistralai/Mistral-7B-Instruct-v0.2", env="DEFAULT_LLM_MODEL")
    fallback_llm_model: str = Field("gpt-4o-mini", env="FALLBACK_LLM_MODEL")
    default_tts_voice_id: str = Field("21m00Tcm4TlvDq8ikWAM", env="DEFAULT_TTS_VOICE_ID")
    
    # Latency Configuration
    stt_chunk_duration: float = Field(2.0, env="STT_CHUNK_DURATION")
    llm_temperature: float = Field(0.0, env="LLM_TEMPERATURE")
    tts_streaming: bool = Field(True, env="TTS_STREAMING")
    cache_tts_responses: bool = Field(True, env="CACHE_TTS_RESPONSES")
    
    # Server Configuration
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    debug: bool = Field(False, env="DEBUG")
    
    # Audio Configuration
    sample_rate: int = Field(16000, env="SAMPLE_RATE")
    channels: int = Field(1, env="CHANNELS")
    audio_format: str = Field("wav", env="AUDIO_FORMAT")
    
    # Latency Thresholds (in seconds)
    stt_timeout: float = Field(5.0, env="STT_TIMEOUT")
    llm_timeout: float = Field(10.0, env="LLM_TIMEOUT")
    tts_timeout: float = Field(8.0, env="TTS_TIMEOUT")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


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
        settings.huggingface_api_key,
        settings.openai_api_key,
        settings.elevenlabs_api_key
    ]
    
    return all(key and key != "hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" 
               and key != "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
               and key != "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" 
               for key in required_keys) 