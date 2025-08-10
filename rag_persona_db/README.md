# RAG Persona Database

A sophisticated RAG (Retrieval-Augmented Generation) system designed for personal documents and personality data analysis. This system combines document processing, vector embeddings, and personality assessment to create a comprehensive knowledge base for personal and professional development.

## 🎯 Purpose

The RAG Persona Database is designed to:
- **Process and analyze personal documents** (CVs, portfolios, projects, blogs)
- **Extract personality insights** from assessments and questionnaires
- **Create searchable vector embeddings** for semantic search and retrieval
- **Support personal development** through comprehensive self-knowledge
- **Enable AI-powered insights** about skills, experiences, and personality traits

## 🏗️ Architecture

The system follows a modular, scalable architecture:

```
rag_persona_db/
├── rag_core/           # Core RAG functionality
│   ├── schema.py       # Data models and validation
│   ├── settings.py     # Configuration management
│   ├── loaders.py      # Document loading and parsing
│   ├── chunking.py     # Text chunking strategies
│   ├── embeddings.py   # Vector embedding services
│   ├── store.py        # Vector database operations
│   ├── agno_flow.py    # Advanced RAG workflows
│   └── utils.py        # Utility functions
├── document/           # Document processing interface
│   ├── create_rag_for_documents.py  # CLI interface
│   └── sample_inputs/  # Example documents
└── tests/              # Comprehensive test suite
```

## 🚀 Features

### Core Capabilities
- **Multi-format document support**: PDF, DOCX, TXT, MD, JSON
- **Intelligent text chunking**: Configurable chunk sizes with overlap
- **Multiple embedding providers**: OpenAI and local sentence-transformers
- **Vector database storage**: ChromaDB integration with persistence
- **Personality analysis**: Big Five, MBTI, and custom trait extraction

### Document Types Supported
- **CV/Resume**: Professional experience and skills
- **Portfolio**: Project showcases and achievements
- **Blog Posts**: Personal insights and knowledge sharing
- **Personality Assessments**: Psychological profile data
- **Testimonials**: Feedback and recommendations
- **Bio**: Personal background and interests

### Advanced Features
- **Semantic search**: Find similar content across documents
- **Metadata enrichment**: Automatic skill and keyword extraction
- **Version control**: Track document changes over time
- **Privacy controls**: Public/private document visibility
- **Multi-language support**: Internationalization ready

## 📦 Installation

### Prerequisites
- Python 3.11+
- pip or poetry
- OpenAI API key (optional, for OpenAI embeddings)

### Quick Start
```bash
# Clone the repository
git clone <repository-url>
cd rag_persona_db

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp env.example .env
# Edit .env with your configuration

# Run tests
pytest tests/
```

### Environment Configuration
Create a `.env` file with your settings:

```env
# ChromaDB Configuration
CHROMA_DIR=.chromadb
CHROMA_COLLECTION=echoai_knowledge

# Embeddings Provider
EMBEDDINGS_PROVIDER=openai  # or sentence-transformers
OPENAI_API_KEY=your_openai_key_here
OPENAI_EMBED_MODEL=text-embedding-3-small

# Document Processing
CHUNK_SIZE=900
CHUNK_OVERLAP=150
DEFAULT_VISIBILITY=public

# Logging
LOG_LEVEL=INFO
```

## 🎮 Usage

### CLI Interface

The system provides a comprehensive command-line interface:

```bash
# Process documents and create RAG embeddings
python -m rag_persona_db.document.create_rag_for_documents process-documents \
    /path/to/documents \
    --type cv \
    --source "cv/master" \
    --version "2.0" \
    --role "Software Engineer" \
    --skills "Python,JavaScript,React" \
    --keywords "web development,backend,frontend"

# List available collections
python -m rag_persona_db.document.create_rag_for_documents list-collections

# Search for similar content
python -m rag_persona_db.document.create_rag_for_documents search \
    "machine learning projects" \
    --limit 10 \
    --threshold 0.7
```

### Python API

```python
from rag_persona_db.rag_core.settings import settings
from rag_persona_db.rag_core.loaders import DocumentLoader
from rag_persona_db.rag_core.chunking import DocumentChunker
from rag_persona_db.rag_core.embeddings import EmbeddingService
from rag_persona_db.rag_core.store import VectorStore

# Initialize services
loader = DocumentLoader()
chunker = DocumentChunker(
    chunk_size=settings.chunk_size,
    chunk_overlap=settings.chunk_overlap
)
embedding_service = EmbeddingService(
    provider=settings.embeddings_provider,
    model_name=settings.openai_embed_model,
    api_key=settings.openai_api_key
)
vector_store = VectorStore(
    collection_name=settings.chroma_collection,
    persist_directory=settings.chroma_dir
)

# Process documents
documents = loader.load_directory("/path/to/documents")
chunks = chunker.chunk_documents(documents)
vector_store.add_documents(chunks, embedding_service)

# Search
results = vector_store.search("Python development", embedding_service, limit=5)
```

## 🔧 Configuration

### Document Processing Settings
- **Chunk Size**: Text chunk size in characters (100-2000)
- **Chunk Overlap**: Overlap between chunks (0-500)
- **Default Visibility**: Public or private documents
- **Language**: Document language code (default: en)

### Embedding Configuration
- **Provider**: OpenAI or local sentence-transformers
- **Model**: Specific embedding model name
- **API Key**: OpenAI API key (if using OpenAI)

### Vector Database Settings
- **Storage Directory**: ChromaDB persistence location
- **Collection Name**: Vector collection identifier
- **Metadata**: Custom metadata fields

## 🧪 Testing

The project includes comprehensive tests:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=rag_persona_db --cov-report=html

# Run specific test categories
pytest tests/test_schema.py
pytest tests/test_settings.py
```

### Test Categories
- **Schema Validation**: Data model testing
- **Settings Configuration**: Environment and config testing
- **Document Processing**: Loader and chunker testing
- **Vector Operations**: Store and search testing
- **Integration**: End-to-end workflow testing

## 📊 Sample Data

The project includes sample documents for testing:

- **Sample CV**: Professional experience and skills
- **Personality Assessment**: Big Five and MBTI data
- **Project Portfolio**: Project showcases and achievements

## 🔒 Security & Privacy

### Data Protection
- **Local Processing**: All processing happens locally by default
- **Encryption**: Sensitive data encryption support
- **Access Control**: Public/private document visibility
- **Audit Trail**: Document processing history

### Privacy Features
- **No External Storage**: Vector database stored locally
- **Configurable Sharing**: Control document visibility
- **Data Retention**: Configurable data retention policies

## 🚧 Development

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install

# Run linting
ruff check .
black .

# Run type checking
mypy rag_persona_db/
```

### Code Quality
- **Linting**: Ruff for code quality
- **Formatting**: Black for consistent formatting
- **Type Checking**: MyPy for type safety
- **Testing**: Pytest for comprehensive testing

## 📈 Performance

### Optimization Features
- **Efficient Chunking**: Smart text segmentation
- **Batch Processing**: Process multiple documents efficiently
- **Caching**: Embedding and metadata caching
- **Async Support**: Non-blocking operations

### Scalability
- **Modular Design**: Easy to extend and modify
- **Plugin Architecture**: Support for custom loaders and processors
- **Distributed Processing**: Support for multiple workers
- **Cloud Ready**: Easy deployment to cloud platforms

## 🔮 Roadmap

### Planned Features
- **Web Interface**: Browser-based document management
- **API Endpoints**: RESTful API for integration
- **Advanced Analytics**: Document insights and trends
- **Collaboration**: Multi-user document sharing
- **Mobile Support**: Mobile app for document capture

### Integration Opportunities
- **Notion**: Import from Notion workspaces
- **Google Drive**: Sync with Google Drive
- **GitHub**: Import from GitHub repositories
- **LinkedIn**: Profile data integration

## 📚 Documentation

### Additional Resources
- **API Reference**: Complete API documentation
- **User Guide**: Step-by-step usage instructions
- **Developer Guide**: Architecture and development details
- **Examples**: Real-world usage examples

### Support
- **Issues**: GitHub issue tracker
- **Discussions**: Community discussions
- **Wiki**: Project knowledge base

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **ChromaDB**: Vector database backend
- **OpenAI**: Embedding models and API
- **Sentence Transformers**: Local embedding models
- **Pydantic**: Data validation and settings
- **Typer**: CLI interface framework

## 📞 Contact

For questions, support, or contributions:
- **GitHub Issues**: [Project Issues](https://github.com/your-repo/issues)
- **Email**: team@example.com
- **Discord**: [Community Server](https://discord.gg/your-server)

---

**Built with ❤️ for personal development and AI-powered insights**
