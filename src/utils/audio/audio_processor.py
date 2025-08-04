import io
import wave
from typing import Generator, Optional
from pydub import AudioSegment
from pydub.utils import make_chunks

from src.utils.logging import log_performance, get_logger
from src.utils.config import get_settings


class AudioProcessor:
    """Handles audio processing and format conversion for optimal STT performance."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.settings = get_settings()
        self.sample_rate = self.settings.sample_rate
        self.channels = self.settings.channels
        self.chunk_duration = self.settings.stt_chunk_duration

    
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
            
            self.logger.info(f"Converted WebM to WAV: {len(webm_audio)} bytes -> {len(wav_buffer.getvalue())} bytes")
            return wav_buffer.getvalue()
            
        except Exception as e:
            self.logger.error(f"Failed to convert WebM to WAV: {str(e)}")
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
                
                self.logger.debug(f"Created audio chunk {i+1}: {len(chunk_buffer.getvalue())} bytes")
                yield chunk_buffer.getvalue()
                
        except Exception as e:
            self.logger.error(f"Failed to chunk audio: {str(e)}")
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
            
            self.logger.debug(f"Normalized audio: {len(audio_data)} bytes -> {len(normalized_buffer.getvalue())} bytes")
            return normalized_buffer.getvalue()
            
        except Exception as e:
            self.logger.error(f"Failed to normalize audio: {str(e)}")
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
            self.logger.error(f"Failed to get audio info: {str(e)}")
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
            
            self.logger.info(f"Processed audio for STT: {len(audio_data)} bytes")
            return audio_data
            
        except Exception as e:
            self.logger.error(f"Failed to process audio for STT: {str(e)}")
            raise