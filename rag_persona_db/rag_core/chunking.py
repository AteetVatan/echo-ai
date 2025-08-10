"""Text chunking functionality for document processing."""

from typing import List, Tuple
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .schema import DocumentItem, Metadata
from .logging_config import get_logger
from .settings import settings

logger = get_logger(__name__)


class Chunker:
    """Text chunking utility with configurable parameters."""
    
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        """Initialize chunker with configuration."""
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        
        # Initialize the text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
        )
        
        logger.info("Chunker initialized", 
                   chunk_size=self.chunk_size, 
                   chunk_overlap=self.chunk_overlap)
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks."""
        if not text or not text.strip():
            return []
        
        try:
            chunks = self.text_splitter.split_text(text)
            logger.debug("Text chunked successfully", 
                        original_length=len(text), 
                        chunks=len(chunks))
            return chunks
        except Exception as e:
            logger.error("Failed to chunk text", error=str(e))
            raise
    
    def chunk_document(self, document: DocumentItem) -> List[Tuple[str, Metadata]]:
        """Chunk a single document into multiple chunks with metadata."""
        if not document.content.strip():
            logger.warning("Document has no content", 
                         source_id=document.metadata.source_id)
            return []
        
        # Split content into chunks
        text_chunks = self.chunk_text(document.content)
        
        if not text_chunks:
            logger.warning("No chunks generated", 
                         source_id=document.metadata.source_id)
            return []
        
        # Create chunk metadata for each text chunk
        chunked_items = []
        for i, chunk_text in enumerate(text_chunks):
            # Create new metadata for this chunk
            chunk_metadata = document.to_chunk_metadata(
                chunk_index=i,
                total_chunks=len(text_chunks),
                content_sha256=document.metadata.content_sha256
            )
            
            chunked_items.append((chunk_text, chunk_metadata))
        
        logger.info("Document chunked successfully", 
                   source_id=document.metadata.source_id,
                   original_chunks=document.metadata.total_chunks,
                   new_chunks=len(chunked_items))
        
        return chunked_items
    
    def chunk_documents(self, documents: List[DocumentItem]) -> List[Tuple[str, Metadata]]:
        """Chunk multiple documents into chunks with metadata."""
        all_chunks = []
        
        for document in documents:
            try:
                chunks = self.chunk_document(document)
                all_chunks.extend(chunks)
            except Exception as e:
                logger.error("Failed to chunk document", 
                           source_id=document.metadata.source_id,
                           error=str(e))
                continue
        
        logger.info("All documents chunked", 
                   total_documents=len(documents),
                   total_chunks=len(all_chunks))
        
        return all_chunks
    
    def get_chunk_stats(self, chunks: List[Tuple[str, Metadata]]) -> dict:
        """Get statistics about the generated chunks."""
        if not chunks:
            return {
                "total_chunks": 0,
                "avg_chunk_size": 0,
                "min_chunk_size": 0,
                "max_chunk_size": 0,
                "total_characters": 0
            }
        
        chunk_sizes = [len(chunk[0]) for chunk in chunks]
        
        stats = {
            "total_chunks": len(chunks),
            "avg_chunk_size": sum(chunk_sizes) / len(chunk_sizes),
            "min_chunk_size": min(chunk_sizes),
            "max_chunk_size": max(chunk_sizes),
            "total_characters": sum(chunk_sizes)
        }
        
        return stats
