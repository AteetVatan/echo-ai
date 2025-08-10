# EchoAI - Real-Time AI Voice Chat System

## 🎯 Project Overview

EchoAI is a sophisticated real-time AI voice chat application that enables natural conversations with AI assistants through voice interaction. The system features a complete pipeline from speech-to-text conversion, AI response generation, to text-to-speech synthesis, all orchestrated through a modern web-based interface.

## 🏗️ Architecture

### System Architecture Pattern
**Modular Layered Architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Frontend      │  │   WebSocket     │  │   REST API   │ │
│  │   (HTML/JS)     │  │   Connection    │  │   Endpoints  │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                        │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Voice Clone Agent                          │ │
│  │        (Orchestrates the entire pipeline)               │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    SERVICE LAYER                            │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │   STT        │  │   LLM        │  │   TTS              │ │
│  │   Service    │  │   Service    │  │   Service          │ │
│  └──────────────┘  └──────────────┘  └────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    UTILITY LAYER                            │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │   Config     │  │   Logging    │  │   Audio            │ │
│  │   Manager    │  │   System     │  │   Processing       │ │
│  └──────────────┘  └──────────────┘  └────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

#### Backend
- **Framework**: FastAPI (Python 3.12+)
- **WebSockets**: Real-time bidirectional communication
- **Orchestration**: Agno framework for AI agent management
- **Audio Processing**: pydub, numpy, ffmpeg
- **Configuration**: pydantic-settings, python-dotenv
- **Logging**: Structured logging with performance metrics

#### AI Services
- **Speech-to-Text**: Hugging Face Whisper (primary), OpenAI Whisper (fallback)
- **Language Model**: Mistral AI API (primary), OpenAI GPT-4o-mini (fallback)
- **Text-to-Speech**: ElevenLabs streaming voice cloning

#### Frontend
- **Interface**: Single-page HTML/JavaScript application
- **Audio**: Web Audio API for real-time audio capture
- **Communication**: WebSocket for real-time data exchange

#### Development & Deployment
- **Testing**: pytest with comprehensive unit and integration tests
- **Containerization**: Docker for consistent deployment
- **Dependencies**: requirements.txt with pinned versions

## 📁 Project Structure

```
EchoAI/
├── 📁 src/                    # Main application code
│   ├── api/               # Web server and API endpoints
│   │   └── main.py           # FastAPI application and WebSocket handlers
│   ├── services/          # AI service implementations
│   │   ├── stt_service.py    # Speech-to-Text service with fallback logic
│   │   ├── llm_service.py    # Language model service with conversation memory
│   │   └── tts_service.py    # Text-to-Speech service with caching
│   ├── agents/            # AI agent orchestration
│   │   └── (removed - replaced by hybrid architecture)
│   └── utils/             # Utility modules and helpers
│       ├── config.py         # Configuration management with environment variables
│       ├── logging.py        # Structured logging and performance monitoring
│       └── 📁 audio/         # Audio processing utilities
│           ├── audio_processor.py      # Comprehensive audio processing
│           └── audio_stream_processor.py # Real-time audio streaming
├── 📁 frontend/              # User interface
│   ├── index.html            # Main HTML page with modern UI
│   └── script.js             # JavaScript for WebSocket and audio handling
├── 📁 tests/                 # Test suite
│   ├── test_stt.py           # STT service tests
│   ├── test_llm.py           # LLM service tests
│   └── test_tts.py           # TTS service tests
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variables template
├── Dockerfile               # Container configuration
└── README.md                # Project documentation
```

## 🔄 Core Features

### 1. Real-Time Voice Chat
- **Traditional Mode**: Record complete audio messages
- **Streaming Mode**: Real-time audio chunk processing for ultra-low latency
- **Bidirectional Communication**: Seamless voice conversation flow

### 2. AI Pipeline
- **Speech-to-Text**: Convert user speech to text with high accuracy
- **AI Response Generation**: Context-aware responses with conversation memory
- **Text-to-Speech**: Natural voice synthesis with voice cloning capabilities

### 3. Performance Optimizations
- **Fallback Mechanisms**: Automatic service switching on failures
- **Caching**: TTS response caching for improved performance
- **Model Preloading**: Warm-up services for faster response times
- **Chunked Processing**: Real-time audio streaming for minimal latency

### 4. User Experience
- **Modern UI**: Clean, responsive interface
- **Real-time Status**: Connection and processing status indicators
- **Conversation History**: Persistent chat interface
- **Performance Metrics**: Latency and throughput monitoring

## 🚀 Getting Started

### Prerequisites
- Python 3.12 or higher
- FFmpeg installed on system
- API keys for:
  - Hugging Face (for STT and LLM)
  - OpenAI (for fallback services)
  - ElevenLabs (for TTS)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd EchoAI
```

2. **Set up virtual environment**
```bash
python -m venv echoai_env
source echoai_env/bin/activate  # On Windows: echoai_env\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your API keys
```

5. **Run the application**
```bash
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

6. **Access the application**
```
Open browser to: http://localhost:8000
```

## 🔧 Configuration

### Environment Variables

```bash
# API Keys
HUGGINGFACE_API_KEY=hf_your_key_here
OPENAI_API_KEY=sk-your_key_here
ELEVENLABS_API_KEY=your_key_here

# Service Configuration
DEFAULT_STT_MODEL=openai/whisper-base
DEFAULT_LLM_MODEL=mistralai/Mistral-7B-Instruct-v0.2
ELEVENLABS_VOICE_ID=your_voice_id

# Performance Settings
STT_TIMEOUT=5.0
LLM_TIMEOUT=10.0
TTS_TIMEOUT=8.0
TTS_CACHE_ENABLED=true
TTS_STREAMING=true

# Audio Settings
SAMPLE_RATE=16000
CHANNELS=1
AUDIO_FORMAT=wav

# Server Settings
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
```

## 🧪 Testing

### Run Tests
```bash
# All tests
pytest

# Specific test file
pytest tests/test_stt.py

# With coverage
pytest --cov=src

# Verbose output
pytest -v
```

### Test Categories
- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end pipeline testing
- **Performance Tests**: Latency and throughput validation
- **Error Handling Tests**: Fallback mechanism validation

## 🐳 Deployment

### Docker Deployment
```bash
# Build image
docker build -t echoai .

# Run container
docker run -p 8000:8000 --env-file .env echoai
```

### Production Considerations
- **Load Balancing**: Multiple instances behind reverse proxy
- **Caching**: Redis for session and response caching
- **Monitoring**: Application performance monitoring
- **Security**: HTTPS, rate limiting, input validation

## 📊 Performance Metrics

### Latency Targets
- **STT Processing**: < 2 seconds
- **LLM Response**: < 5 seconds
- **TTS Synthesis**: < 3 seconds
- **Total Pipeline**: < 8 seconds

### Throughput
- **Concurrent Users**: 10+ simultaneous conversations
- **Audio Quality**: 16kHz, mono, WAV format
- **Streaming Latency**: < 500ms per chunk

## 🔍 Debugging

### Common Issues

1. **API Key Errors**
   - Verify all API keys in `.env` file
   - Check API key permissions and quotas

2. **Audio Recording Issues**
   - Ensure microphone permissions granted
   - Use HTTPS or localhost for microphone access

3. **WebSocket Connection**
   - Verify server is running on correct port
   - Check firewall settings

4. **Performance Issues**
   - Monitor resource usage (CPU, memory)
   - Check API rate limits
   - Verify model loading status

### Debug Tools
- **Structured Logging**: Detailed performance and error logs
- **WebSocket Inspector**: Browser developer tools
- **Performance Monitoring**: Built-in latency tracking

## 🎯 Use Cases

### Primary Use Cases
1. **Personal AI Assistant**: Voice-based task management
2. **Language Learning**: Interactive conversation practice
3. **Accessibility**: Voice interface for users with disabilities
4. **Customer Support**: AI-powered voice support system

### Extended Use Cases
1. **Education**: Interactive voice lessons and tutoring
2. **Healthcare**: Voice-based health monitoring and assistance
3. **Entertainment**: Voice-controlled games and storytelling
4. **Business**: Meeting transcription and voice notes

## 🔮 Future Enhancements

### Planned Features
- **Multi-language Support**: Internationalization
- **Voice Recognition**: Speaker identification
- **Emotion Detection**: Sentiment analysis in voice
- **Custom Voice Training**: User-specific voice cloning
- **Mobile App**: Native iOS/Android applications

### Technical Improvements
- **Edge Computing**: Local processing for privacy
- **Advanced Caching**: Intelligent response caching
- **Load Balancing**: Horizontal scaling capabilities
- **Analytics**: Usage and performance analytics

## 📝 Contributing

### Development Guidelines
- Follow PEP 8 coding standards
- Write comprehensive tests
- Document all public APIs
- Use type hints throughout
- Implement proper error handling

### Code Review Process
1. Create feature branch
2. Implement changes with tests
3. Submit pull request
4. Code review and approval
5. Merge to main branch

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Team

**Project Lead**: [Your Name]  
**Architecture**: Modular AI Pipeline Design  
**Technology Stack**: FastAPI, WebSockets, Hugging Face, Mistral AI, OpenAI, ElevenLabs  

---

*EchoAI - Bringing AI conversations to life through voice* 🎤🤖 