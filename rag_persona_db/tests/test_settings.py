"""Tests for RAG Persona Database settings configuration."""

import pytest
import os
from unittest.mock import patch
from pydantic import ValidationError

from rag_persona_db.rag_core.settings import Settings, load_settings


class TestSettings:
    """Test Settings model validation and configuration."""
    
    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()
        
        assert settings.chroma_dir == ".chromadb"
        assert settings.chroma_collection == "echoai_knowledge"
        assert settings.embeddings_provider == "openai"
        assert settings.openai_embed_model == "text-embedding-3-small"
        assert settings.local_embed_model == "sentence-transformers/all-MiniLM-L6-v2"
        assert settings.chunk_size == 900
        assert settings.chunk_overlap == 150
        assert settings.default_visibility == "public"
        assert settings.log_level == "INFO"
    
    def test_environment_variable_override(self):
        """Test environment variable overrides."""
        with patch.dict(os.environ, {
            "CHROMA_DIR": "/custom/chroma",
            "CHROMA_COLLECTION": "custom_collection",
            "EMBEDDINGS_PROVIDER": "sentence-transformers",
            "CHUNK_SIZE": "1200",
            "CHUNK_OVERLAP": "200",
            "DEFAULT_VISIBILITY": "private",
            "LOG_LEVEL": "DEBUG"
        }):
            settings = Settings()
            
            assert settings.chroma_dir == "/custom/chroma"
            assert settings.chroma_collection == "custom_collection"
            assert settings.embeddings_provider == "sentence-transformers"
            assert settings.chunk_size == 1200
            assert settings.chunk_overlap == 200
            assert settings.default_visibility == "private"
            assert settings.log_level == "DEBUG"
    
    def test_chunk_overlap_validation(self):
        """Test chunk overlap validation."""
        # Valid overlap
        settings = Settings(chunk_size=1000, chunk_overlap=200)
        assert settings.chunk_overlap == 200
        
        # Invalid overlap - equal to chunk size
        with pytest.raises(ValidationError, match="chunk_overlap must be less than chunk_size"):
            Settings(chunk_size=1000, chunk_overlap=1000)
        
        # Invalid overlap - greater than chunk size
        with pytest.raises(ValidationError, match="chunk_overlap must be less than chunk_size"):
            Settings(chunk_size=1000, chunk_overlap=1200)
    
    def test_chunk_size_validation(self):
        """Test chunk size validation."""
        # Valid chunk sizes
        settings = Settings(chunk_size=100)
        assert settings.chunk_size == 100
        
        settings = Settings(chunk_size=2000)
        assert settings.chunk_size == 2000
        
        # Invalid chunk size - too small
        with pytest.raises(ValidationError, match="ensure this value is greater than or equal to 100"):
            Settings(chunk_size=50)
        
        # Invalid chunk size - too large
        with pytest.raises(ValidationError, match="ensure this value is less than or equal to 2000"):
            Settings(chunk_size=2500)
    
    def test_chunk_overlap_validation(self):
        """Test chunk overlap validation."""
        # Valid overlap
        settings = Settings(chunk_size=1000, chunk_overlap=100)
        assert settings.chunk_overlap == 100
        
        settings = Settings(chunk_size=1000, chunk_overlap=500)
        assert settings.chunk_overlap == 500
        
        # Invalid overlap - too large
        with pytest.raises(ValidationError, match="ensure this value is less than or equal to 500"):
            Settings(chunk_size=1000, chunk_overlap=600)
        
        # Invalid overlap - negative
        with pytest.raises(ValidationError, match="ensure this value is greater than or equal to 0"):
            Settings(chunk_size=1000, chunk_overlap=-50)
    
    def test_openai_api_key_validation(self):
        """Test OpenAI API key validation."""
        # OpenAI provider without API key should fail
        with pytest.raises(ValidationError, match="OPENAI_API_KEY is required when using OpenAI embeddings"):
            Settings(embeddings_provider="openai", openai_api_key="")
        
        # OpenAI provider with API key should work
        settings = Settings(embeddings_provider="openai", openai_api_key="sk-123456")
        assert settings.openai_api_key == "sk-123456"
        
        # Local provider without OpenAI API key should work
        settings = Settings(embeddings_provider="sentence-transformers", openai_api_key="")
        assert settings.openai_api_key == ""
    
    def test_embeddings_provider_validation(self):
        """Test embeddings provider validation."""
        # Valid providers
        settings = Settings(embeddings_provider="openai")
        assert settings.embeddings_provider == "openai"
        
        settings = Settings(embeddings_provider="sentence-transformers")
        assert settings.embeddings_provider == "sentence-transformers"
        
        # Invalid provider
        with pytest.raises(ValidationError):
            Settings(embeddings_provider="invalid_provider")
    
    def test_visibility_validation(self):
        """Test visibility validation."""
        # Valid visibility values
        settings = Settings(default_visibility="public")
        assert settings.default_visibility == "public"
        
        settings = Settings(default_visibility="private")
        assert settings.default_visibility == "private"
        
        # Invalid visibility
        with pytest.raises(ValidationError):
            Settings(default_visibility="invalid_visibility")
    
    def test_model_name_override(self):
        """Test model name override based on provider."""
        # OpenAI provider should use OpenAI model
        settings = Settings(
            embeddings_provider="openai",
            openai_api_key="sk-123456"
        )
        assert "text-embedding" in settings.openai_embed_model
        
        # Local provider should use local model
        settings = Settings(embeddings_provider="sentence-transformers")
        assert "sentence-transformers" in settings.local_embed_model
    
    def test_settings_immutability(self):
        """Test that settings are properly configured."""
        settings = Settings()
        
        # Verify all required fields are present
        assert hasattr(settings, 'chroma_dir')
        assert hasattr(settings, 'chroma_collection')
        assert hasattr(settings, 'embeddings_provider')
        assert hasattr(settings, 'chunk_size')
        assert hasattr(settings, 'chunk_overlap')
        assert hasattr(settings, 'default_visibility')
        assert hasattr(settings, 'log_level')
    
    def test_custom_chroma_configuration(self):
        """Test custom ChromaDB configuration."""
        settings = Settings(
            chroma_dir="/custom/path",
            chroma_collection="my_collection"
        )
        
        assert settings.chroma_dir == "/custom/path"
        assert settings.chroma_collection == "my_collection"
    
    def test_custom_embedding_models(self):
        """Test custom embedding model configuration."""
        settings = Settings(
            openai_embed_model="text-embedding-ada-002",
            local_embed_model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        
        assert settings.openai_embed_model == "text-embedding-ada-002"
        assert settings.local_embed_model == "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class TestLoadSettings:
    """Test settings loading functionality."""
    
    def test_load_settings_function(self):
        """Test load_settings function returns Settings instance."""
        settings = load_settings()
        assert isinstance(settings, Settings)
    
    def test_global_settings_instance(self):
        """Test global settings instance is available."""
        from rag_persona_db.rag_core.settings import settings
        assert isinstance(settings, Settings)
    
    def test_environment_file_loading(self):
        """Test .env file loading configuration."""
        settings = Settings()
        
        # Verify Config class is properly set
        assert hasattr(settings.__class__, 'Config')
        assert settings.__class__.Config.env_file == ".env"
        assert settings.__class__.Config.env_file_encoding == "utf-8"
        assert settings.__class__.Config.case_sensitive is False


class TestSettingsIntegration:
    """Test settings integration with other components."""
    
    def test_settings_with_document_processing(self):
        """Test settings work with document processing parameters."""
        settings = Settings(
            chunk_size=800,
            chunk_overlap=100,
            default_visibility="private"
        )
        
        # These settings should be usable for document processing
        assert settings.chunk_size + settings.chunk_overlap < 1000
        assert settings.chunk_overlap < settings.chunk_size
        assert settings.default_visibility in ["public", "private"]
    
    def test_settings_with_vector_store(self):
        """Test settings work with vector store configuration."""
        settings = Settings(
            chroma_dir="/data/vector_store",
            chroma_collection="my_documents"
        )
        
        # These settings should be usable for vector store initialization
        assert settings.chroma_dir == "/data/vector_store"
        assert settings.chroma_collection == "my_documents"
    
    def test_settings_with_embeddings(self):
        """Test settings work with embedding service configuration."""
        # Test OpenAI configuration
        openai_settings = Settings(
            embeddings_provider="openai",
            openai_api_key="sk-123456",
            openai_embed_model="text-embedding-3-large"
        )
        
        assert openai_settings.embeddings_provider == "openai"
        assert openai_settings.openai_api_key == "sk-123456"
        assert openai_settings.openai_embed_model == "text-embedding-3-large"
        
        # Test local configuration
        local_settings = Settings(
            embeddings_provider="sentence-transformers",
            local_embed_model="sentence-transformers/all-mpnet-base-v2"
        )
        
        assert local_settings.embeddings_provider == "sentence-transformers"
        assert "all-mpnet-base-v2" in local_settings.local_embed_model
