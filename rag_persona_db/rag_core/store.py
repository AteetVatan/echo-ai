"""Chroma vector store operations with idempotent upserts."""

import os
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_community.vectorstores import Chroma

from .schema import Metadata
from .embeddings import EmbeddingsProvider
from .settings import settings
from .logging_config import get_logger

logger = get_logger(__name__)


def sha256_hash(text: str) -> str:
    """Generate SHA256 hash of text content."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


class CareerVectorStore:
    """Chroma-based vector store for career and personality documents."""
    
    def __init__(self, 
                 persist_directory: str = None,
                 collection_name: str = None,
                 embeddings_provider: EmbeddingsProvider = None):
        """Initialize the vector store."""
        self.persist_directory = persist_directory or settings.chroma_dir
        self.collection_name = collection_name or settings.chroma_collection
        self.embeddings_provider = embeddings_provider
        
        # Ensure persist directory exists
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # Initialize Chroma client
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        logger.info("CareerVectorStore initialized", 
                   persist_directory=self.persist_directory,
                   collection_name=self.collection_name)
    
    def _get_existing_metadata(self, source_id: str, version: str) -> List[Dict[str, Any]]:
        """Get existing metadata for a source to check for duplicates."""
        try:
            results = self.collection.get(
                where={"source_id": source_id, "version": version}
            )
            return results.get("metadatas", [])
        except Exception as e:
            logger.warning("Failed to get existing metadata", 
                          source_id=source_id, 
                          version=version, 
                          error=str(e))
            return []
    
    def _filter_new_chunks(self, 
                          texts: List[str], 
                          metadatas: List[Dict[str, Any]]) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Filter out chunks that already exist in the store."""
        if not texts or not metadatas:
            return [], []
        
        new_texts = []
        new_metadatas = []
        
        for text, metadata in zip(texts, metadatas):
            source_id = metadata.get("source_id")
            version = metadata.get("version")
            content_hash = metadata.get("content_sha256")
            
            if not all([source_id, version, content_hash]):
                logger.warning("Missing required metadata fields", metadata=metadata)
                continue
            
            # Check if this chunk already exists
            existing_metadata = self._get_existing_metadata(source_id, version)
            is_duplicate = any(
                existing.get("content_sha256") == content_hash 
                for existing in existing_metadata
            )
            
            if not is_duplicate:
                new_texts.append(text)
                new_metadatas.append(metadata)
            else:
                logger.debug("Skipping duplicate chunk", 
                           source_id=source_id, 
                           content_hash=content_hash[:8])
        
        logger.info("Filtered chunks", 
                   original_count=len(texts),
                   new_count=len(new_texts),
                   duplicates=len(texts) - len(new_texts))
        
        return new_texts, new_metadatas
    
    def upsert(self, 
               texts: List[str], 
               metadatas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Upsert texts with metadata, avoiding duplicates."""
        if not texts or not metadatas:
            logger.warning("No texts or metadatas provided for upsert")
            return {"added": 0, "skipped": 0, "total": 0}
        
        if len(texts) != len(metadatas):
            raise ValueError("Texts and metadatas must have the same length")
        
        # Filter out existing chunks
        new_texts, new_metadatas = self._filter_new_chunks(texts, metadatas)
        
        if not new_texts:
            logger.info("No new chunks to add")
            return {"added": 0, "skipped": len(texts), "total": len(texts)}
        
        try:
            # Add new chunks to the collection
            self.collection.add(
                documents=new_texts,
                metadatas=new_metadatas,
                ids=[f"{metadata.get('source_id', 'unknown')}_{i}" 
                     for i, metadata in enumerate(new_metadatas)]
            )
            
            logger.info("Chunks added successfully", 
                       added=len(new_texts),
                       skipped=len(texts) - len(new_texts))
            
            return {
                "added": len(new_texts),
                "skipped": len(texts) - len(new_texts),
                "total": len(texts)
            }
            
        except Exception as e:
            logger.error("Failed to upsert chunks", error=str(e))
            raise
    
    def search(self, 
               query: str, 
               n_results: int = 10, 
               where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for similar documents."""
        try:
            # Get query embedding
            if self.embeddings_provider:
                query_embedding = self.embeddings_provider.embed_query(query)
            else:
                # Use Chroma's default embedding if no provider specified
                query_embedding = None
            
            # Perform search
            results = self.collection.query(
                query_texts=[query] if query_embedding is None else None,
                query_embeddings=[query_embedding] if query_embedding is not None else None,
                n_results=n_results,
                where=where
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results.get("documents", []))):
                formatted_results.append({
                    "content": results["documents"][i],
                    "metadata": results["metadatas"][i],
                    "distance": results["distances"][i] if "distances" in results else None,
                    "id": results["ids"][i] if "ids" in results else None
                })
            
            logger.info("Search completed", 
                       query=query[:50] + "..." if len(query) > 50 else query,
                       results=len(formatted_results))
            
            return formatted_results
            
        except Exception as e:
            logger.error("Search failed", query=query, error=str(e))
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        try:
            count = self.collection.count()
            
            # Get sample metadata to analyze document types
            sample_results = self.collection.get(limit=min(100, count))
            metadatas = sample_results.get("metadatas", [])
            
            # Count by document type
            doc_type_counts = {}
            source_counts = {}
            for metadata in metadatas:
                doc_type = metadata.get("doc_type", "unknown")
                source_id = metadata.get("source_id", "unknown")
                
                doc_type_counts[doc_type] = doc_type_counts.get(doc_type, 0) + 1
                source_counts[source_id] = source_counts.get(source_id, 0) + 1
            
            stats = {
                "total_chunks": count,
                "document_types": doc_type_counts,
                "sources": source_counts,
                "collection_name": self.collection_name,
                "persist_directory": self.persist_directory
            }
            
            logger.info("Collection stats retrieved", total_chunks=count)
            return stats
            
        except Exception as e:
            logger.error("Failed to get collection stats", error=str(e))
            raise
    
    def as_retriever(self, 
                     k: int = 6, 
                     mmr_lambda: float = 0.35,
                     where: Optional[Dict[str, Any]] = None):
        """Get a retriever interface for the vector store."""
        # Create LangChain Chroma vector store for retriever interface
        if not self.embeddings_provider:
            raise ValueError("Embeddings provider required for retriever interface")
        
        # Convert to LangChain format
        langchain_chroma = Chroma(
            client=self.client,
            collection_name=self.collection_name,
            embedding_function=self.embeddings_provider.embeddings if hasattr(self.embeddings_provider, 'embeddings') else None,
            persist_directory=self.persist_directory
        )
        
        return langchain_chroma.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": k,
                "lambda_mult": mmr_lambda,
                "filter": where
            }
        )
    
    def reset_collection(self):
        """Reset the collection (remove all documents)."""
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("Collection reset successfully", collection_name=self.collection_name)
        except Exception as e:
            logger.error("Failed to reset collection", error=str(e))
            raise
