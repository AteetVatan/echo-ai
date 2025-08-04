"""
Audio processing utilities for EchoAI voice chat system.

This module handles audio format conversion, chunking, and processing
for optimal compatibility with STT services and low-latency streaming.
"""

import io
import wave
import asyncio
from typing import Optional, Tuple, Generator
import numpy as np
from pydub import AudioSegment
from pydub.utils import make_chunks
from src.utils.config import get_settings
from src.utils.logging import get_logger, log_performance


logger = get_logger(__name__)
settings = get_settings()


class AudioProcessor:
    """Handles audio processing and format conversion for optimal STT performance."""
    
    def __init__(self):
        self.sample_rate = settings.sample_rate
        self.channels = settings.channels
        self.chunk_duration = settings.stt_chunk_duration
    
    @log_performance
    async def convert_webm_to_wav(self, webm_audio: bytes) -> bytes:
        """
        Convert WebM audio to WAV format for STT compatibility.
        
        Args:
            webm_audio: Raw WebM audio bytes
            
        Returns:
            bytes: WAV format audio bytes
        """
        try:
            # Load WebM audio
            audio = AudioSegment.from_file(io.BytesIO(webm_audio), format="webm")
            
            # Convert to mono and set sample rate
            audio = audio.set_channels(self.channels)
            audio = audio.set_frame_rate(self.sample_rate)
            
            # Export as WAV
            wav_buffer = io.BytesIO()
            audio.export(wav_buffer, format="wav")
            wav_buffer.seek(0)
            
            logger.info(f"Converted WebM to WAV: {len(webm_audio)} bytes -> {len(wav_buffer.getvalue())} bytes")
            return wav_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to convert WebM to WAV: {str(e)}")
            raise
    
    @log_performance
    def chunk_audio(self, audio_data: bytes, chunk_duration_ms: Optional[int] = None) -> Generator[bytes, None, None]:
        """
        Split audio into chunks for faster STT processing.
        
        Args:
            audio_data: Raw audio bytes
            chunk_duration_ms: Duration of each chunk in milliseconds
            
        Yields:
            bytes: Audio chunk bytes
        """
        if chunk_duration_ms is None:
            chunk_duration_ms = int(self.chunk_duration * 1000)
        
        try:
            # Load audio
            audio = AudioSegment.from_wav(io.BytesIO(audio_data))
            
            # Create chunks
            chunks = make_chunks(audio, chunk_duration_ms)
            
            for i, chunk in enumerate(chunks):
                # Export chunk to bytes
                chunk_buffer = io.BytesIO()
                chunk.export(chunk_buffer, format="wav")
                chunk_buffer.seek(0)
                
                logger.debug(f"Created audio chunk {i+1}: {len(chunk_buffer.getvalue())} bytes")
                yield chunk_buffer.getvalue()
                
        except Exception as e:
            logger.error(f"Failed to chunk audio: {str(e)}")
            raise
    
    @log_performance
    def normalize_audio(self, audio_data: bytes) -> bytes:
        """
        Normalize audio levels for better STT accuracy.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            bytes: Normalized audio bytes
        """
        try:
            # Load audio
            audio = AudioSegment.from_wav(io.BytesIO(audio_data))
            
            # Normalize audio levels
            normalized_audio = audio.normalize()
            
            # Export normalized audio
            normalized_buffer = io.BytesIO()
            normalized_audio.export(normalized_buffer, format="wav")
            normalized_buffer.seek(0)
            
            logger.debug(f"Normalized audio: {len(audio_data)} bytes -> {len(normalized_buffer.getvalue())} bytes")
            return normalized_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to normalize audio: {str(e)}")
            raise
    
    @log_performance
    def get_audio_info(self, audio_data: bytes) -> dict:
        """
        Get audio file information.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            dict: Audio information including duration, sample rate, channels
        """
        try:
            with wave.open(io.BytesIO(audio_data), 'rb') as wav_file:
                frames = wav_file.getnframes()
                sample_rate = wav_file.getframerate()
                duration = frames / sample_rate
                channels = wav_file.getnchannels()
                
                return {
                    'duration': duration,
                    'sample_rate': sample_rate,
                    'channels': channels,
                    'frames': frames,
                    'size_bytes': len(audio_data)
                }
        except Exception as e:
            logger.error(f"Failed to get audio info: {str(e)}")
            raise
    
    @log_performance
    async def process_audio_for_stt(self, audio_data: bytes, format: str = "webm") -> bytes:
        """
        Process audio for optimal STT performance.
        
        Args:
            audio_data: Raw audio bytes
            format: Input audio format
            
        Returns:
            bytes: Processed audio bytes ready for STT
        """
        try:
            # Convert format if needed
            if format.lower() == "webm":
                audio_data = await self.convert_webm_to_wav(audio_data)
            
            # Normalize audio
            audio_data = self.normalize_audio(audio_data)
            
            logger.info(f"Processed audio for STT: {len(audio_data)} bytes")
            return audio_data
            
        except Exception as e:
            logger.error(f"Failed to process audio for STT: {str(e)}")
            raise


class AudioStreamProcessor:
    """Handles real-time audio streaming for WebSocket connections."""
    
    def __init__(self, chunk_size: int = 1024):
        self.chunk_size = chunk_size
        self.logger = get_logger(f"{__name__}.AudioStreamProcessor")
    
    async def process_audio_stream(self, audio_stream: asyncio.StreamReader) -> Generator[bytes, None, None]:
        """
        Process incoming audio stream in real-time.
        
        Args:
            audio_stream: Async stream reader for audio data
            
        Yields:
            bytes: Processed audio chunks
        """
        try:
            while True:
                chunk = await audio_stream.read(self.chunk_size)
                if not chunk:
                    break
                
                self.logger.debug(f"Processed audio chunk: {len(chunk)} bytes")
                yield chunk
                
        except Exception as e:
            self.logger.error(f"Error processing audio stream: {str(e)}")
            raise
    
    def create_audio_chunks(self, audio_data: bytes, chunk_size: int = 1024) -> Generator[bytes, None, None]:
        """
        Create fixed-size chunks from audio data.
        
        Args:
            audio_data: Raw audio bytes
            chunk_size: Size of each chunk in bytes
            
        Yields:
            bytes: Audio chunks
        """
        for i in range(0, len(audio_data), chunk_size):
            yield audio_data[i:i + chunk_size]


# Global instances
audio_processor = AudioProcessor()
stream_processor = AudioStreamProcessor() 