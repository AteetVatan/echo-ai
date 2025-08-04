"""
Audio processing utilities for EchoAI voice chat system.

This module handles audio format conversion, chunking, and processing
for optimal compatibility with STT services and low-latency streaming.
"""

from .audio_processor import AudioProcessor
from .audio_stream_processor import AudioStreamProcessor

# Global instances
audio_processor = AudioProcessor()
stream_processor = AudioStreamProcessor() 