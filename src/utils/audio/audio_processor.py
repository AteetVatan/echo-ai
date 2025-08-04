"""
Audio processing utilities for EchoAI voice chat system.

This module handles audio format conversion, processing, and optimization
for optimal compatibility with STT services and low-latency streaming.
"""

import asyncio
import io
import wave
from typing import Optional
import numpy as np
from pydub import AudioSegment
from pydub.utils import make_chunks

from src.utils.logging import get_logger
from src.utils.config import get_settings


logger = get_logger(__name__)
settings = get_settings()


class AudioProcessor:
    """Handles audio processing and format conversion for STT compatibility."""
    
    def __init__(self):
        self.target_sample_rate = settings.SAMPLE_RATE
        self.target_channels = settings.CHANNELS
        self.target_format = settings.AUDIO_FORMAT
        
    async def process_audio_for_stt(self, audio_data: bytes, input_format: str = "webm") -> bytes:
        """
        Process audio data for optimal STT performance.
        
        Args:
            audio_data: Raw audio data
            input_format: Input audio format (webm, wav, mp3, etc.)
            
        Returns:
            Processed audio data in WAV format
        """
        try:
            # Load audio using pydub
            audio = AudioSegment.from_file(io.BytesIO(audio_data), format=input_format)
            
            # Convert to mono if needed
            if audio.channels != self.target_channels:
                audio = audio.set_channels(self.target_channels)
            
            # Resample if needed
            if audio.frame_rate != self.target_sample_rate:
                audio = audio.set_frame_rate(self.target_sample_rate)
            
            # Normalize audio levels
            audio = self._normalize_audio(audio)
            
            # Convert to WAV format
            output_buffer = io.BytesIO()
            audio.export(output_buffer, format="wav")
            output_buffer.seek(0)
            
            processed_audio = output_buffer.read()
            
            logger.debug(f"Audio processed: {len(audio_data)} -> {len(processed_audio)} bytes")
            
            return processed_audio
            
        except Exception as e:
            logger.error(f"Failed to process audio: {str(e)}")
            raise
    
    def _normalize_audio(self, audio: AudioSegment) -> AudioSegment:
        """
        Normalize audio levels for better STT performance.
        
        Args:
            audio: AudioSegment to normalize
            
        Returns:
            Normalized AudioSegment
        """
        try:
            # Normalize to -20dB target
            target_dBFS = -20
            change_in_dBFS = target_dBFS - audio.dBFS
            
            if change_in_dBFS != 0:
                audio = audio.apply_gain(change_in_dBFS)
            
            return audio
            
        except Exception as e:
            logger.warning(f"Audio normalization failed: {str(e)}")
            return audio
    
    def create_audio_chunks(self, audio_data: bytes, chunk_duration_ms: int = 1000) -> list:
        """
        Create audio chunks for streaming processing.
        
        Args:
            audio_data: Audio data in bytes
            chunk_duration_ms: Duration of each chunk in milliseconds
            
        Returns:
            List of audio chunk bytes
        """
        try:
            # Load audio
            audio = AudioSegment.from_wav(io.BytesIO(audio_data))
            
            # Create chunks
            chunks = make_chunks(audio, chunk_duration_ms)
            
            # Convert chunks to bytes
            chunk_bytes = []
            for chunk in chunks:
                buffer = io.BytesIO()
                chunk.export(buffer, format="wav")
                buffer.seek(0)
                chunk_bytes.append(buffer.read())
            
            logger.debug(f"Created {len(chunk_bytes)} audio chunks of {chunk_duration_ms}ms each")
            
            return chunk_bytes
            
        except Exception as e:
            logger.error(f"Failed to create audio chunks: {str(e)}")
            return [audio_data]  # Return original as single chunk
    
    def combine_audio_chunks(self, audio_chunks: list) -> bytes:
        """
        Combine audio chunks back into a single audio file.
        
        Args:
            audio_chunks: List of audio chunk bytes
            
        Returns:
            Combined audio data
        """
        try:
            if not audio_chunks:
                return b""
            
            if len(audio_chunks) == 1:
                return audio_chunks[0]
            
            # Load first chunk
            combined_audio = AudioSegment.from_wav(io.BytesIO(audio_chunks[0]))
            
            # Append remaining chunks
            for chunk_bytes in audio_chunks[1:]:
                chunk_audio = AudioSegment.from_wav(io.BytesIO(chunk_bytes))
                combined_audio += chunk_audio
            
            # Export combined audio
            output_buffer = io.BytesIO()
            combined_audio.export(output_buffer, format="wav")
            output_buffer.seek(0)
            
            logger.debug(f"Combined {len(audio_chunks)} chunks into single audio")
            
            return output_buffer.read()
            
        except Exception as e:
            logger.error(f"Failed to combine audio chunks: {str(e)}")
            raise
    
    def detect_silence(self, audio_data: bytes, silence_threshold: int = -40, min_silence_len: int = 1000) -> bool:
        """
        Detect if audio contains mostly silence.
        
        Args:
            audio_data: Audio data in bytes
            silence_threshold: dB threshold for silence detection
            min_silence_len: Minimum silence length in milliseconds
            
        Returns:
            True if audio is mostly silence
        """
        try:
            audio = AudioSegment.from_wav(io.BytesIO(audio_data))
            
            # Find silent parts
            silent_ranges = detect_nonsilent(
                audio,
                min_silence_len=min_silence_len,
                silence_thresh=silence_threshold
            )
            
            # Calculate total non-silent duration
            total_non_silent = sum(end - start for start, end in silent_ranges)
            total_duration = len(audio)
            
            # Check if mostly silence
            silence_ratio = 1 - (total_non_silent / total_duration)
            
            return silence_ratio > 0.8  # 80% silence threshold
            
        except Exception as e:
            logger.warning(f"Silence detection failed: {str(e)}")
            return False
    
    def trim_silence(self, audio_data: bytes, silence_threshold: int = -40) -> bytes:
        """
        Trim silence from beginning and end of audio.
        
        Args:
            audio_data: Audio data in bytes
            silence_threshold: dB threshold for silence detection
            
        Returns:
            Trimmed audio data
        """
        try:
            audio = AudioSegment.from_wav(io.BytesIO(audio_data))
            
            # Trim silence
            trimmed_audio = audio.strip_silence(silence_thresh=silence_threshold)
            
            # Export trimmed audio
            output_buffer = io.BytesIO()
            trimmed_audio.export(output_buffer, format="wav")
            output_buffer.seek(0)
            
            logger.debug(f"Audio trimmed: {len(audio_data)} -> {len(output_buffer.getvalue())} bytes")
            
            return output_buffer.read()
            
        except Exception as e:
            logger.warning(f"Silence trimming failed: {str(e)}")
            return audio_data  # Return original if trimming fails
    
    def get_audio_info(self, audio_data: bytes) -> dict:
        """
        Get information about audio data.
        
        Args:
            audio_data: Audio data in bytes
            
        Returns:
            Dict with audio information
        """
        try:
            audio = AudioSegment.from_wav(io.BytesIO(audio_data))
            
            return {
                "duration_ms": len(audio),
                "sample_rate": audio.frame_rate,
                "channels": audio.channels,
                "sample_width": audio.sample_width,
                "dBFS": audio.dBFS,
                "max_dBFS": audio.max_dBFS,
                "rms": audio.rms
            }
            
        except Exception as e:
            logger.error(f"Failed to get audio info: {str(e)}")
            return {}
    
    def create_test_audio(self, duration_ms: int = 1000, frequency: int = 440) -> bytes:
        """
        Create test audio for model warm-up.
        
        Args:
            duration_ms: Duration in milliseconds
            frequency: Frequency in Hz
            
        Returns:
            Test audio data
        """
        try:
            # Generate sine wave
            sample_rate = self.target_sample_rate
            samples = int(sample_rate * duration_ms / 1000)
            
            # Create sine wave
            t = np.linspace(0, duration_ms / 1000, samples, False)
            sine_wave = np.sin(2 * np.pi * frequency * t)
            
            # Convert to 16-bit PCM
            audio_data = (sine_wave * 32767).astype(np.int16)
            
            # Create WAV file
            output_buffer = io.BytesIO()
            with wave.open(output_buffer, 'wb') as wav_file:
                wav_file.setnchannels(self.target_channels)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data.tobytes())
            
            output_buffer.seek(0)
            return output_buffer.read()
            
        except Exception as e:
            logger.error(f"Failed to create test audio: {str(e)}")
            raise


# Import detect_nonsilent function
try:
    from pydub.silence import detect_nonsilent
except ImportError:
    # Fallback implementation if pydub.silence is not available
    def detect_nonsilent(audio, min_silence_len=1000, silence_thresh=-40):
        """Simple silence detection fallback."""
        # This is a simplified implementation
        # In production, use pydub.silence.detect_nonsilent
        return [(0, len(audio))]


# Global audio processor instance
audio_processor = AudioProcessor()