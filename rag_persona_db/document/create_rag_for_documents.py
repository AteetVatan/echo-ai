"""CLI interface for creating RAG from documents and personality data."""

import typer
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel

from rag_persona_db.rag_core.settings import settings
from rag_persona_db.rag_core.loaders import DocumentLoader
from rag_persona_db.rag_core.chunking import DocumentChunker
from rag_persona_db.rag_core.embeddings import EmbeddingService
from rag_persona_db.rag_core.store import VectorStore
from rag_persona_db.rag_core.schema import DocumentItem, Metadata, DocumentType, Visibility
from rag_persona_db.rag_core.utils import calculate_content_hash

app = typer.Typer(help="RAG Persona Database - Document Processing CLI")
console = Console()


@app.command()
def process_documents(
    input_path: Path = typer.Argument(..., help="Path to document or directory"),
    doc_type: DocumentType = typer.Option(..., "--type", "-t", help="Document type"),
    source_id: str = typer.Option(..., "--source", "-s", help="Source identifier (e.g., 'cv/master')"),
    version: str = typer.Option("1.0", "--version", "-v", help="Document version"),
    visibility: Visibility = typer.Option("public", "--visibility", help="Document visibility"),
    role_focus: Optional[str] = typer.Option(None, "--role", help="Primary role or focus area"),
    skills: Optional[List[str]] = typer.Option(None, "--skills", help="Comma-separated skills"),
    keywords: Optional[List[str]] = typer.Option(None, "--keywords", help="Comma-separated keywords"),
    language: str = typer.Option("en", "--language", help="Document language code"),
    url: Optional[str] = typer.Option(None, "--url", help="Source URL"),
    chunk_size: Optional[int] = typer.Option(None, "--chunk-size", help="Chunk size in characters"),
    chunk_overlap: Optional[int] = typer.Option(None, "--chunk-overlap", help="Chunk overlap in characters"),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory for processed data"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Process without storing to vector database"),
):
    """Process documents and create RAG embeddings."""
    
    # Override settings if provided
    if chunk_size:
        settings.chunk_size = chunk_size
    if chunk_overlap:
        settings.chunk_overlap = chunk_overlap
    
    # Process skills and keywords
    if skills:
        skills = [s.strip() for s in skills[0].split(",") if s.strip()]
    if keywords:
        keywords = [k.strip() for k in keywords[0].split(",") if k.strip()]
    
    console.print(Panel.fit(
        f"[bold blue]Processing {doc_type.value} documents[/bold blue]\n"
        f"Source: {source_id}\n"
        f"Version: {version}\n"
        f"Visibility: {visibility.value}",
        title="RAG Persona Database"
    ))
    
    try:
        # Initialize services
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("Initializing services...", total=None)
            
            loader = DocumentLoader()
            chunker = DocumentChunker(
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap
            )
            embedding_service = EmbeddingService(
                provider=settings.embeddings_provider,
                model_name=settings.openai_embed_model if settings.embeddings_provider == "openai" else settings.local_embed_model,
                api_key=settings.openai_api_key
            )
            vector_store = VectorStore(
                collection_name=settings.chroma_collection,
                persist_directory=settings.chroma_dir
            )
            
            progress.update(task, description="Loading documents...")
            
            # Load documents
            if input_path.is_file():
                documents = [loader.load_document(input_path)]
            else:
                documents = loader.load_directory(input_path)
            
            if not documents:
                console.print("[red]No documents found to process[/red]")
                raise typer.Exit(1)
            
            progress.update(task, description=f"Processing {len(documents)} documents...")
            
            total_chunks = 0
            processed_docs = []
            
            for doc in documents:
                # Create metadata
                metadata = Metadata(
                    doc_type=doc_type,
                    source_id=source_id,
                    version=version,
                    visibility=visibility,
                    role_focus=role_focus,
                    skills=skills or [],
                    keywords=keywords or [],
                    language=language,
                    url=url,
                    chunk_index=0,  # Will be updated per chunk
                    total_chunks=0,  # Will be calculated
                    content_sha256="",  # Will be calculated
                )
                
                # Create document item
                doc_item = DocumentItem(
                    content=doc.content,
                    metadata=metadata,
                    file_path=str(doc.file_path) if doc.file_path else None,
                    file_size=doc.file_size,
                    file_extension=doc.file_extension
                )
                
                # Chunk document
                chunks = chunker.chunk_document(doc_item)
                total_chunks += len(chunks)
                processed_docs.extend(chunks)
            
            progress.update(task, description=f"Creating embeddings for {total_chunks} chunks...")
            
            if not dry_run:
                # Store in vector database
                vector_store.add_documents(processed_docs, embedding_service)
                console.print(f"[green]✓ Successfully stored {total_chunks} chunks in vector database[/green]")
            else:
                console.print(f"[yellow]✓ Dry run completed - {total_chunks} chunks would be stored[/yellow]")
            
            # Display summary
            display_summary(processed_docs, doc_type, source_id, dry_run)
            
            if output_dir and not dry_run:
                save_processed_data(processed_docs, output_dir)
                
    except Exception as e:
        console.print(f"[red]Error processing documents: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def list_collections():
    """List available vector database collections."""
    try:
        vector_store = VectorStore(
            collection_name=settings.chroma_collection,
            persist_directory=settings.chroma_dir
        )
        
        collections = vector_store.list_collections()
        
        if not collections:
            console.print("[yellow]No collections found[/yellow]")
            return
        
        table = Table(title="Available Collections")
        table.add_column("Collection Name", style="cyan")
        table.add_column("Document Count", style="green")
        table.add_column("Embedding Dimension", style="blue")
        
        for collection in collections:
            table.add_row(
                collection.name,
                str(collection.count()),
                str(collection.metadata.get("embedding_dimension", "Unknown"))
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error listing collections: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    collection: str = typer.Option(None, "--collection", "-c", help="Collection name"),
    limit: int = typer.Option(5, "--limit", "-l", help="Number of results to return"),
    similarity_threshold: float = typer.Option(0.7, "--threshold", "-t", help="Similarity threshold"),
):
    """Search for similar documents in the vector database."""
    try:
        vector_store = VectorStore(
            collection_name=collection or settings.chroma_collection,
            persist_directory=settings.chroma_dir
        )
        
        embedding_service = EmbeddingService(
            provider=settings.embeddings_provider,
            model_name=settings.openai_embed_model if settings.embeddings_provider == "openai" else settings.local_embed_model,
            api_key=settings.openai_api_key
        )
        
        results = vector_store.search(query, embedding_service, limit=limit, threshold=similarity_threshold)
        
        if not results:
            console.print("[yellow]No results found[/yellow]")
            return
        
        console.print(f"[bold blue]Search Results for: {query}[/bold blue]")
        
        for i, result in enumerate(results, 1):
            console.print(f"\n[bold cyan]{i}.[/bold cyan] [bold]{result.metadata.doc_type.value}[/bold]")
            console.print(f"   Source: {result.metadata.source_id}")
            console.print(f"   Similarity: {result.similarity:.3f}")
            console.print(f"   Content: {result.content[:200]}...")
            
    except Exception as e:
        console.print(f"[red]Error searching: {str(e)}[/red]")
        raise typer.Exit(1)


def display_summary(documents: List[DocumentItem], doc_type: DocumentType, source_id: str, dry_run: bool):
    """Display processing summary."""
    table = Table(title="Processing Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Document Type", doc_type.value)
    table.add_row("Source ID", source_id)
    table.add_row("Total Chunks", str(len(documents)))
    table.add_row("Mode", "Dry Run" if dry_run else "Production")
    
    # Group by document type
    doc_types = {}
    for doc in documents:
        doc_type_str = doc.metadata.doc_type.value
        doc_types[doc_type_str] = doc_types.get(doc_type_str, 0) + 1
    
    for doc_type_str, count in doc_types.items():
        table.add_row(f"{doc_type_str.title()} Chunks", str(count))
    
    console.print(table)


def save_processed_data(documents: List[DocumentItem], output_dir: Path):
    """Save processed data to output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save metadata summary
    metadata_file = output_dir / "metadata_summary.json"
    import json
    from datetime import datetime
    
    summary = {
        "processed_at": datetime.utcnow().isoformat(),
        "total_documents": len(documents),
        "document_types": {},
        "sources": {},
        "skills": set(),
        "keywords": set()
    }
    
    for doc in documents:
        # Count document types
        doc_type = doc.metadata.doc_type.value
        summary["document_types"][doc_type] = summary["document_types"].get(doc_type, 0) + 1
        
        # Count sources
        source = doc.metadata.source_id
        summary["sources"][source] = summary["sources"].get(source, 0) + 1
        
        # Collect skills and keywords
        summary["skills"].update(doc.metadata.skills)
        summary["keywords"].update(doc.metadata.keywords)
    
    # Convert sets to lists for JSON serialization
    summary["skills"] = list(summary["skills"])
    summary["keywords"] = list(summary["keywords"])
    
    with open(metadata_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    console.print(f"[green]✓ Metadata summary saved to {metadata_file}[/green]")


if __name__ == "__main__":
    app()
