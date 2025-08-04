# 🎤 EchoAI - Voice Chat with AI Clone

A real-time AI voice chat system featuring Speech-to-Text, Language Model processing, and Text-to-Speech synthesis with low-latency streaming capabilities.

## 🚀 Features

- **🎤 Real-time Voice Chat**: Seamless voice conversation with AI assistant
- **🧠 Multi-Model AI Pipeline**: STT → LLM → TTS with intelligent fallbacks
- **⚡ Low Latency**: Optimized for real-time conversation with chunked processing
- **🔄 Fallback Mechanisms**: Automatic switching between primary and backup models
- **💾 Smart Caching**: TTS response caching for common phrases
- **📊 Performance Monitoring**: Real-time latency and usage statistics
- **🌐 WebSocket Streaming**: Real-time audio streaming via WebSocket
- **🎨 Modern UI**: Beautiful, responsive frontend interface

## 🏗️ Architecture

### Core Components

1. **STT Service**: Hugging Face Whisper (default) + OpenAI Whisper (fallback)
2. **LLM Service**: Mistral 7B (Hugging Face) + GPT-4o-mini (fallback)
3. **TTS Service**: ElevenLabs streaming voice cloning with caching
4. **Agno Agent**: Orchestrates the complete AI pipeline
5. **FastAPI Backend**: WebSocket endpoints for real-time communication
6. **Frontend**: HTML/JS interface with audio recording and playback

### Latency Optimization

- **Chunked Audio Processing**: 1-2 second audio segments for faster STT
- **Async Concurrency**: Non-blocking API calls across all services
- **Parallel Pipeline**: TTS streaming while LLM generates response
- **Model Preloading**: Warm-up APIs on startup for reduced latency
- **Efficient Audio Conversion**: Server-side WebM→WAV conversion
- **Smart Caching**: Cache common TTS responses for instant playback

## 📋 Prerequisites

- Python 3.12+
- FFmpeg (for audio processing)
- API Keys:
  - Hugging Face API Key
  - OpenAI API Key
  - ElevenLabs API Key

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/EchoAI.git
cd EchoAI
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy the example environment file and add your API keys:

```bash
cp env.example .env
```

Edit `.env` with your actual API keys:

```env
HUGGINGFACE_API_KEY=your_hf_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
```

### 4. Run the Application

```bash
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Access the Application

Open your browser and navigate to:
- **Frontend**: `http://localhost:8000/frontend/index.html`
- **API Docs**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/health`

## 🐳 Docker Deployment

### Build and Run with Docker

```bash
# Build the Docker image
docker build -t echoai .

# Run the container
docker run -p 8000:8000 --env-file .env echoai
```

### Docker Compose

Create a `docker-compose.yml` file:

```yaml
version: '3.8'
services:
  echoai:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
```

Run with:
```bash
docker-compose up -d
```

## 🧪 Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test Suites

```bash
# STT Service Tests
pytest tests/test_stt.py -v

# LLM Service Tests
pytest tests/test_llm.py -v

# TTS Service Tests
pytest tests/test_tts.py -v
```

### Test Coverage

```bash
pytest --cov=src tests/ --cov-report=html
```

## 📊 API Endpoints

### REST Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `GET /stats` - Performance statistics
- `POST /clear-conversation` - Clear conversation history

### WebSocket Endpoints

- `WS /ws/voice` - Real-time voice chat

### WebSocket Message Types

#### Client → Server
```json
{
  "type": "audio",
  "audio": "base64_encoded_audio_data"
}
```

#### Server → Client
```json
{
  "type": "response",
  "transcription": "User's transcribed speech",
  "response_text": "AI's response",
  "audio": "base64_encoded_response_audio",
  "latency": {
    "pipeline": 2.5,
    "stt": 0.8,
    "llm": 1.2,
    "tts": 0.5
  }
}
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HUGGINGFACE_API_KEY` | Hugging Face API key | Required |
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `ELEVENLABS_API_KEY` | ElevenLabs API key | Required |
| `DEFAULT_STT_MODEL` | Primary STT model | `openai/whisper-large-v3` |
| `FALLBACK_STT_MODEL` | Fallback STT model | `openai/whisper-1` |
| `DEFAULT_LLM_MODEL` | Primary LLM model | `mistralai/Mistral-7B-Instruct-v0.2` |
| `FALLBACK_LLM_MODEL` | Fallback LLM model | `gpt-4o-mini` |
| `DEFAULT_TTS_VOICE_ID` | ElevenLabs voice ID | `21m00Tcm4TlvDq8ikWAM` |
| `STT_CHUNK_DURATION` | Audio chunk duration (seconds) | `2.0` |
| `LLM_TEMPERATURE` | LLM response randomness | `0.0` |
| `TTS_STREAMING` | Enable TTS streaming | `True` |
| `CACHE_TTS_RESPONSES` | Enable TTS caching | `True` |

### Latency Thresholds

| Service | Default Timeout | Fallback Trigger |
|---------|----------------|------------------|
| STT | 5.0s | > 3.0s |
| LLM | 10.0s | > 5.0s |
| TTS | 8.0s | > 4.0s |

## 🚀 Deployment

### Hugging Face Spaces

1. Create a new Space on Hugging Face
2. Upload your code to the Space
3. Configure environment variables in Space settings
4. Deploy automatically

### Railway/Render

1. Connect your GitHub repository
2. Set environment variables
3. Deploy automatically

### VPS Deployment

```bash
# Install system dependencies
sudo apt update
sudo apt install -y python3.12 python3.12-pip ffmpeg

# Clone and setup
git clone https://github.com/yourusername/EchoAI.git
cd EchoAI
pip install -r requirements.txt

# Setup systemd service
sudo nano /etc/systemd/system/echoai.service
```

Systemd service file:
```ini
[Unit]
Description=EchoAI Voice Chat
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/EchoAI
Environment=PATH=/path/to/EchoAI/venv/bin
ExecStart=/path/to/EchoAI/venv/bin/python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

## 📈 Performance Optimization

### Latency Mitigation Strategies

1. **Chunked Processing**: Process 1-2 second audio segments
2. **Async Concurrency**: Non-blocking API calls
3. **Parallel Pipeline**: Start TTS while LLM generates
4. **Smart Caching**: Cache common TTS responses
5. **Model Preloading**: Warm up APIs on startup
6. **Efficient Audio**: Server-side format conversion
7. **Fallback Logic**: Automatic model switching

### Monitoring

- Real-time latency tracking
- Performance statistics via `/stats` endpoint
- Structured logging with timestamps
- Error tracking and fallback monitoring

## 🔒 Security Considerations

- API keys stored in environment variables
- Input validation and sanitization
- Rate limiting for API calls
- Secure WebSocket connections
- Audio data encryption in transit

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Hugging Face](https://huggingface.co/) for open-source models
- [OpenAI](https://openai.com/) for API services
- [ElevenLabs](https://elevenlabs.io/) for voice synthesis
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [Agno](https://github.com/agno-ai/agno) for agent orchestration

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Check the documentation at `/docs`
- Review the health endpoint at `/health`

---

**Made with ❤️ for real-time AI voice conversations**