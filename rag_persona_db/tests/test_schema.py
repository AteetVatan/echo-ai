"""Tests for RAG Persona Database schema models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from rag_persona_db.rag_core.schema import (
    DocumentType,
    Visibility,
    Metadata,
    DocumentItem,
    validate_personality
)


class TestDocumentType:
    """Test DocumentType enum."""
    
    def test_document_types(self):
        """Test all document types are accessible."""
        assert DocumentType.CV == "cv"
        assert DocumentType.PROJECT == "project"
        assert DocumentType.BLOG == "blog"
        assert DocumentType.PORTFOLIO == "portfolio"
        assert DocumentType.TESTIMONIAL == "testimonial"
        assert DocumentType.BIO == "bio"
        assert DocumentType.PERSONALITY == "personality"


class TestVisibility:
    """Test Visibility enum."""
    
    def test_visibility_values(self):
        """Test visibility values."""
        assert Visibility.PUBLIC == "public"
        assert Visibility.PRIVATE == "private"


class TestMetadata:
    """Test Metadata model."""
    
    def test_valid_metadata(self):
        """Test creating valid metadata."""
        metadata = Metadata(
            doc_type=DocumentType.CV,
            source_id="cv/master",
            version="1.0",
            visibility=Visibility.PUBLIC,
            role_focus="Software Engineer",
            skills=["Python", "JavaScript"],
            keywords=["web development", "backend"],
            language="en",
            url="https://example.com/cv",
            chunk_index=0,
            total_chunks=5,
            content_sha256="abc123"
        )
        
        assert metadata.doc_type == DocumentType.CV
        assert metadata.source_id == "cv/master"
        assert metadata.version == "1.0"
        assert metadata.visibility == Visibility.PUBLIC
        assert metadata.role_focus == "Software Engineer"
        assert metadata.skills == ["Python", "JavaScript"]
        assert metadata.keywords == ["web development", "backend"]
        assert metadata.language == "en"
        assert metadata.url == "https://example.com/cv"
        assert metadata.chunk_index == 0
        assert metadata.total_chunks == 5
        assert metadata.content_sha256 == "abc123"
        assert isinstance(metadata.created_at, datetime)
        assert isinstance(metadata.updated_at, datetime)
    
    def test_invalid_source_id(self):
        """Test validation of source_id format."""
        with pytest.raises(ValidationError, match="source_id must contain '/' separator"):
            Metadata(
                doc_type=DocumentType.CV,
                source_id="invalid_id",
                version="1.0",
                chunk_index=0,
                total_chunks=1,
                content_sha256="abc123"
            )
    
    def test_personality_tags_validation(self):
        """Test personality tags are only allowed for personality documents."""
        # Should work for personality documents
        metadata = Metadata(
            doc_type=DocumentType.PERSONALITY,
            source_id="personality/test",
            version="1.0",
            chunk_index=0,
            total_chunks=1,
            content_sha256="abc123",
            personality_tags=["introvert", "analytical"]
        )
        assert metadata.personality_tags == ["introvert", "analytical"]
        
        # Should clear personality tags for non-personality documents
        metadata = Metadata(
            doc_type=DocumentType.CV,
            source_id="cv/test",
            version="1.0",
            chunk_index=0,
            total_chunks=1,
            content_sha256="abc123",
            personality_tags=["introvert", "analytical"]
        )
        assert metadata.personality_tags == []
    
    def test_default_values(self):
        """Test default values are set correctly."""
        metadata = Metadata(
            doc_type=DocumentType.CV,
            source_id="cv/test",
            version="1.0",
            chunk_index=0,
            total_chunks=1,
            content_sha256="abc123"
        )
        
        assert metadata.visibility == Visibility.PUBLIC
        assert metadata.role_focus is None
        assert metadata.skills == []
        assert metadata.keywords == []
        assert metadata.language == "en"
        assert metadata.url is None
        assert metadata.personality_tags == []
    
    def test_chunk_overlap_validation(self):
        """Test chunk overlap validation."""
        with pytest.raises(ValidationError, match="chunk_overlap must be less than chunk_size"):
            Metadata(
                doc_type=DocumentType.CV,
                source_id="cv/test",
                version="1.0",
                chunk_index=0,
                total_chunks=1,
                content_sha256="abc123",
                chunk_size=100,
                chunk_overlap=150
            )


class TestDocumentItem:
    """Test DocumentItem model."""
    
    def test_valid_document_item(self):
        """Test creating valid document item."""
        metadata = Metadata(
            doc_type=DocumentType.CV,
            source_id="cv/master",
            version="1.0",
            chunk_index=0,
            total_chunks=1,
            content_sha256="abc123"
        )
        
        doc_item = DocumentItem(
            content="This is a sample CV content.",
            metadata=metadata,
            file_path="/path/to/cv.txt",
            file_size=1024,
            file_extension=".txt"
        )
        
        assert doc_item.content == "This is a sample CV content."
        assert doc_item.metadata == metadata
        assert doc_item.file_path == "/path/to/cv.txt"
        assert doc_item.file_size == 1024
        assert doc_item.file_extension == ".txt"
    
    def test_content_validation(self):
        """Test content validation."""
        metadata = Metadata(
            doc_type=DocumentType.CV,
            source_id="cv/test",
            version="1.0",
            chunk_index=0,
            total_chunks=1,
            content_sha256="abc123"
        )
        
        # Empty content should fail
        with pytest.raises(ValidationError, match="Content cannot be empty"):
            DocumentItem(
                content="",
                metadata=metadata
            )
        
        # Whitespace-only content should fail
        with pytest.raises(ValidationError, match="Content cannot be empty"):
            DocumentItem(
                content="   \n\t   ",
                metadata=metadata
            )
        
        # Content with whitespace should be trimmed
        doc_item = DocumentItem(
            content="  trimmed content  ",
            metadata=metadata
        )
        assert doc_item.content == "trimmed content"
    
    def test_to_chunk_metadata(self):
        """Test creating chunk metadata from document item."""
        metadata = Metadata(
            doc_type=DocumentType.CV,
            source_id="cv/master",
            version="1.0",
            chunk_index=0,
            total_chunks=1,
            content_sha256="abc123"
        )
        
        doc_item = DocumentItem(
            content="Sample content",
            metadata=metadata
        )
        
        chunk_metadata = doc_item.to_chunk_metadata(
            chunk_index=2,
            total_chunks=5,
            content_sha256="def456"
        )
        
        assert chunk_metadata.chunk_index == 2
        assert chunk_metadata.total_chunks == 5
        assert chunk_metadata.content_sha256 == "def456"
        assert chunk_metadata.updated_at > metadata.updated_at


class TestValidatePersonality:
    """Test personality validation function."""
    
    def test_big_five_personality(self):
        """Test Big Five personality framework extraction."""
        data = {
            "big_five": {
                "openness": 0.8,
                "conscientiousness": 0.3,
                "extraversion": 0.7,
                "agreeableness": 0.2,
                "neuroticism": 0.9
            }
        }
        
        tags = validate_personality(data)
        expected_tags = ["high_openness", "high_extraversion", "low_conscientiousness", 
                        "low_agreeableness", "high_neuroticism"]
        
        assert set(tags) == set(expected_tags)
    
    def test_mbti_personality(self):
        """Test MBTI personality extraction."""
        data = {"mbti": "INTJ"}
        tags = validate_personality(data)
        assert "INTJ" in tags
    
    def test_custom_traits(self):
        """Test custom traits extraction."""
        data = {
            "traits": ["creative", "analytical", "introverted"],
            "work_style": ["collaborative", "independent"]
        }
        
        tags = validate_personality(data)
        expected_tags = ["creative", "analytical", "introverted", "collaborative", "independent"]
        
        assert set(tags) == set(expected_tags)
    
    def test_mixed_personality_data(self):
        """Test mixed personality data extraction."""
        data = {
            "big_five": {"openness": 0.9, "conscientiousness": 0.2},
            "mbti": "ENFP",
            "traits": ["empathetic", "energetic"],
            "work_style": ["team_oriented", "creative_problem_solving"]
        }
        
        tags = validate_personality(data)
        expected_tags = ["high_openness", "low_conscientiousness", "ENFP", 
                        "empathetic", "energetic", "team_oriented", "creative_problem_solving"]
        
        assert set(tags) == set(expected_tags)
    
    def test_empty_personality_data(self):
        """Test empty personality data."""
        tags = validate_personality({})
        assert tags == []
        
        tags = validate_personality(None)
        assert tags == []
    
    def test_invalid_personality_data(self):
        """Test invalid personality data handling."""
        data = {
            "big_five": "invalid_string",
            "mbti": 123,
            "traits": "not_a_list"
        }
        
        tags = validate_personality(data)
        assert tags == []
    
    def test_duplicate_removal(self):
        """Test duplicate personality tags are removed."""
        data = {
            "traits": ["creative", "creative", "analytical"],
            "work_style": ["creative", "analytical", "analytical"]
        }
        
        tags = validate_personality(data)
        assert len(tags) == 2
        assert set(tags) == {"creative", "analytical"}


class TestSchemaIntegration:
    """Test schema components work together."""
    
    def test_full_document_workflow(self):
        """Test complete document workflow from metadata to chunk."""
        # Create base metadata
        metadata = Metadata(
            doc_type=DocumentType.PORTFOLIO,
            source_id="portfolio/2024",
            version="2.0",
            visibility=Visibility.PUBLIC,
            role_focus="Senior Developer",
            skills=["Python", "React", "AWS"],
            keywords=["web development", "cloud computing"],
            chunk_index=0,
            total_chunks=1,
            content_sha256="abc123"
        )
        
        # Create document item
        doc_item = DocumentItem(
            content="Portfolio content here",
            metadata=metadata,
            file_path="/path/to/portfolio.md",
            file_size=2048,
            file_extension=".md"
        )
        
        # Create chunk metadata
        chunk_metadata = doc_item.to_chunk_metadata(
            chunk_index=1,
            total_chunks=3,
            content_sha256="def456"
        )
        
        # Verify relationships
        assert chunk_metadata.doc_type == DocumentType.PORTFOLIO
        assert chunk_metadata.source_id == "portfolio/2024"
        assert chunk_metadata.version == "2.0"
        assert chunk_metadata.role_focus == "Senior Developer"
        assert chunk_metadata.chunk_index == 1
        assert chunk_metadata.total_chunks == 3
        assert chunk_metadata.content_sha256 == "def456"
