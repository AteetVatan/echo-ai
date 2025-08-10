"""Utility functions for RAG Persona Database."""

import hashlib
import time
from typing import Any, Dict, List
from pathlib import Path
from contextlib import contextmanager

from .logging_config import get_logger

logger = get_logger(__name__)


def sha256_hash(text: str) -> str:
    """Generate SHA256 hash of text content."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def generate_document_id(source_id: str, version: str, chunk_index: int) -> str:
    """Generate a unique document ID."""
    return f"{source_id}_{version}_{chunk_index}"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage."""
    import re
    # Remove or replace unsafe characters
    safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Limit length
    if len(safe_filename) > 255:
        safe_filename = safe_filename[:255]
    return safe_filename


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"


def extract_text_summary(text: str, max_length: int = 200) -> str:
    """Extract a summary of text content."""
    if not text:
        return ""
    
    # Clean up text
    cleaned = ' '.join(text.split())
    
    if len(cleaned) <= max_length:
        return cleaned
    
    # Try to break at sentence boundary
    sentences = cleaned.split('.')
    summary = ""
    
    for sentence in sentences:
        if len(summary + sentence + '.') <= max_length:
            summary += sentence + '.'
        else:
            break
    
    if not summary:
        # If no sentence fits, just truncate
        summary = cleaned[:max_length-3] + "..."
    
    return summary


@contextmanager
def timer(operation_name: str):
    """Context manager for timing operations."""
    start_time = time.time()
    logger.info(f"Starting {operation_name}")
    
    try:
        yield
    finally:
        elapsed_time = time.time() - start_time
        logger.info(f"Completed {operation_name} in {elapsed_time:.2f}s")


def validate_file_path(file_path: str) -> bool:
    """Validate if a file path exists and is accessible."""
    path = Path(file_path)
    return path.exists() and path.is_file() and path.stat().st_size > 0


def get_supported_extensions() -> List[str]:
    """Get list of supported file extensions."""
    return ['.pdf', '.docx', '.md', '.txt', '.html', '.htm', '.json']


def is_supported_file(file_path: str) -> bool:
    """Check if file is supported based on extension."""
    extension = Path(file_path).suffix.lower()
    return extension in get_supported_extensions()


def create_sample_files(directory: str) -> Dict[str, str]:
    """Create sample files for testing."""
    sample_dir = Path(directory)
    sample_dir.mkdir(parents=True, exist_ok=True)
    
    samples = {}
    
    # Sample CV (Markdown)
    cv_content = """# John Doe - Senior Software Engineer

## Experience
- **Senior Software Engineer** at TechCorp (2020-Present)
  - Led development of microservices architecture
  - Implemented CI/CD pipelines using Jenkins and Docker
  - Mentored junior developers and conducted code reviews

## Skills
- Python, JavaScript, Go
- AWS, Docker, Kubernetes
- Microservices, REST APIs, GraphQL

## Education
- BS Computer Science, University of Technology (2016)
"""
    
    cv_path = sample_dir / "cv_master_2025.md"
    cv_path.write_text(cv_content, encoding='utf-8')
    samples["cv"] = str(cv_path)
    
    # Sample blog post
    blog_content = """# Building Scalable Microservices

This post explores the challenges and solutions for building scalable microservices architectures.

## Key Points
- Service decomposition strategies
- API gateway patterns
- Circuit breaker implementation
- Monitoring and observability

## Conclusion
Microservices require careful planning but offer significant benefits for large-scale applications.
"""
    
    blog_path = sample_dir / "blog_microservices.md"
    blog_path.write_text(blog_content, encoding='utf-8')
    samples["blog"] = str(blog_path)
    
    # Sample personality questionnaire
    personality_data = {
        "name": "John Doe",
        "description": "Software engineer with analytical mindset",
        "big_five": {
            "openness": 0.8,
            "conscientiousness": 0.9,
            "extraversion": 0.4,
            "agreeableness": 0.7,
            "neuroticism": 0.3
        },
        "mbti": "INTJ",
        "work_style": ["analytical", "systematic", "independent"],
        "traits": ["detail-oriented", "problem-solver", "continuous-learner"]
    }
    
    import json
    personality_path = sample_dir / "personality_questionnaire.json"
    personality_path.write_text(json.dumps(personality_data, indent=2), encoding='utf-8')
    samples["personality"] = str(personality_path)
    
    # Sample notes
    notes_content = """Project Notes - AI Integration

- Research OpenAI API integration
- Evaluate embedding models
- Plan vector database schema
- Consider privacy implications

Next steps:
1. Set up development environment
2. Create proof of concept
3. Test with sample data
"""
    
    notes_path = sample_dir / "project_notes.txt"
    notes_path.write_text(notes_content, encoding='utf-8')
    samples["notes"] = str(notes_path)
    
    logger.info("Sample files created", directory=str(sample_dir), files=list(samples.keys()))
    return samples


def cleanup_sample_files(directory: str):
    """Clean up sample files."""
    sample_dir = Path(directory)
    if sample_dir.exists():
        for file_path in sample_dir.glob("*"):
            if file_path.is_file():
                file_path.unlink()
        sample_dir.rmdir()
        logger.info("Sample files cleaned up", directory=str(directory))
