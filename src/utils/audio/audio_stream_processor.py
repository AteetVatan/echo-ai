import asyncio
from typing import Generator
from src.utils.logging import get_logger
from src.utils.config import get_settings



class AudioStreamProcessor:
    """Handles real-time audio streaming for WebSocket connections."""
    
    def __init__(self, chunk_size: int = 1024):
        self.logger = get_logger(__name__)
        self.settings = get_settings()
        self.chunk_size = chunk_size
    
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