"""Tests for RAG Persona Database CLI interface."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typer.testing import CliRunner

from rag_persona_db.document.create_rag_for_documents import app


class TestCLIInterface:
    """Test CLI interface functionality."""
    
    @pytest.fixture
    def runner(self):
        """Create CLI runner for testing."""
        return CliRunner()
    
    @pytest.fixture
    def mock_services(self):
        """Mock all service dependencies."""
        with patch('rag_persona_db.document.create_rag_for_documents.DocumentLoader') as mock_loader, \
             patch('rag_persona_db.document.create_rag_for_documents.DocumentChunker') as mock_chunker, \
             patch('rag_persona_db.document.create_rag_for_documents.EmbeddingService') as mock_embedding, \
             patch('rag_persona_db.document.create_rag_for_documents.VectorStore') as mock_store:
            
            # Mock loader
            mock_loader_instance = Mock()
            mock_loader_instance.load_document.return_value = Mock(
                content="Sample document content",
                file_path=Path("/test/doc.txt"),
                file_size=1024,
                file_extension=".txt"
            )
            mock_loader_instance.load_directory.return_value = [
                Mock(
                    content="Sample document content",
                    file_path=Path("/test/doc.txt"),
                    file_size=1024,
                    file_extension=".txt"
                )
            ]
            mock_loader.return_value = mock_loader_instance
            
            # Mock chunker
            mock_chunker_instance = Mock()
            mock_chunker_instance.chunk_document.return_value = [
                Mock(
                    content="Chunk 1",
                    metadata=Mock(
                        doc_type="cv",
                        source_id="cv/test",
                        version="1.0",
                        chunk_index=0,
                        total_chunks=2,
                        content_sha256="abc123"
                    )
                ),
                Mock(
                    content="Chunk 2",
                    metadata=Mock(
                        doc_type="cv",
                        source_id="cv/test",
                        version="1.0",
                        chunk_index=1,
                        total_chunks=2,
                        content_sha256="def456"
                    )
                )
            ]
            mock_chunker.return_value = mock_chunker_instance
            
            # Mock embedding service
            mock_embedding_instance = Mock()
            mock_embedding.return_value = mock_embedding_instance
            
            # Mock vector store
            mock_store_instance = Mock()
            mock_store_instance.add_documents.return_value = None
            mock_store.return_value = mock_store_instance
            
            yield {
                'loader': mock_loader,
                'chunker': mock_chunker,
                'embedding': mock_embedding,
                'store': mock_store,
                'loader_instance': mock_loader_instance,
                'chunker_instance': mock_chunker_instance,
                'embedding_instance': mock_embedding_instance,
                'store_instance': mock_store_instance
            }
    
    def test_process_documents_single_file(self, runner, mock_services):
        """Test processing a single document file."""
        with patch('rag_persona_db.document.create_rag_for_documents.settings') as mock_settings:
            mock_settings.chunk_size = 900
            mock_settings.chunk_overlap = 150
            mock_settings.embeddings_provider = "openai"
            mock_settings.openai_embed_model = "text-embedding-3-small"
            mock_settings.openai_api_key = "sk-test"
            mock_settings.chroma_collection = "test_collection"
            mock_settings.chroma_dir = ".test_chroma"
            
            result = runner.invoke(app, [
                "process-documents",
                "/test/doc.txt",
                "--type", "cv",
                "--source", "cv/test",
                "--version", "1.0",
                "--role", "Software Engineer",
                "--skills", "Python,JavaScript",
                "--keywords", "web development,backend"
            ])
            
            assert result.exit_code == 0
            assert "Successfully stored 2 chunks in vector database" in result.stdout
            
            # Verify services were called correctly
            mock_services['loader_instance'].load_document.assert_called_once_with(Path("/test/doc.txt"))
            mock_services['chunker_instance'].chunk_document.assert_called_once()
            mock_services['store_instance'].add_documents.assert_called_once()
    
    def test_process_documents_directory(self, runner, mock_services):
        """Test processing a directory of documents."""
        with patch('rag_persona_db.document.create_rag_for_documents.settings') as mock_settings:
            mock_settings.chunk_size = 900
            mock_settings.chunk_overlap = 150
            mock_settings.embeddings_provider = "openai"
            mock_settings.openai_embed_model = "text-embedding-3-small"
            mock_settings.openai_api_key = "sk-test"
            mock_settings.chroma_collection = "test_collection"
            mock_settings.chroma_dir = ".test_chroma"
            
            result = runner.invoke(app, [
                "process-documents",
                "/test/documents/",
                "--type", "portfolio",
                "--source", "portfolio/2024",
                "--version", "2.0",
                "--visibility", "public"
            ])
            
            assert result.exit_code == 0
            assert "Successfully stored 2 chunks in vector database" in result.stdout
            
            # Verify services were called correctly
            mock_services['loader_instance'].load_directory.assert_called_once_with(Path("/test/documents/"))
            mock_services['chunker_instance'].chunk_document.assert_called_once()
            mock_services['store_instance'].add_documents.assert_called_once()
    
    def test_process_documents_dry_run(self, runner, mock_services):
        """Test dry run mode without storing to database."""
        with patch('rag_persona_db.document.create_rag_for_documents.settings') as mock_settings:
            mock_settings.chunk_size = 900
            mock_settings.chunk_overlap = 150
            mock_settings.embeddings_provider = "openai"
            mock_settings.openai_embed_model = "text-embedding-3-small"
            mock_settings.openai_api_key = "sk-test"
            mock_settings.chroma_collection = "test_collection"
            mock_settings.chroma_dir = ".test_chroma"
            
            result = runner.invoke(app, [
                "process-documents",
                "/test/doc.txt",
                "--type", "cv",
                "--source", "cv/test",
                "--version", "1.0",
                "--dry-run"
            ])
            
            assert result.exit_code == 0
            assert "Dry run completed - 2 chunks would be stored" in result.stdout
            
            # Verify vector store was not called
            mock_services['store_instance'].add_documents.assert_not_called()
    
    def test_process_documents_custom_chunking(self, runner, mock_services):
        """Test custom chunk size and overlap parameters."""
        with patch('rag_persona_db.document.create_rag_for_documents.settings') as mock_settings:
            mock_settings.chunk_size = 900
            mock_settings.chunk_overlap = 150
            mock_settings.embeddings_provider = "openai"
            mock_settings.openai_embed_model = "text-embedding-3-small"
            mock_settings.openai_api_key = "sk-test"
            mock_settings.chroma_collection = "test_collection"
            mock_settings.chroma_dir = ".test_chroma"
            
            result = runner.invoke(app, [
                "process-documents",
                "/test/doc.txt",
                "--type", "cv",
                "--source", "cv/test",
                "--version", "1.0",
                "--chunk-size", "1200",
                "--chunk-overlap", "200"
            ])
            
            assert result.exit_code == 0
            
            # Verify chunker was initialized with custom parameters
            mock_services['chunker'].assert_called_with(
                chunk_size=1200,
                chunk_overlap=200
            )
    
    def test_process_documents_with_output(self, runner, mock_services, tmp_path):
        """Test processing with output directory specified."""
        with patch('rag_persona_db.document.create_rag_for_documents.settings') as mock_settings:
            mock_settings.chunk_size = 900
            mock_settings.chunk_overlap = 150
            mock_settings.embeddings_provider = "openai"
            mock_settings.openai_embed_model = "text-embedding-3-small"
            mock_settings.openai_api_key = "sk-test"
            mock_settings.chroma_collection = "test_collection"
            mock_settings.chroma_dir = ".test_chroma"
            
            output_dir = tmp_path / "output"
            
            result = runner.invoke(app, [
                "process-documents",
                "/test/doc.txt",
                "--type", "cv",
                "--source", "cv/test",
                "--version", "1.0",
                "--output", str(output_dir)
            ])
            
            assert result.exit_code == 0
            assert "Metadata summary saved to" in result.stdout
            
            # Verify output directory was created
            assert output_dir.exists()
            assert (output_dir / "metadata_summary.json").exists()
    
    def test_list_collections(self, runner, mock_services):
        """Test listing collections command."""
        with patch('rag_persona_db.document.create_rag_for_documents.settings') as mock_settings:
            mock_settings.chroma_collection = "test_collection"
            mock_settings.chroma_dir = ".test_chroma"
            
            # Mock collection data
            mock_collection = Mock()
            mock_collection.name = "test_collection"
            mock_collection.count.return_value = 100
            mock_collection.metadata = {"embedding_dimension": 1536}
            
            mock_services['store_instance'].list_collections.return_value = [mock_collection]
            
            result = runner.invoke(app, ["list-collections"])
            
            assert result.exit_code == 0
            assert "test_collection" in result.stdout
            assert "100" in result.stdout
            assert "1536" in result.stdout
    
    def test_search_documents(self, runner, mock_services):
        """Test search command."""
        with patch('rag_persona_db.document.create_rag_for_documents.settings') as mock_settings:
            mock_settings.chroma_collection = "test_collection"
            mock_settings.chroma_dir = ".test_chroma"
            mock_settings.embeddings_provider = "openai"
            mock_settings.openai_embed_model = "text-embedding-3-small"
            mock_settings.openai_api_key = "sk-test"
            
            # Mock search results
            mock_result1 = Mock()
            mock_result1.metadata.doc_type.value = "cv"
            mock_result1.metadata.source_id = "cv/test"
            mock_result1.similarity = 0.85
            mock_result1.content = "Sample CV content about Python development"
            
            mock_result2 = Mock()
            mock_result2.metadata.doc_type.value = "portfolio"
            mock_result2.metadata.source_id = "portfolio/test"
            mock_result2.similarity = 0.78
            mock_result2.content = "Portfolio content about web development"
            
            mock_services['store_instance'].search.return_value = [mock_result1, mock_result2]
            
            result = runner.invoke(app, [
                "search",
                "Python development",
                "--limit", "5",
                "--threshold", "0.7"
            ])
            
            assert result.exit_code == 0
            assert "Python development" in result.stdout
            assert "cv" in result.stdout
            assert "portfolio" in result.stdout
            assert "0.850" in result.stdout
            assert "0.780" in result.stdout
    
    def test_search_no_results(self, runner, mock_services):
        """Test search with no results."""
        with patch('rag_persona_db.document.create_rag_for_documents.settings') as mock_settings:
            mock_settings.chroma_collection = "test_collection"
            mock_settings.chroma_dir = ".test_chroma"
            mock_settings.embeddings_provider = "openai"
            mock_settings.openai_embed_model = "text-embedding-3-small"
            mock_settings.openai_api_key = "sk-test"
            
            mock_services['store_instance'].search.return_value = []
            
            result = runner.invoke(app, ["search", "nonexistent query"])
            
            assert result.exit_code == 0
            assert "No results found" in result.stdout
    
    def test_process_documents_missing_required_args(self, runner):
        """Test process-documents with missing required arguments."""
        result = runner.invoke(app, ["process-documents"])
        
        assert result.exit_code != 0
        assert "Missing argument" in result.stdout
    
    def test_process_documents_invalid_document_type(self, runner):
        """Test process-documents with invalid document type."""
        result = runner.invoke(app, [
            "process-documents",
            "/test/doc.txt",
            "--type", "invalid_type",
            "--source", "cv/test",
            "--version", "1.0"
        ])
        
        assert result.exit_code != 0
        assert "Invalid value" in result.stdout
    
    def test_process_documents_invalid_visibility(self, runner):
        """Test process-documents with invalid visibility."""
        result = runner.invoke(app, [
            "process-documents",
            "/test/doc.txt",
            "--type", "cv",
            "--source", "cv/test",
            "--version", "1.0",
            "--visibility", "invalid_visibility"
        ])
        
        assert result.exit_code != 0
        assert "Invalid value" in result.stdout
    
    def test_help_command(self, runner):
        """Test help command output."""
        result = runner.invoke(app, ["--help"])
        
        assert result.exit_code == 0
        assert "RAG Persona Database - Document Processing CLI" in result.stdout
        assert "process-documents" in result.stdout
        assert "list-collections" in result.stdout
        assert "search" in result.stdout
    
    def test_process_documents_help(self, runner):
        """Test process-documents help output."""
        result = runner.invoke(app, ["process-documents", "--help"])
        
        assert result.exit_code == 0
        assert "Process documents and create RAG embeddings" in result.stdout
        assert "--type" in result.stdout
        assert "--source" in result.stdout
        assert "--version" in result.stdout


class TestCLIErrorHandling:
    """Test CLI error handling and edge cases."""
    
    @pytest.fixture
    def runner(self):
        """Create CLI runner for testing."""
        return CliRunner()
    
    def test_process_documents_file_not_found(self, runner, mock_services):
        """Test handling of non-existent file."""
        with patch('rag_persona_db.document.create_rag_for_documents.settings') as mock_settings:
            mock_settings.chunk_size = 900
            mock_settings.chunk_overlap = 150
            mock_settings.embeddings_provider = "openai"
            mock_settings.openai_embed_model = "text-embedding-3-small"
            mock_settings.openai_api_key = "sk-test"
            mock_settings.chroma_collection = "test_collection"
            mock_settings.chroma_dir = ".test_chroma"
            
            # Mock loader to return empty list
            mock_services['loader_instance'].load_directory.return_value = []
            
            result = runner.invoke(app, [
                "process-documents",
                "/nonexistent/path/",
                "--type", "cv",
                "--source", "cv/test",
                "--version", "1.0"
            ])
            
            assert result.exit_code == 1
            assert "No documents found to process" in result.stdout
    
    def test_process_documents_service_error(self, runner, mock_services):
        """Test handling of service errors."""
        with patch('rag_persona_db.document.create_rag_for_documents.settings') as mock_settings:
            mock_settings.chunk_size = 900
            mock_settings.chunk_overlap = 150
            mock_settings.embeddings_provider = "openai"
            mock_settings.openai_embed_model = "text-embedding-3-small"
            mock_settings.openai_api_key = "sk-test"
            mock_settings.chroma_collection = "test_collection"
            mock_settings.chroma_dir = ".test_chroma"
            
            # Mock vector store to raise exception
            mock_services['store_instance'].add_documents.side_effect = Exception("Database error")
            
            result = runner.invoke(app, [
                "process-documents",
                "/test/doc.txt",
                "--type", "cv",
                "--source", "cv/test",
                "--version", "1.0"
            ])
            
            assert result.exit_code == 1
            assert "Error processing documents: Database error" in result.stdout
    
    def test_list_collections_error(self, runner, mock_services):
        """Test handling of collection listing errors."""
        with patch('rag_persona_db.document.create_rag_for_documents.settings') as mock_settings:
            mock_settings.chroma_collection = "test_collection"
            mock_settings.chroma_dir = ".test_chroma"
            
            # Mock vector store to raise exception
            mock_services['store_instance'].list_collections.side_effect = Exception("Connection error")
            
            result = runner.invoke(app, ["list-collections"])
            
            assert result.exit_code == 1
            assert "Error listing collections: Connection error" in result.stdout
    
    def test_search_error(self, runner, mock_services):
        """Test handling of search errors."""
        with patch('rag_persona_db.document.create_rag_for_documents.settings') as mock_settings:
            mock_settings.chroma_collection = "test_collection"
            mock_settings.chroma_dir = ".test_chroma"
            mock_settings.embeddings_provider = "openai"
            mock_settings.openai_embed_model = "text-embedding-3-small"
            mock_settings.openai_api_key = "sk-test"
            
            # Mock vector store to raise exception
            mock_services['store_instance'].search.side_effect = Exception("Search error")
            
            result = runner.invoke(app, ["search", "test query"])
            
            assert result.exit_code == 1
            assert "Error searching: Search error" in result.stdout


class TestCLIIntegration:
    """Test CLI integration with real components."""
    
    @pytest.fixture
    def runner(self):
        """Create CLI runner for testing."""
        return CliRunner()
    
    def test_end_to_end_processing(self, runner, tmp_path):
        """Test end-to-end document processing workflow."""
        # Create a test document
        test_doc = tmp_path / "test_cv.txt"
        test_doc.write_text("Experienced software engineer with Python skills.")
        
        # Mock settings to avoid external dependencies
        with patch('rag_persona_db.document.create_rag_for_documents.settings') as mock_settings, \
             patch('rag_persona_db.document.create_rag_for_documents.DocumentLoader') as mock_loader, \
             patch('rag_persona_db.document.create_rag_for_documents.DocumentChunker') as mock_chunker, \
             patch('rag_persona_db.document.create_rag_for_documents.EmbeddingService') as mock_embedding, \
             patch('rag_persona_db.document.create_rag_for_documents.VectorStore') as mock_store:
            
            # Configure mock settings
            mock_settings.chunk_size = 900
            mock_settings.chunk_overlap = 150
            mock_settings.embeddings_provider = "openai"
            mock_settings.openai_embed_model = "text-embedding-3-small"
            mock_settings.openai_api_key = "sk-test"
            mock_settings.chroma_collection = "test_collection"
            mock_settings.chroma_dir = ".test_chroma"
            
            # Mock document loading
            mock_loader_instance = Mock()
            mock_loader_instance.load_document.return_value = Mock(
                content="Experienced software engineer with Python skills.",
                file_path=test_doc,
                file_size=test_doc.stat().st_size,
                file_extension=".txt"
            )
            mock_loader.return_value = mock_loader_instance
            
            # Mock chunking
            mock_chunker_instance = Mock()
            mock_chunker_instance.chunk_document.return_value = [
                Mock(
                    content="Experienced software engineer with Python skills.",
                    metadata=Mock(
                        doc_type="cv",
                        source_id="cv/test",
                        version="1.0",
                        chunk_index=0,
                        total_chunks=1,
                        content_sha256="abc123"
                    )
                )
            ]
            mock_chunker.return_value = mock_chunker_instance
            
            # Mock embedding service
            mock_embedding_instance = Mock()
            mock_embedding.return_value = mock_embedding_instance
            
            # Mock vector store
            mock_store_instance = Mock()
            mock_store_instance.add_documents.return_value = None
            mock_store.return_value = mock_store_instance
            
            # Run the command
            result = runner.invoke(app, [
                "process-documents",
                str(test_doc),
                "--type", "cv",
                "--source", "cv/test",
                "--version", "1.0",
                "--dry-run"
            ])
            
            # Verify the command succeeded
            assert result.exit_code == 0
            assert "Dry run completed - 1 chunks would be stored" in result.stdout
            
            # Verify all services were called
            mock_loader_instance.load_document.assert_called_once()
            mock_chunker_instance.chunk_document.assert_called_once()
            # Note: add_documents not called in dry-run mode
