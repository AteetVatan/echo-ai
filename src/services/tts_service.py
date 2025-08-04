"""
Text-to-Speech (TTS) service for EchoAI voice chat system.

This module provides TTS functionality using ElevenLabs for low-latency
streaming voice cloning with caching for common phrases.
"""

import asyncio
import time
import hashlib
from typing import Optional, Dict, Any, Generator
import aiohttp
from src.utils.config import get_settings
from src.utils.logging import get_logger, log_performance, log_error_with_context


logger = get_logger(__name__)
settings = get_settings()


class TTSService:
    """Handles Text-to-Speech conversion with ElevenLabs streaming."""
    
    def __init__(self):
        self.elevenlabs_api_key = settings.elevenlabs_api_key
        self.voice_id = settings.default_tts_voice_id
        self.streaming = settings.tts_streaming
        self.cache_responses = settings.cache_tts_responses
        self.timeout = settings.tts_timeout
        
        # Performance monitoring
        self.latency = []
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Response cache
        self.response_cache: Dict[str, bytes] = {}
        self.max_cache_size = 100
        
        # Common phrases cache
        self._init_common_phrases_cache()
    
    def _init_common_phrases_cache(self) -> None:
        """Initialize cache with common phrases for faster response."""
        common_phrases = [
            "Hello, how can I help you?",
            "I understand.",
            "That's interesting.",
            "Let me think about that.",
            "I'm here to help.",
            "Thank you for sharing that.",
            "I appreciate your question.",
            "That's a good point.",
            "I see what you mean.",
            "Let me clarify that."
        ]
        
        for phrase in common_phrases:
            cache_key = self._get_cache_key(phrase)
            # We'll populate these with actual audio when first requested
            self.response_cache[cache_key] = b""  # Placeholder
    
    def _get_cache_key(self, text: str) -> str:
        """
        Generate cache key for text.
        
        Args:
            text: Input text
            
        Returns:
            str: Cache key
        """
        # Create hash of text + voice_id for unique cache keys
        cache_string = f"{text.lower().strip()}:{self.voice_id}"
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def _is_cached(self, text: str) -> bool:
        """
        Check if text is cached.
        
        Args:
            text: Input text
            
        Returns:
            bool: True if cached
        """
        cache_key = self._get_cache_key(text)
        return cache_key in self.response_cache and self.response_cache[cache_key]
    
    def _get_cached_audio(self, text: str) -> Optional[bytes]:
        """
        Get cached audio for text.
        
        Args:
            text: Input text
            
        Returns:
            Optional[bytes]: Cached audio or None
        """
        cache_key = self._get_cache_key(text)
        return self.response_cache.get(cache_key)
    
    def _cache_audio(self, text: str, audio_data: bytes) -> None:
        """
        Cache audio for text.
        
        Args:
            text: Input text
            audio_data: Audio bytes
        """
        cache_key = self._get_cache_key(text)
        
        # Manage cache size
        if len(self.response_cache) >= self.max_cache_size:
            # Remove oldest entries (simple FIFO)
            oldest_key = next(iter(self.response_cache))
            del self.response_cache[oldest_key]
        
        self.response_cache[cache_key] = audio_data
        logger.debug(f"Cached audio for text: '{text[:30]}...'")
    
    @log_performance
    async def synthesize_speech(self, text: str, use_streaming: bool = None) -> Dict[str, Any]:
        """
        Synthesize speech from text using ElevenLabs.
        
        Args:
            text: Text to synthesize
            use_streaming: Override streaming setting
            
        Returns:
            Dict containing audio data and metadata
        """
        if use_streaming is None:
            use_streaming = self.streaming
        
        start_time = time.time()
        
        try:
            # Check cache first
            if self.cache_responses and self._is_cached(text):
                cached_audio = self._get_cached_audio(text)
                if cached_audio:
                    latency = time.time() - start_time
                    self.latency.append(latency)
                    self.cache_hits += 1
                    
                    logger.info(f"TTS cache hit in {latency:.3f}s: '{text[:30]}...'")
                    
                    return {
                        "audio_data": cached_audio,
                        "model": "elevenlabs_cached",
                        "latency": latency,
                        "cached": True
                    }
            
            # Synthesize new audio
            if use_streaming:
                audio_data = await self._synthesize_streaming(text)
            else:
                audio_data = await self._synthesize_non_streaming(text)
            
            latency = time.time() - start_time
            self.latency.append(latency)
            self.cache_misses += 1
            
            # Cache the result
            if self.cache_responses:
                self._cache_audio(text, audio_data)
            
            logger.info(f"TTS completed in {latency:.3f}s: '{text[:30]}...'")
            
            return {
                "audio_data": audio_data,
                "model": "elevenlabs",
                "latency": latency,
                "cached": False
            }
            
        except Exception as e:
            latency = time.time() - start_time
            log_error_with_context(logger, e, {"text_length": len(text), "latency": latency})
            raise
    
    async def _synthesize_streaming(self, text: str) -> bytes:
        """
        Synthesize speech using ElevenLabs streaming API.
        
        Args:
            text: Text to synthesize
            
        Returns:
            bytes: Audio data
        """
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.elevenlabs_api_key
            }
            
            payload = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    
                    if response.status == 200:
                        audio_data = await response.read()
                        return audio_data
                    else:
                        error_text = await response.text()
                        raise Exception(f"ElevenLabs API error {response.status}: {error_text}")
                        
        except Exception as e:
            logger.error(f"Streaming TTS failed: {str(e)}")
            raise
    
    async def _synthesize_non_streaming(self, text: str) -> bytes:
        """
        Synthesize speech using ElevenLabs non-streaming API.
        
        Args:
            text: Text to synthesize
            
        Returns:
            bytes: Audio data
        """
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.elevenlabs_api_key
            }
            
            payload = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    
                    if response.status == 200:
                        audio_data = await response.read()
                        return audio_data
                    else:
                        error_text = await response.text()
                        raise Exception(f"ElevenLabs API error {response.status}: {error_text}")
                        
        except Exception as e:
            logger.error(f"Non-streaming TTS failed: {str(e)}")
            raise
    
    async def synthesize_streaming_chunks(self, text: str) -> Generator[bytes, None, None]:
        """
        Synthesize speech in streaming chunks for real-time playback.
        
        Args:
            text: Text to synthesize
            
        Yields:
            bytes: Audio chunks
        """
        try:
            # Split text into sentences for chunked synthesis
            sentences = self._split_into_sentences(text)
            
            for sentence in sentences:
                if sentence.strip():
                    audio_data = await self._synthesize_streaming(sentence.strip())
                    yield audio_data
                    
                    # Small delay between chunks for natural flow
                    await asyncio.sleep(0.1)
                    
        except Exception as e:
            logger.error(f"Streaming TTS chunks failed: {str(e)}")
            raise
    
    def _split_into_sentences(self, text: str) -> list:
        """
        Split text into sentences for chunked synthesis.
        
        Args:
            text: Input text
            
        Returns:
            list: List of sentences
        """
        import re
        
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    async def warm_up_cache(self) -> None:
        """Pre-populate cache with common phrases."""
        try:
            logger.info("Warming up TTS cache with common phrases...")
            
            common_phrases = [
                "Hello, how can I help you?",
                "I understand.",
                "That's interesting.",
                "Let me think about that.",
                "I'm here to help."
            ]
            
            for phrase in common_phrases:
                try:
                    await self.synthesize_speech(phrase)
                    logger.debug(f"Cached phrase: '{phrase}'")
                except Exception as e:
                    logger.warning(f"Failed to cache phrase '{phrase}': {str(e)}")
            
            logger.info("TTS cache warm-up completed")
            
        except Exception as e:
            logger.warning(f"Failed to warm up TTS cache: {str(e)}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for monitoring.
        
        Returns:
            Dict with performance metrics
        """
        return {
            "average_latency": sum(self.latency) / len(self.latency) if self.latency else 0,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0,
            "total_synthesis": len(self.latency),
            "cache_size": len(self.response_cache)
        }
    
    def clear_cache(self) -> None:
        """Clear the TTS response cache."""
        self.response_cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        logger.info("TTS cache cleared")


# Global TTS service instance
tts_service = TTSService() 