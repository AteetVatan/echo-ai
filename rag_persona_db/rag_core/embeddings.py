"""Embeddings provider management and configuration."""

from typing import Union, Optional
from langchain_openai import OpenAIEmbeddings
from sentence_transformers import SentenceTransformer

from .settings import settings
from .logging_config import get_logger

logger = get_logger(__name__)


class EmbeddingsProvider:
    """Base class for embeddings providers."""
    
    def __init__(self):
        self.dimension = None
    
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of documents."""
        raise NotImplementedError
    
    def embed_query(self, text: str) -> list[float]:
        """Embed a single query."""
        raise NotImplementedError


class OpenAIEmbeddingsProvider(EmbeddingsProvider):
    """OpenAI embeddings provider."""
    
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        super().__init__()
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=api_key,
            model=model,
            dimensions=1536  # text-embedding-3-small default
        )
        self.dimension = 1536
        logger.info("OpenAI embeddings provider initialized", model=model)
    
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed documents using OpenAI."""
        try:
            embeddings = self.embeddings.embed_documents(texts)
            logger.debug("Documents embedded with OpenAI", count=len(texts))
            return embeddings
        except Exception as e:
            logger.error("Failed to embed documents with OpenAI", error=str(e))
            raise
    
    def embed_query(self, text: str) -> list[float]:
        """Embed query using OpenAI."""
        try:
            embedding = self.embeddings.embed_query(text)
            logger.debug("Query embedded with OpenAI")
            return embedding
        except Exception as e:
            logger.error("Failed to embed query with OpenAI", error=str(e))
            raise


class SentenceTransformersProvider(EmbeddingsProvider):
    """Local sentence-transformers embeddings provider."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        super().__init__()
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        logger.info("Sentence-transformers provider initialized", 
                   model=model_name, 
                   dimension=self.dimension)
    
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed documents using sentence-transformers."""
        try:
            embeddings = self.model.encode(texts, convert_to_tensor=False)
            # Convert to list of lists if needed
            if hasattr(embeddings, 'tolist'):
                embeddings = embeddings.tolist()
            logger.debug("Documents embedded with sentence-transformers", count=len(texts))
            return embeddings
        except Exception as e:
            logger.error("Failed to embed documents with sentence-transformers", error=str(e))
            raise
    
    def embed_query(self, text: str) -> list[float]:
        """Embed query using sentence-transformers."""
        try:
            embedding = self.model.encode([text], convert_to_tensor=False)
            # Convert to list if needed
            if hasattr(embedding, 'tolist'):
                embedding = embedding.tolist()
            if isinstance(embedding, list) and len(embedding) == 1:
                embedding = embedding[0]
            logger.debug("Query embedded with sentence-transformers")
            return embedding
        except Exception as e:
            logger.error("Failed to embed query with sentence-transformers", error=str(e))
            raise


def get_embeddings(provider: Optional[str] = None) -> EmbeddingsProvider:
    """Get embeddings provider based on configuration."""
    provider = provider or settings.embeddings_provider
    
    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key is required for OpenAI embeddings")
        
        return OpenAIEmbeddingsProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_embed_model
        )
    
    elif provider == "sentence-transformers":
        return SentenceTransformersProvider(
            model_name=settings.local_embed_model
        )
    
    else:
        raise ValueError(f"Unsupported embeddings provider: {provider}")


def get_embeddings_with_fallback() -> EmbeddingsProvider:
    """Get embeddings provider with fallback logic."""
    try:
        # Try OpenAI first if configured
        if settings.embeddings_provider == "openai" and settings.openai_api_key:
            return get_embeddings("openai")
    except Exception as e:
        logger.warning("OpenAI embeddings failed, falling back to sentence-transformers", 
                      error=str(e))
    
    # Fallback to sentence-transformers
    logger.info("Using sentence-transformers as embeddings provider")
    return get_embeddings("sentence-transformers")
