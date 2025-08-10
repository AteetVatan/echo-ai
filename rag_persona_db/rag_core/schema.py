"""Pydantic models for document items and metadata."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class DocumentType(str, Enum):
    """Supported document types."""
    CV = "cv"
    PROJECT = "project"
    BLOG = "blog"
    PORTFOLIO = "portfolio"
    TESTIMONIAL = "testimonial"
    BIO = "bio"
    PERSONALITY = "personality"


class Visibility(str, Enum):
    """Document visibility levels."""
    PUBLIC = "public"
    PRIVATE = "private"


class Metadata(BaseModel):
    """Metadata for document chunks."""
    
    # Core identification
    doc_type: DocumentType
    source_id: str = Field(..., description="Stable logical identifier for the source")
    version: str = Field(..., description="Date or semantic version")
    visibility: Visibility = Field(default="public")
    
    # Content classification
    role_focus: Optional[str] = Field(None, description="Primary role or focus area")
    skills: List[str] = Field(default_factory=list, description="Skills mentioned")
    keywords: List[str] = Field(default_factory=list, description="Key terms and concepts")
    language: str = Field(default="en", description="Document language code")
    url: Optional[str] = Field(None, description="Source URL if applicable")
    
    # Personality-specific fields
    personality_tags: List[str] = Field(default_factory=list, description="Personality traits")
    
    # Processing metadata
    chunk_index: int = Field(..., description="Index of this chunk within the document")
    total_chunks: int = Field(..., description="Total number of chunks in the document")
    content_sha256: str = Field(..., description="SHA256 hash of chunk content")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator("personality_tags")
    def validate_personality_tags(cls, v, values):
        """Validate personality tags are only present for personality documents."""
        if values.get("doc_type") != DocumentType.PERSONALITY and v:
            return []
        return v
    
    @validator("source_id")
    def validate_source_id(cls, v):
        """Ensure source_id follows naming convention."""
        if "/" not in v:
            raise ValueError("source_id must contain '/' separator (e.g., 'cv/master')")
        return v


class DocumentItem(BaseModel):
    """Complete document item with content and metadata."""
    
    # Content
    content: str = Field(..., description="Document content text")
    
    # Metadata
    metadata: Metadata
    
    # File information
    file_path: Optional[str] = Field(None, description="Original file path")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    file_extension: Optional[str] = Field(None, description="File extension")
    
    @validator("content")
    def validate_content(cls, v):
        """Ensure content is not empty."""
        if not v or not v.strip():
            raise ValueError("Content cannot be empty")
        return v.strip()
    
    def to_chunk_metadata(self, chunk_index: int, total_chunks: int, content_sha256: str) -> Metadata:
        """Create metadata for a specific chunk."""
        metadata_dict = self.metadata.dict()
        metadata_dict.update({
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "content_sha256": content_sha256,
            "updated_at": datetime.utcnow(),
        })
        return Metadata(**metadata_dict)


def validate_personality(data: Dict[str, Any]) -> List[str]:
    """Normalize personality questionnaire data to personality tags."""
    personality_tags = []
    
    # Extract personality traits from questionnaire
    if isinstance(data, dict):
        # Common personality frameworks
        if "big_five" in data:
            big_five = data["big_five"]
            for trait, score in big_five.items():
                if isinstance(score, (int, float)) and score > 0.6:
                    personality_tags.append(f"high_{trait}")
                elif isinstance(score, (int, float)) and score < 0.4:
                    personality_tags.append(f"low_{trait}")
        
        # Myers-Briggs
        if "mbti" in data:
            personality_tags.append(data["mbti"])
        
        # Custom traits
        if "traits" in data and isinstance(data["traits"], list):
            personality_tags.extend(data["traits"])
        
        # Work style preferences
        if "work_style" in data:
            personality_tags.extend(data["work_style"])
    
    return list(set(personality_tags))  # Remove duplicates
