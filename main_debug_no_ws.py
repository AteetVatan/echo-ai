#!/usr/bin/env python3
"""
EchoAI Debug Script - Process audio file without WebSocket

This script allows you to quickly test the AI pipeline by processing
a sample audio file through STT → LLM → TTS without WebSocket connections.

Usage:
    python main_debug_no_ws.py [audio_file_path]

Examples:
    python main_debug_no_ws.py                    # Uses generated test audio
    python main_debug_no_ws.py sample_audio.wav   # Uses your audio file
    python main_debug_no_ws.py test.mp3          # Supports various audio formats

Features:
    Tests individual components (STT, LLM, TTS)
    Tests complete pipeline
    Saves generated audio output
    Detailed latency breakdown
    Comprehensive error reporting
    No WebSocket dependencies

Requirements:
    - Valid API keys in .env file
    - Python 3.12+
    - All dependencies installed
"""

import asyncio
import sys
import os
import time
import base64
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.agents.voice_clone_agent import voice_clone_agent
from src.utils import get_settings, setup_logging, get_logger
from src.utils.audio.audio_utils import audio_processor


def create_test_audio() -> bytes:
    """Create a simple test audio file for debugging."""
    try:
        # Create a simple sine wave audio for testing
        import numpy as np
        import io
        import wave
        
        # Generate a 1-second sine wave at 440 Hz
        sample_rate = 16000
        duration = 1.0
        frequency = 440.0
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * frequency * t)
        
        # Convert to 16-bit PCM
        audio_data = (audio_data * 32767).astype(np.int16)
        
        # Create WAV file in memory
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        return buffer.getvalue()
        
    except ImportError:
        # Fallback: create a minimal audio file
        logger.warning("numpy not available, creating minimal test audio")
        return b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"


async def load_audio_file(file_path: str) -> bytes:
    """Load audio file from disk."""
    try:
        with open(file_path, 'rb') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Audio file not found: {file_path}")
        return None
    except Exception as e:
        logger.error(f"Error loading audio file: {str(e)}")
        return None


async def debug_stt_only(audio_data: bytes) -> dict:
    """Debug STT service only."""
    logger.info("Testing STT Service...")
    
    try:
        # Process audio for STT
        processed_audio = await audio_processor.process_audio_for_stt(audio_data)
        logger.info(f"Audio processed: {len(processed_audio)} bytes")
        
        # Test STT
        from src.services.stt_service import stt_service
        start_time = time.time()
        
        result = await stt_service.transcribe_audio(processed_audio)
        
        latency = time.time() - start_time
        logger.info(f"STT completed in {latency:.2f}s")
        logger.info(f"Transcription: {result.get('text', 'No text')}")
        logger.info(f"Model used: {result.get('model_used', 'Unknown')}")
        
        return result
        
    except Exception as e:
        logger.error(f" STT failed: {str(e)}")
        return {"error": str(e)}


async def debug_llm_only(text: str) -> dict:
    """Debug LLM service only."""
    logger.info("Testing LLM Service...")
    
    try:
        from src.services.llm_service import llm_service
        
        start_time = time.time()
        result = await llm_service.generate_response(text)
        
        latency = time.time() - start_time
        logger.info(f" LLM completed in {latency:.2f}s")
        logger.info(f" Response: {result.get('text', 'No response')}")
        logger.info(f" Model used: {result.get('model', 'Unknown')}")
        
        return result
        
    except Exception as e:
        logger.error(f" LLM failed: {str(e)}")
        return {"error": str(e)}


async def debug_tts_only(text: str) -> dict:
    """Debug TTS service only."""
    logger.info("🔊 Testing TTS Service...")
    
    try:
        from src.services.tts_service import tts_service
        
        start_time = time.time()
        result = await tts_service.synthesize_speech(text)
        
        latency = time.time() - start_time
        logger.info(f" TTS completed in {latency:.2f}s")
        logger.info(f" Audio generated: {len(result.get('audio_data', b''))} bytes")
        logger.info(f" Model used: {result.get('model', 'Unknown')}")
        
        return result
        
    except Exception as e:
        logger.error(f" TTS failed: {str(e)}")
        return {"error": str(e)}


async def debug_full_pipeline(audio_data: bytes) -> dict:
    """Debug the complete AI pipeline."""
    logger.info("Testing Complete AI Pipeline...")
    
    try:
        start_time = time.time()
        
        # Process through agent
        result = await voice_clone_agent.process_voice_input(audio_data)
        
        total_latency = time.time() - start_time
        
        if "error" in result:
            logger.error(f"Pipeline failed: {result['error']}")
            return result
        
        logger.info(f" Full pipeline completed in {total_latency:.2f}s")
        logger.info(f" Transcription: {result.get('transcription', 'No text')}")
        logger.info(f" Response: {result.get('response_text', 'No response')}")
        logger.info(f" Audio generated: {len(result.get('audio_data', b''))} bytes")
        logger.info(f" Latency breakdown:")
        logger.info(f" - STT: {result.get('stt_latency', 0):.2f}s")
        logger.info(f" - LLM: {result.get('llm_latency', 0):.2f}s")
        logger.info(f" - TTS: {result.get('tts_latency', 0):.2f}s")
        logger.info(f" - Total: {result.get('pipeline_latency', total_latency):.2f}s")
        
        return result
        
    except Exception as e:
        logger.error(f" Full pipeline failed: {str(e)}")
        return {"error": str(e)}


async def save_audio_output(audio_data: bytes, output_path: str = "debug_output.wav"):
    """Save generated audio to file."""
    try:
        with open(output_path, 'wb') as f:
            f.write(audio_data)
        logger.info(f" Audio saved to: {output_path}")
        return True
    except Exception as e:
        logger.error(f" Failed to save audio: {str(e)}")
        return False


async def main():
    """Main debug function."""
    # Setup logging
    setup_logging()
    global logger
    logger = get_logger(__name__)
    
    # Get settings
    settings = get_settings()
    
    logger.info(" EchoAI Debug Script Starting...")
    logger.info("=" * 50)
    
    # Parse command line arguments
    # create os path
    audio_file_path = os.path.join(os.path.dirname(__file__), 'audio_cache', 'DTspCYcPUEd8ZsrSm2qm_4788221984486102553.mp3')
    # audio_cache/DTspCYcPUEd8ZsrSm2qm_4788221984486102553.wav
    logger.info(f" Using audio file: {audio_file_path}")
    
    
    if len(sys.argv) > 1:
        audio_file_path = sys.argv[1]
        logger.info(f" Using audio file: {audio_file_path}")
    else:
        logger.info(" No audio file provided, creating test audio")
    
    # Load or create audio data
    if audio_file_path:
        audio_data = await load_audio_file(audio_file_path)
        if not audio_data:
            logger.error(" Failed to load audio file, exiting")
            return
    else:
        audio_data = create_test_audio()
        logger.info(" Test audio created")
    
    logger.info(f" Audio data size: {len(audio_data)} bytes")
    
    # Validate API keys
    from src.utils import validate_api_keys
    if not validate_api_keys():
        logger.warning(" Some API keys are missing or invalid")
        logger.info("Please check your .env file")
    
    # Warm up services
    logger.info(" Warming up AI services...")
    try:
        await voice_clone_agent.warm_up_services()
        logger.info(" Services warmed up successfully")
    except Exception as e:
        logger.error(f" Failed to warm up services: {str(e)}")
        return
    
    logger.info("=" * 50)
    
    # Test individual components
    logger.info(" Testing Individual Components...")
    
    # Test STT
    stt_result = await debug_stt_only(audio_data)
    if "error" in stt_result:
        logger.error(" STT test failed, stopping")
        return
    
    transcription = stt_result.get("text", "")
    if not transcription:
        logger.warning(" No transcription generated, using test text")
        transcription = "Hello, this is a test message for debugging."
    
    logger.info("-" * 30)
    
    # Test LLM
    llm_result = await debug_llm_only(transcription)
    if "error" in llm_result:
        logger.error("LLM test failed, stopping")
        return
    
    response_text = llm_result.get("text", "")
    if not response_text:
        logger.warning(" No response generated")
        response_text = "I received your message but couldn't generate a proper response."
    
    logger.info("-" * 30)
    
    # Test TTS
    tts_result = await debug_tts_only(response_text)
    if "error" in tts_result:
        logger.error("TTS test failed")
    else:
        # Save audio output
        await save_audio_output(tts_result.get("audio_data", b""))
    
    logger.info("=" * 50)
    
    # Test full pipeline
    logger.info("Testing Complete Pipeline...")
    pipeline_result = await debug_full_pipeline(audio_data)
    
    if "error" not in pipeline_result:
        # Save final audio output
        await save_audio_output(pipeline_result.get("audio_data", b""), "pipeline_output.wav")
    
    logger.info("=" * 50)
    logger.info("Debug session completed!")
    
    # Print summary
    logger.info(" Summary:")
    logger.info(f"   - Audio processed: {len(audio_data)} bytes")
    logger.info(f"   - Transcription: {transcription}")
    logger.info(f"   - Response: {response_text}")
    if "error" not in pipeline_result:
        logger.info(f"   - Total pipeline time: {pipeline_result.get('pipeline_latency', 0):.2f}s")
    
    logger.info("🎉 Debug script finished successfully!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n Debug script interrupted by user")
    except Exception as e:
        print(f" Fatal error: {str(e)}")
        sys.exit(1) 