"""
Text-to-Speech service for EchoAI voice chat system.

This module provides TTS functionality using ElevenLabs API with streaming
support and caching for optimal performance.
"""

import asyncio
import time
import hashlib
from typing import Dict, Any, List, Optional, Generator, AsyncGenerator
import aiohttp
from asyncio import Semaphore
import random

from src.utils import get_settings
from src.utils import get_logger, log_performance, log_error_with_context
from src.utils.audio import stream_processor
from src.db import DBOperations

logger = get_logger(__name__)
settings = get_settings()


class TTSService:
    """Text-to-Speech service with streaming and caching support."""
    
    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY
        self.voice_id = settings.ELEVENLABS_VOICE_ID
        self.model_id = settings.ELEVENLABS_MODEL_ID
        self.base_url = settings.ELEVENLABS_API_BASE
        
        self.db = DBOperations()
        
        self.cache = {}
        self.cache_enabled = settings.TTS_CACHE_ENABLED
        
        self.streaming_enabled = settings.TTS_STREAMING
        self.semaphore = asyncio.Semaphore(5)
        
        # Performance tracking
        self.performance_stats = {
            "total_syntheses": 0,
            "successful_syntheses": 0,
            "failed_syntheses": 0,
            "cache_hits": 0,
            "avg_latency": 0.0,
            "latencies": []
        }
        
    def _init_audio_cache(self):
        """Initialize audio cache from database."""
        try:
            cache = self.db.load_all_audio(self.voice_id)
            for cache_key, audio_data in cache.items():
                self.cache[cache_key] = audio_data
            logger.info(f"Loaded {len(cache)} audio entries from database")
            return cache
        except Exception as e:
            logger.error(f"Failed to initialize audio cache: {str(e)}")
            return {}
        
    
    def _get_cache_key(self, text: str, voice_id: str = None) -> str:
        """Generate cache key for text and voice combination."""
        voice = voice_id or self.voice_id
        text_hash = str(abs(hash(text)))
        return f"{voice}_{text_hash}"
    
    def _is_cached(self, text: str, voice_id: str = None) -> bool:
        """Check if text is cached."""
        if not self.cache_enabled:
            return False
        cache_key = self._get_cache_key(text, voice_id)
        return cache_key in self.cache
    
    def _get_cached_audio(self, text: str, voice_id: str = None) -> Optional[bytes]:
        """Get cached audio data."""
        if not self.cache_enabled:
            return None
        
        # First check in-memory cache
        cache_key = self._get_cache_key(text, voice_id)
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # If not in memory, try database
        voice = voice_id or self.voice_id
        try:
            audio_data = self.db.load_audio(text, voice)
            if audio_data:
                # Add to in-memory cache
                self.cache[cache_key] = audio_data
                return audio_data
        except Exception as e:
            logger.warning(f"Failed to load audio from database: {str(e)}")
        
        return None
    
    def _cache_audio(self, text: str, audio_data: bytes, voice_id: str = None) -> None:
        """Cache audio data."""
        if not self.cache_enabled:
            return
        cache_key = self._get_cache_key(text, voice_id)
        self.cache[cache_key] = audio_data
        
        # Limit cache size
        if len(self.cache) > 1000:
            # Remove oldest entries
            oldest_keys = list(self.cache.keys())[:100]
            for key in oldest_keys:
                del self.cache[key]
    
    @log_performance
    async def synthesize_speech(self, text: str, use_streaming: bool = True, voice_id: str = None) -> Dict[str, Any]:
        """
        Synthesize speech from text using ElevenLabs API.
        
        Args:
            text: Text to synthesize
            use_streaming: Whether to use streaming synthesis
            voice_id: Voice ID to use (optional)
            
        Returns:
            Dict with audio data and metadata
        """
        start_time = time.time()
        
        try:
            self.performance_stats["total_syntheses"] += 1
            
            # Check cache first
            cached_audio = self._get_cached_audio(text, voice_id)
            if cached_audio:
                self.performance_stats["cache_hits"] += 1
                latency = time.time() - start_time
                self._update_stats(latency, True)
                
                return {
                    "audio_data": cached_audio,
                    "model": "elevenlabs_cached",
                    "latency": latency,
                    "cached": True
                }
            
            # Choose synthesis method
            result = await self.synthesize_with_retry(text, voice_id, use_streaming=use_streaming)
            
            if "error" in result:
                self._update_stats(time.time() - start_time, False)
                return result
            
            # Cache the result
            self._cache_audio(text, result["audio_data"], voice_id)
            
            # Save to database
            try:
                voice = voice_id or self.voice_id
                self.db.save_audio(text, result["audio_data"], voice)
            except Exception as e:
                logger.warning(f"Failed to save audio to database: {str(e)}")
            
            self._update_stats(result["latency"], True)
            return result
            
        except Exception as e:
            latency = time.time() - start_time
            self._update_stats(latency, False)
            log_error_with_context(logger, e, {"method": "synthesize_speech", "text_length": len(text)})
            return {"error": f"Speech synthesis failed: {str(e)}"}
    
    async def _synthesize_streaming(self, text: str, voice_id: str = None) -> Dict[str, Any]:
        """Synthesize speech using streaming API."""
        start_time = time.time()
        
        try:
            voice = voice_id or self.voice_id
            url = f"{self.base_url}/text-to-speech/{voice}/stream"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            data = {
                "text": text,
                "model_id": self.model_id,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        audio_data = await response.read()
                        latency = time.time() - start_time
                        
                        logger.debug(f"Streaming synthesis completed in {latency:.3f}s")
                        
                        return {
                            "audio_data": audio_data,
                            "model": "elevenlabs_streaming",
                            "latency": latency,
                            "cached": False
                        }
                    else:
                        error_text = await response.text()
                        raise Exception(f"ElevenLabs API error: {response.status} - {error_text}")
                        
        except Exception as e:
            latency = time.time() - start_time
            log_error_with_context(logger, e, {"method": "_synthesize_streaming", "latency": latency})
            raise
    
    async def _synthesize_non_streaming(self, text: str, voice_id: str = None) -> Dict[str, Any]:
        """Synthesize speech using non-streaming API."""
        start_time = time.time()
        
        try:
            voice = voice_id or self.voice_id
            url = f"{self.base_url}/text-to-speech/{voice}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            data = {
                "text": text,
                "model_id": self.model_id,
                "voice_settings": {
                    "stability": 0.5, 
                    "similarity_boost": 0.5
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        audio_data = await response.read()
                        latency = time.time() - start_time
                        
                        logger.debug(f"Non-streaming synthesis completed in {latency:.3f}s")
                        
                        return {
                            "audio_data": audio_data,
                            "model": "elevenlabs_non_streaming",
                            "latency": latency,
                            "cached": False
                        }
                    else:
                        error_text = await response.text()
                        raise Exception(f"ElevenLabs API error: {response.status} - {error_text}")
                        
        except Exception as e:
            latency = time.time() - start_time
            log_error_with_context(logger, e, {"method": "_synthesize_non_streaming", "latency": latency})
            raise
    
    async def synthesize_streaming_chunks(self, text: str, voice_id: str = None) -> AsyncGenerator[bytes, None]:
        """
        Synthesize speech in streaming chunks for real-time playback.
        
        Args:
            text: Text to synthesize
            voice_id: Voice ID to use (optional)
            
        Yields:
            Audio chunks as bytes
        """
        try:
            # Split text into sentences for chunked processing
            sentences = self._split_into_sentences(text)
            
            for sentence in sentences:
                if not sentence.strip():
                    continue
                
                # Synthesize each sentence
                result = await self.synthesize_speech(sentence, use_streaming=True, voice_id=voice_id)
                
                if "error" in result:
                    logger.error(f"Failed to synthesize sentence: {result['error']}")
                    continue
                
                # Create audio chunks using AudioStreamProcessor
                audio_chunks = stream_processor.create_audio_chunks(result["audio_data"], chunk_size=1024)
                
                for chunk in audio_chunks:
                    yield chunk
                    
                # Small delay between sentences for natural flow
                await asyncio.sleep(0.1)
                
        except Exception as e:
            log_error_with_context(logger, e, {"method": "synthesize_streaming_chunks", "text_length": len(text)})
            raise
        


    async def synthesize_with_retry(self, text: str, voice_id: str = None, use_streaming: bool = False, retries: int = 3):
        """Synthesize speech with concurrency control and retries for rate-limit errors."""
        for attempt in range(retries):
            try:
                async with self.semaphore:  # Concurrency limit

                    if use_streaming and self.streaming_enabled:
                        result = await self._synthesize_streaming(text, voice_id)
                    else:
                        result = await self._synthesize_non_streaming(text, voice_id)

                    return result  #Success: return immediately

            except Exception as e:
                if "too_many_concurrent_requests" in str(e):
                    wait_time = 2 ** attempt + random.random()
                    logger.warning(f"[TTS] Concurrency limit hit. Retrying in {wait_time:.2f}s (Attempt {attempt+1}/{retries})")
                    await asyncio.sleep(wait_time)
                else:
                    raise  # Non-rate-limit error → propagate immediately

        raise Exception(f"[TTS] Failed after {retries} retries: Too many concurrent requests")

    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences for chunked synthesis."""
        import re
        
        # Simple sentence splitting (can be enhanced with NLP libraries)
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    async def warm_up_cache(self) -> None:
        """Warm up TTS cache with common phrases."""
        try:
            logger.info("Warming up TTS cache...")
            
            # Initialize database and load existing cache
            if self.cache_enabled:
                self.cache = self._init_audio_cache()
            
            common_phrases = [
                "Hello, how can I help you?",
                "I understand.",
                "That's interesting.",
                "Let me think about that.",
                "Thank you for sharing.",
                "I'm here to help.",
                "That's a great question.",
                "I appreciate your input."
            ]
            
            # Synthesize common phrases (synchronous for warm-up)
            for phrase in common_phrases:
                try:
                    # Use asyncio.run to run the async synthesis in sync context
                    result = await self.synthesize_speech(phrase, use_streaming=False, voice_id=self.voice_id)
                    
                    
                    if "error" in result:
                        logger.warning(f"Failed to synthesize phrase: {result['error']}")
                except Exception as e:
                    logger.warning(f"Failed to synthesize phrase '{phrase}': {str(e)}")
            
            logger.info(f"TTS cache warmed up with {len(common_phrases)} phrases")
            
        except Exception as e:
            logger.warning(f"Failed to warm up TTS cache: {str(e)}")
    
    def _update_stats(self, latency: float, success: bool) -> None:
        """Update performance statistics."""
        self.performance_stats["latencies"].append(latency)
        
        if success:
            self.performance_stats["successful_syntheses"] += 1
        else:
            self.performance_stats["failed_syntheses"] += 1
        
        # Keep only last 100 latencies
        if len(self.performance_stats["latencies"]) > 100:
            self.performance_stats["latencies"] = self.performance_stats["latencies"][-100:]
        
        # Update average latency
        if self.performance_stats["latencies"]:
            self.performance_stats["avg_latency"] = sum(self.performance_stats["latencies"]) / len(self.performance_stats["latencies"])
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            "total_syntheses": self.performance_stats["total_syntheses"],
            "successful_syntheses": self.performance_stats["successful_syntheses"],
            "failed_syntheses": self.performance_stats["failed_syntheses"],
            "cache_hits": self.performance_stats["cache_hits"],
            "avg_latency": self.performance_stats["avg_latency"],
            "cache_enabled": self.cache_enabled,
            "streaming_enabled": self.streaming_enabled,
            "cache_size": len(self.cache)
        }
    
    def clear_cache(self) -> None:
        """Clear TTS cache."""
        self.cache.clear()
        logger.info("TTS cache cleared")
    
    def cleanup(self) -> None:
        """Clean up database connections."""
        try:
            self.db.close()
            logger.info("TTS service cleanup completed")
        except Exception as e:
            logger.error(f"Failed to cleanup TTS service: {str(e)}")


# Global service instance
tts_service = TTSService() 