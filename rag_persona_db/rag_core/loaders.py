"""Document loaders for various file formats."""

import os
import json
import hashlib
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

import pypdf
import docx2txt
import trafilatura
from readability import Document as ReadabilityDocument

from .schema import DocumentItem, Metadata, DocumentType, Visibility
from .logging_config import get_logger
from .settings import settings

logger = get_logger(__name__)


def sha256_hash(text: str) -> str:
    """Generate SHA256 hash of text content."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def extract_metadata_from_filename(file_path: str) -> Dict[str, Any]:
    """Extract metadata from filename and path."""
    path = Path(file_path)
    filename = path.stem
    extension = path.suffix.lower()
    
    # Default metadata based on file type
    metadata = {
        "file_extension": extension,
        "file_size": path.stat().st_size if path.exists() else None,
        "file_path": str(file_path),
    }
    
    # Try to infer document type from filename
    filename_lower = filename.lower()
    if any(word in filename_lower for word in ["cv", "resume", "curriculum"]):
        metadata["doc_type"] = DocumentType.CV
        metadata["source_id"] = "cv/master"
    elif any(word in filename_lower for word in ["blog", "post", "article"]):
        metadata["doc_type"] = DocumentType.BLOG
        metadata["source_id"] = f"blog/{filename}"
    elif any(word in filename_lower for word in ["project", "portfolio"]):
        metadata["doc_type"] = DocumentType.PROJECT
        metadata["source_id"] = f"project/{filename}"
    elif any(word in filename_lower for word in ["personality", "questionnaire"]):
        metadata["doc_type"] = DocumentType.PERSONALITY
        metadata["source_id"] = f"personality/{filename}"
    else:
        metadata["doc_type"] = DocumentType.BIO
        metadata["source_id"] = f"bio/{filename}"
    
    # Set version to current date
    metadata["version"] = datetime.now().strftime("%Y-%m-%d")
    metadata["visibility"] = settings.default_visibility
    metadata["language"] = "en"
    
    return metadata


def load_pdf(file_path: str) -> List[DocumentItem]:
    """Load PDF documents and extract text."""
    try:
        logger.info("Loading PDF file", file_path=file_path)
        
        with open(file_path, 'rb') as file:
            pdf_reader = pypdf.PdfReader(file)
            
        documents = []
        metadata = extract_metadata_from_filename(file_path)
        
        for page_num, page in enumerate(pdf_reader.pages):
            text = page.extract_text()
            if text.strip():
                # Create document item for each page
                doc_metadata = Metadata(
                    doc_type=metadata["doc_type"],
                    source_id=metadata["source_id"],
                    version=metadata["version"],
                    visibility=metadata["visibility"],
                    language=metadata["language"],
                    chunk_index=page_num,
                    total_chunks=len(pdf_reader.pages),
                    content_sha256=sha256_hash(text),
                    file_path=metadata["file_path"],
                    file_size=metadata["file_size"],
                    file_extension=metadata["file_extension"],
                )
                
                documents.append(DocumentItem(
                    content=text,
                    metadata=doc_metadata
                ))
        
        logger.info("PDF loaded successfully", 
                   file_path=file_path, 
                   pages=len(pdf_reader.pages),
                   documents=len(documents))
        
        return documents
        
    except Exception as e:
        logger.error("Failed to load PDF", file_path=file_path, error=str(e))
        raise


def load_docx(file_path: str) -> List[DocumentItem]:
    """Load DOCX documents and extract text."""
    try:
        logger.info("Loading DOCX file", file_path=file_path)
        
        text = docx2txt.process(file_path)
        if not text.strip():
            logger.warning("DOCX file contains no text", file_path=file_path)
            return []
        
        metadata = extract_metadata_from_filename(file_path)
        
        # Create single document item for the entire document
        doc_metadata = Metadata(
            doc_type=metadata["doc_type"],
            source_id=metadata["source_id"],
            version=metadata["version"],
            visibility=metadata["visibility"],
            language=metadata["language"],
            chunk_index=0,
            total_chunks=1,
            content_sha256=sha256_hash(text),
            file_path=metadata["file_path"],
            file_size=metadata["file_size"],
            file_extension=metadata["file_extension"],
        )
        
        document = DocumentItem(
            content=text,
            metadata=doc_metadata
        )
        
        logger.info("DOCX loaded successfully", 
                   file_path=file_path, 
                   documents=1)
        
        return [document]
        
    except Exception as e:
        logger.error("Failed to load DOCX", file_path=file_path, error=str(e))
        raise


def load_md(file_path: str) -> List[DocumentItem]:
    """Load Markdown documents and extract text."""
    try:
        logger.info("Loading Markdown file", file_path=file_path)
        
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        if not content.strip():
            logger.warning("Markdown file contains no text", file_path=file_path)
            return []
        
        # Extract front matter if present
        front_matter = {}
        if content.startswith('---'):
            try:
                end_marker = content.find('---', 3)
                if end_marker != -1:
                    front_matter_text = content[3:end_marker].strip()
                    front_matter = yaml.safe_load(front_matter_text) or {}
                    content = content[end_marker + 3:].strip()
            except Exception:
                logger.warning("Failed to parse front matter", file_path=file_path)
        
        metadata = extract_metadata_from_filename(file_path)
        
        # Override with front matter if available
        if front_matter:
            if 'title' in front_matter:
                metadata["source_id"] = f"{metadata['doc_type']}/{front_matter['title']}"
            if 'date' in front_matter:
                metadata["version"] = front_matter['date']
            if 'tags' in front_matter:
                metadata["keywords"] = front_matter['tags']
        
        doc_metadata = Metadata(
            doc_type=metadata["doc_type"],
            source_id=metadata["source_id"],
            version=metadata["version"],
            visibility=metadata["visibility"],
            language=metadata["language"],
            keywords=metadata.get("keywords", []),
            chunk_index=0,
            total_chunks=1,
            content_sha256=sha256_hash(content),
            file_path=metadata["file_path"],
            file_size=metadata["file_size"],
            file_extension=metadata["file_extension"],
        )
        
        document = DocumentItem(
            content=content,
            metadata=doc_metadata
        )
        
        logger.info("Markdown loaded successfully", 
                   file_path=file_path, 
                   documents=1)
        
        return [document]
        
    except Exception as e:
        logger.error("Failed to load Markdown", file_path=file_path, error=str(e))
        raise


def load_txt(file_path: str) -> List[DocumentItem]:
    """Load plain text documents."""
    try:
        logger.info("Loading text file", file_path=file_path)
        
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        if not content.strip():
            logger.warning("Text file contains no content", file_path=file_path)
            return []
        
        metadata = extract_metadata_from_filename(file_path)
        
        doc_metadata = Metadata(
            doc_type=metadata["doc_type"],
            source_id=metadata["source_id"],
            version=metadata["version"],
            visibility=metadata["visibility"],
            language=metadata["language"],
            chunk_index=0,
            total_chunks=1,
            content_sha256=sha256_hash(content),
            file_path=metadata["file_path"],
            file_size=metadata["file_size"],
            file_extension=metadata["file_extension"],
        )
        
        document = DocumentItem(
            content=content,
            metadata=doc_metadata
        )
        
        logger.info("Text file loaded successfully", 
                   file_path=file_path, 
                   documents=1)
        
        return [document]
        
    except Exception as e:
        logger.error("Failed to load text file", file_path=file_path, error=str(e))
        raise


def load_html(file_path: str) -> List[DocumentItem]:
    """Load HTML documents and extract text."""
    try:
        logger.info("Loading HTML file", file_path=file_path)
        
        with open(file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
        
        # Try trafilatura first (better for article extraction)
        try:
            text = trafilatura.extract(html_content, include_comments=False, include_tables=False)
            if not text or not text.strip():
                raise ValueError("Trafilatura extraction failed")
        except Exception:
            logger.info("Trafilatura failed, trying readability", file_path=file_path)
            # Fallback to readability-lxml
            doc = ReadabilityDocument(html_content)
            text = doc.summary()
            # Clean up HTML tags
            import re
            text = re.sub(r'<[^>]+>', '', text)
        
        if not text.strip():
            logger.warning("HTML file contains no extractable text", file_path=file_path)
            return []
        
        metadata = extract_metadata_from_filename(file_path)
        
        doc_metadata = Metadata(
            doc_type=metadata["doc_type"],
            source_id=metadata["source_id"],
            version=metadata["version"],
            visibility=metadata["visibility"],
            language=metadata["language"],
            chunk_index=0,
            total_chunks=1,
            content_sha256=sha256_hash(text),
            file_path=metadata["file_path"],
            file_size=metadata["file_size"],
            file_extension=metadata["file_extension"],
        )
        
        document = DocumentItem(
            content=text,
            metadata=doc_metadata
        )
        
        logger.info("HTML loaded successfully", 
                   file_path=file_path, 
                   documents=1)
        
        return [document]
        
    except Exception as e:
        logger.error("Failed to load HTML", file_path=file_path, error=str(e))
        raise


def load_personality_json(file_path: str) -> List[DocumentItem]:
    """Load personality questionnaire JSON files."""
    try:
        logger.info("Loading personality JSON file", file_path=file_path)
        
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        if not isinstance(data, dict):
            raise ValueError("JSON must contain an object")
        
        # Extract personality traits
        from .schema import validate_personality
        personality_tags = validate_personality(data)
        
        # Convert to text representation
        content_lines = []
        if "name" in data:
            content_lines.append(f"Name: {data['name']}")
        if "description" in data:
            content_lines.append(f"Description: {data['description']}")
        
        # Add personality traits
        if personality_tags:
            content_lines.append(f"Personality Traits: {', '.join(personality_tags)}")
        
        # Add other relevant fields
        for key, value in data.items():
            if key not in ["name", "description"] and isinstance(value, (str, int, float)):
                content_lines.append(f"{key.title()}: {value}")
        
        content = "\n".join(content_lines)
        
        metadata = extract_metadata_from_filename(file_path)
        metadata["doc_type"] = DocumentType.PERSONALITY
        metadata["personality_tags"] = personality_tags
        
        doc_metadata = Metadata(
            doc_type=metadata["doc_type"],
            source_id=metadata["source_id"],
            version=metadata["version"],
            visibility=metadata["visibility"],
            language=metadata["language"],
            personality_tags=metadata["personality_tags"],
            chunk_index=0,
            total_chunks=1,
            content_sha256=sha256_hash(content),
            file_path=metadata["file_path"],
            file_size=metadata["file_size"],
            file_extension=metadata["file_extension"],
        )
        
        document = DocumentItem(
            content=content,
            metadata=doc_metadata
        )
        
        logger.info("Personality JSON loaded successfully", 
                   file_path=file_path, 
                   documents=1,
                   traits=len(personality_tags))
        
        return [document]
        
    except Exception as e:
        logger.error("Failed to load personality JSON", file_path=file_path, error=str(e))
        raise


def load_document(file_path: str) -> List[DocumentItem]:
    """Load document based on file extension."""
    file_path = str(file_path)
    extension = Path(file_path).suffix.lower()
    
    loaders = {
        '.pdf': load_pdf,
        '.docx': load_docx,
        '.md': load_md,
        '.txt': load_txt,
        '.html': load_html,
        '.htm': load_html,
        '.json': load_personality_json,
    }
    
    if extension not in loaders:
        raise ValueError(f"Unsupported file extension: {extension}")
    
    return loaders[extension](file_path)


def load_documents_from_directory(directory_path: str) -> List[DocumentItem]:
    """Load all supported documents from a directory."""
    directory = Path(directory_path)
    if not directory.exists() or not directory.is_dir():
        raise ValueError(f"Directory does not exist: {directory_path}")
    
    supported_extensions = {'.pdf', '.docx', '.md', '.txt', '.html', '.htm', '.json'}
    all_documents = []
    
    for file_path in directory.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
            try:
                documents = load_document(str(file_path))
                all_documents.extend(documents)
            except Exception as e:
                logger.error("Failed to load document", 
                           file_path=str(file_path), 
                           error=str(e))
                continue
    
    logger.info("Directory loading completed", 
               directory=directory_path, 
               total_documents=len(all_documents))
    
    return all_documents
