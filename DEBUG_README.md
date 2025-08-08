# EchoAI Debug Script Guide

## 🎯 Overview

The `main_debug_no_ws.py` script is a standalone debugging tool that allows you to test the EchoAI voice chat system without WebSocket connections. This is perfect for:

- **Quick testing** of the AI pipeline
- **Debugging** individual components (STT, LLM, TTS)
- **Performance analysis** with detailed latency breakdown
- **Development** without browser dependencies

## 🚀 Quick Start

### 1. Basic Usage

```bash
# Test with generated audio (sine wave)
python main_debug_no_ws.py

# Test with your own audio file
python main_debug_no_ws.py my_audio.wav

# Test with different audio formats
python main_debug_no_ws.py test.mp3
python main_debug_no_ws.py sample.m4a
```

### 2. What It Does

The script performs these tests in sequence:

1. **🔍 STT Test**: Converts your audio to text
2. **🧠 LLM Test**: Generates AI response from text
3. **🔊 TTS Test**: Converts response back to speech
4. **🚀 Full Pipeline**: Tests the complete STT→LLM→TTS flow

### 3. Output Files

The script generates these files:

- `debug_output.wav` - Individual TTS output
- `pipeline_output.wav` - Complete pipeline output

## 📊 Sample Output

```
🔧 EchoAI Debug Script Starting...
==================================================
📁 Using audio file: sample_audio.wav
📊 Audio data size: 32000 bytes
🔥 Warming up AI services...
✅ Services warmed up successfully
==================================================
🧪 Testing Individual Components...
🔍 Testing STT Service...
✅ Audio processed: 32000 bytes
✅ STT completed in 1.23s
📝 Transcription: Hello, how are you today?
🔧 Model used: openai/whisper-large-v3
------------------------------
🧠 Testing LLM Service...
✅ LLM completed in 2.45s
💬 Response: I'm doing great! How about you?
🔧 Model used: mistral_ai
------------------------------
🔊 Testing TTS Service...
✅ TTS completed in 1.87s
🎵 Audio generated: 45000 bytes
🔧 Model used: ElevenLabs
💾 Audio saved to: debug_output.wav
==================================================
🚀 Testing Complete Pipeline...
✅ Full pipeline completed in 5.67s
📝 Transcription: Hello, how are you today?
💬 Response: I'm doing great! How about you?
🎵 Audio generated: 45000 bytes
⏱️ Latency breakdown:
   - STT: 1.23s
   - LLM: 2.45s
   - TTS: 1.87s
   - Total: 5.67s
💾 Audio saved to: pipeline_output.wav
==================================================
✅ Debug session completed!
📋 Summary:
   - Audio processed: 32000 bytes
   - Transcription: Hello, how are you today?
   - Response: I'm doing great! How about you?
   - Total pipeline time: 5.67s
🎉 Debug script finished successfully!
```

## 🔧 Configuration

### Environment Setup

Make sure your `.env` file contains valid API keys:

```bash
# Required API Keys
HUGGINGFACE_API_KEY=hf_your_key_here
OPENAI_API_KEY=sk-your_key_here
ELEVENLABS_API_KEY=your_key_here
MISTRAL_API_KEY=your_mistral_key_here

# Optional: Model Configuration
DEFAULT_STT_MODEL=openai/whisper-large-v3
MISTRAL_MODEL=mistral-large-latest
ELEVENLABS_VOICE_ID=your_voice_id

# Mistral Configuration
MISTRAL_API_BASE=https://api.mistral.ai
MISTRAL_TEMPERATURE=0.0
```

### Audio File Requirements

The script supports various audio formats:

- **WAV** (recommended for best compatibility)
- **MP3** (will be converted automatically)
- **M4A** (will be converted automatically)
- **WebM** (will be converted automatically)

**Optimal settings:**
- Sample rate: 16kHz
- Channels: Mono
- Format: WAV

## 🐛 Troubleshooting

### Common Issues

1. **"API key not found"**
   ```bash
   # Check your .env file
   cat .env
   
   # Verify keys are not placeholder values
   # Should not contain: hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

2. **"Audio file not found"**
   ```bash
   # Check file path
   ls -la your_audio_file.wav
   
   # Use absolute path if needed
   python main_debug_no_ws.py /full/path/to/audio.wav
   ```

3. **"STT failed"**
   ```bash
   # Check Hugging Face API key
   # Try with a simple audio file first
   python main_debug_no_ws.py  # Uses test audio
   ```

4. **"LLM failed"**
   ```bash
   # Check OpenAI API key
   # Verify internet connection
   # Check API rate limits
   ```

5. **"TTS failed"**
   ```bash
   # Check ElevenLabs API key
   # Verify voice ID is correct
   # Check API quota
   ```

### Debug Mode

For more detailed logging:

```bash
# Set log level to DEBUG
export LOG_LEVEL=DEBUG
python main_debug_no_ws.py
```

## 📈 Performance Analysis

### Latency Targets

The script helps you verify these performance targets:

- **STT Processing**: < 2 seconds
- **LLM Response**: < 5 seconds  
- **TTS Synthesis**: < 3 seconds
- **Total Pipeline**: < 8 seconds

### Performance Tips

1. **Use WAV format** for fastest processing
2. **Keep audio files small** (< 10 seconds)
3. **Use mono audio** for better STT accuracy
4. **Check API quotas** to avoid rate limiting

## 🔄 Integration with Main App

This debug script uses the same components as the main application:

- **Same services**: STT, LLM, TTS
- **Same configuration**: `.env` file
- **Same models**: Hugging Face, OpenAI, ElevenLabs
- **Same audio processing**: pydub, numpy

If the debug script works, the main app should work too!

## 🎯 Use Cases

### Development
```bash
# Test new audio files
python main_debug_no_ws.py new_sample.wav

# Verify API keys work
python main_debug_no_ws.py

# Test different models
# Edit .env file and run again
```

### Performance Testing
```bash
# Test with various audio files
for file in *.wav; do
    echo "Testing $file"
    python main_debug_no_ws.py "$file"
done
```

### Troubleshooting
```bash
# Isolate STT issues
# Check the STT section in output

# Isolate LLM issues  
# Check the LLM section in output

# Isolate TTS issues
# Check the TTS section in output
```

## 📝 Script Features

### ✅ What It Tests

- **Audio Processing**: Format conversion, normalization
- **STT Service**: Speech-to-text conversion
- **LLM Service**: AI response generation
- **TTS Service**: Text-to-speech synthesis
- **Full Pipeline**: End-to-end processing
- **Error Handling**: Graceful failure reporting
- **Performance Metrics**: Detailed latency tracking

### ✅ What It Outputs

- **Console Logs**: Detailed progress and results
- **Audio Files**: Generated speech output
- **Performance Data**: Latency breakdown
- **Error Reports**: Detailed failure information

### ✅ What It Validates

- **API Keys**: All required keys present and valid
- **Service Availability**: All AI services accessible
- **Audio Compatibility**: Audio format processing
- **Pipeline Integration**: Complete flow working

## 🚀 Next Steps

After successful debug testing:

1. **Start the main app**: `python -m uvicorn src.api.main:app --reload`
2. **Test WebSocket**: Open browser to `http://localhost:8000`
3. **Real-time testing**: Use the web interface for live voice chat

---

*Happy debugging! 🎤🤖* 