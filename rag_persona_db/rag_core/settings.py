"""Configuration settings for RAG Persona Database."""

import os
from typing import Literal
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # ChromaDB Configuration
    chroma_dir: str = Field(default=".chromadb", env="CHROMA_DIR")
    chroma_collection: str = Field(default="echoai_knowledge", env="CHROMA_COLLECTION")
    
    # Embeddings Provider
    embeddings_provider: Literal["openai", "sentence-transformers"] = Field(
        default="openai", env="EMBEDDINGS_PROVIDER"
    )
    
    # OpenAI Configuration
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    openai_embed_model: str = Field(
        default="text-embedding-3-small", env="OPENAI_EMBED_MODEL"
    )
    
    # Local Embeddings Configuration
    local_embed_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", 
        env="LOCAL_EMBED_MODEL"
    )
    
    # Chunking Configuration
    chunk_size: int = Field(default=900, env="CHUNK_SIZE", ge=100, le=2000)
    chunk_overlap: int = Field(default=150, env="CHUNK_OVERLAP", ge=0, le=500)
    
    # Document Configuration
    default_visibility: Literal["public", "private"] = Field(
        default="public", env="DEFAULT_VISIBILITY"
    )
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    @validator("chunk_overlap")
    def validate_chunk_overlap(cls, v, values):
        """Ensure chunk overlap is less than chunk size."""
        if "chunk_size" in values and v >= values["chunk_size"]:
            raise ValueError("chunk_overlap must be less than chunk_size")
        return v
    
    @validator("openai_api_key")
    def validate_openai_key(cls, v, values):
        """Ensure OpenAI API key is provided when using OpenAI embeddings."""
        if values.get("embeddings_provider") == "openai" and not v:
            raise ValueError("OPENAI_API_KEY is required when using OpenAI embeddings")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def load_settings() -> Settings:
    """Load and return application settings."""
    return Settings()


# Global settings instance
settings = load_settings()
