"""Agno-based orchestration flow for document processing pipeline."""

from typing import List, Dict, Any, Optional
from pathlib import Path
import time

from agno import Agent, Task, Workflow

from .loaders import load_documents_from_directory
from .chunking import Chunker
from .embeddings import get_embeddings_with_fallback
from .store import CareerVectorStore
from .schema import DocumentItem
from .logging_config import get_logger
from .settings import settings

logger = get_logger(__name__)


class IngestAgent(Agent):
    """Agent responsible for loading documents from various sources."""
    
    def __init__(self):
        super().__init__("IngestAgent")
        self.logger = get_logger(f"{__name__}.IngestAgent")
    
    def process(self, input_path: str) -> List[DocumentItem]:
        """Load documents from the specified input path."""
        self.logger.info("Starting document ingestion", input_path=input_path)
        
        try:
            if Path(input_path).is_file():
                # Single file
                from .loaders import load_document
                documents = load_document(input_path)
            else:
                # Directory
                documents = load_documents_from_directory(input_path)
            
            self.logger.info("Document ingestion completed", 
                           input_path=input_path,
                           documents=len(documents))
            
            return documents
            
        except Exception as e:
            self.logger.error("Document ingestion failed", 
                            input_path=input_path,
                            error=str(e))
            raise


class PreprocessAgent(Agent):
    """Agent responsible for document preprocessing and cleaning."""
    
    def __init__(self):
        super().__init__("PreprocessAgent")
        self.logger = get_logger(f"{__name__}.PreprocessAgent")
    
    def process(self, documents: List[DocumentItem]) -> List[DocumentItem]:
        """Preprocess and clean documents."""
        self.logger.info("Starting document preprocessing", documents=len(documents))
        
        processed_documents = []
        
        for document in documents:
            try:
                # Basic text cleaning
                cleaned_content = self._clean_text(document.content)
                
                # Create new document with cleaned content
                processed_doc = DocumentItem(
                    content=cleaned_content,
                    metadata=document.metadata,
                    file_path=document.file_path,
                    file_size=document.file_size,
                    file_extension=document.file_extension
                )
                
                processed_documents.append(processed_doc)
                
            except Exception as e:
                self.logger.warning("Failed to preprocess document", 
                                  source_id=document.metadata.source_id,
                                  error=str(e))
                # Keep original document if preprocessing fails
                processed_documents.append(document)
        
        self.logger.info("Document preprocessing completed", 
                        original=len(documents),
                        processed=len(processed_documents))
        
        return processed_documents
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return text
        
        # Remove excessive whitespace
        import re
        text = re.sub(r'\s+', ' ', text)
        
        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        return text.strip()


class ChunkAgent(Agent):
    """Agent responsible for text chunking."""
    
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        super().__init__("ChunkAgent")
        self.logger = get_logger(f"{__name__}.ChunkAgent")
        self.chunker = Chunker(chunk_size, chunk_overlap)
    
    def process(self, documents: List[DocumentItem]) -> List[tuple]:
        """Chunk documents into smaller pieces."""
        self.logger.info("Starting document chunking", documents=len(documents))
        
        try:
            chunks = self.chunker.chunk_documents(documents)
            
            # Get chunk statistics
            stats = self.chunker.get_chunk_stats(chunks)
            
            self.logger.info("Document chunking completed", 
                           documents=len(documents),
                           chunks=len(chunks),
                           stats=stats)
            
            return chunks
            
        except Exception as e:
            self.logger.error("Document chunking failed", error=str(e))
            raise


class EmbedAgent(Agent):
    """Agent responsible for generating embeddings."""
    
    def __init__(self):
        super().__init__("EmbedAgent")
        self.logger = get_logger(f"{__name__}.EmbedAgent")
        self.embeddings_provider = None
    
    def process(self, chunks: List[tuple]) -> List[tuple]:
        """Generate embeddings for text chunks."""
        self.logger.info("Starting embedding generation", chunks=len(chunks))
        
        try:
            # Initialize embeddings provider if not already done
            if self.embeddings_provider is None:
                self.embeddings_provider = get_embeddings_with_fallback()
                self.logger.info("Embeddings provider initialized", 
                               provider=type(self.embeddings_provider).__name__)
            
            # For now, we'll just pass through the chunks
            # Embeddings will be generated when storing in the vector store
            self.logger.info("Embedding generation completed", chunks=len(chunks))
            
            return chunks
            
        except Exception as e:
            self.logger.error("Embedding generation failed", error=str(e))
            raise


class StoreAgent(Agent):
    """Agent responsible for storing documents in the vector store."""
    
    def __init__(self, vector_store: CareerVectorStore = None):
        super().__init__("StoreAgent")
        self.logger = get_logger(f"{__name__}.StoreAgent")
        self.vector_store = vector_store
    
    def process(self, chunks: List[tuple]) -> Dict[str, Any]:
        """Store chunks in the vector store."""
        self.logger.info("Starting document storage", chunks=len(chunks))
        
        if not self.vector_store:
            raise ValueError("Vector store not initialized")
        
        try:
            # Separate texts and metadata
            texts = [chunk[0] for chunk in chunks]
            metadatas = [chunk[1].dict() for chunk in chunks]
            
            # Store in vector store
            result = self.vector_store.upsert(texts, metadatas)
            
            self.logger.info("Document storage completed", 
                           chunks=len(chunks),
                           result=result)
            
            return result
            
        except Exception as e:
            self.logger.error("Document storage failed", error=str(e))
            raise


class AuditAgent(Agent):
    """Agent responsible for auditing and reporting pipeline results."""
    
    def __init__(self, vector_store: CareerVectorStore = None):
        super().__init__("AuditAgent")
        self.logger = get_logger(f"{__name__}.AuditAgent")
        self.vector_store = vector_store
    
    def process(self, storage_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate audit report for the pipeline run."""
        self.logger.info("Starting pipeline audit")
        
        try:
            # Get collection statistics
            if self.vector_store:
                collection_stats = self.vector_store.get_stats()
            else:
                collection_stats = {"error": "Vector store not available"}
            
            # Compile audit report
            audit_report = {
                "pipeline_run": {
                    "timestamp": time.time(),
                    "storage_result": storage_result,
                    "collection_stats": collection_stats
                },
                "summary": {
                    "documents_added": storage_result.get("added", 0),
                    "documents_skipped": storage_result.get("skipped", 0),
                    "total_processed": storage_result.get("total", 0),
                    "total_in_collection": collection_stats.get("total_chunks", 0)
                }
            }
            
            self.logger.info("Pipeline audit completed", 
                           added=audit_report["summary"]["documents_added"],
                           skipped=audit_report["summary"]["documents_skipped"])
            
            return audit_report
            
        except Exception as e:
            self.logger.error("Pipeline audit failed", error=str(e))
            raise


def create_pipeline() -> Workflow:
    """Create the document processing pipeline workflow."""
    
    # Initialize agents
    ingest_agent = IngestAgent()
    preprocess_agent = PreprocessAgent()
    chunk_agent = ChunkAgent()
    embed_agent = EmbedAgent()
    store_agent = StoreAgent()
    audit_agent = AuditAgent()
    
    # Create workflow
    workflow = Workflow("DocumentProcessingPipeline")
    
    # Define tasks
    ingest_task = Task("ingest", ingest_agent.process)
    preprocess_task = Task("preprocess", preprocess_agent.process)
    chunk_task = Task("chunk", chunk_agent.process)
    embed_task = Task("embed", embed_agent.process)
    store_task = Task("store", store_agent.process)
    audit_task = Task("audit", audit_agent.process)
    
    # Add tasks to workflow
    workflow.add_task(ingest_task)
    workflow.add_task(preprocess_task)
    workflow.add_task(chunk_task)
    workflow.add_task(embed_task)
    workflow.add_task(store_task)
    workflow.add_task(audit_task)
    
    # Define task dependencies
    workflow.add_dependency(preprocess_task, ingest_task)
    workflow.add_dependency(chunk_task, preprocess_task)
    workflow.add_dependency(embed_task, chunk_task)
    workflow.add_dependency(store_task, embed_task)
    workflow.add_dependency(audit_task, store_task)
    
    return workflow


def run_pipeline(input_path: str, 
                embeddings_provider = None,
                vector_store: CareerVectorStore = None) -> Dict[str, Any]:
    """Run the complete document processing pipeline."""
    
    logger.info("Starting document processing pipeline", input_path=input_path)
    
    try:
        # Initialize vector store if not provided
        if vector_store is None:
            if embeddings_provider is None:
                embeddings_provider = get_embeddings_with_fallback()
            vector_store = CareerVectorStore(embeddings_provider=embeddings_provider)
        
        # Create and configure pipeline
        workflow = create_pipeline()
        
        # Configure agents that need external dependencies
        workflow.get_task("store").agent.vector_store = vector_store
        workflow.get_task("audit").agent.vector_store = vector_store
        
        # Run pipeline
        result = workflow.run(input_path)
        
        logger.info("Document processing pipeline completed successfully")
        return result
        
    except Exception as e:
        logger.error("Document processing pipeline failed", error=str(e))
        raise


def verify_query(query: str, 
                k: int = 6,
                embeddings_provider = None,
                vector_store: CareerVectorStore = None) -> List[str]:
    """Verify a query against the vector store."""
    
    logger.info("Verifying query", query=query, k=k)
    
    try:
        # Initialize vector store if not provided
        if vector_store is None:
            if embeddings_provider is None:
                embeddings_provider = get_embeddings_with_fallback()
            vector_store = CareerVectorStore(embeddings_provider=embeddings_provider)
        
        # Search for relevant documents
        results = vector_store.search(query, n_results=k)
        
        # Extract content from results
        content_list = [result["content"] for result in results]
        
        logger.info("Query verification completed", 
                   query=query,
                   results=len(content_list))
        
        return content_list
        
    except Exception as e:
        logger.error("Query verification failed", query=query, error=str(e))
        raise
