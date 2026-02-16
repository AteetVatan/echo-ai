"""
Text-to-Speech service for EchoAI voice chat system.

This module provides TTS functionality using Microsoft Edge neural TTS
(via edge-tts) with streaming support and caching for optimal performance.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, AsyncGenerator
import edge_tts

from src.utils import get_settings
from src.utils import get_logger, log_performance, log_error_with_context
from src.utils.audio import audio_stream_processor
from src.db import DBOperations

logger = get_logger(__name__)
settings = get_settings()


class TTSService:
    """Text-to-Speech service with streaming and caching support."""
    
    def __init__(self):
        self.voice = settings.EDGE_TTS_VOICE
        
        self.db = DBOperations()
        
        self.cache = {}
        self.cache_enabled = settings.TTS_CACHE_ENABLED
        
        self.streaming_enabled = settings.TTS_STREAMING
        
        # Performance tracking
        self.performance_stats = {
            "total_syntheses": 0,
            "successful_syntheses": 0,
            "failed_syntheses": 0,
            "cache_hits": 0,
            "avg_latency": 0.0,
            "latencies": []
        }
        
    def _init_audio_cache(self) -> Dict[str, bytes]:
        """Load audio cache from database and return it."""
        try:
            cache = self.db.load_all_audio(self.voice)
            logger.info(f"Loaded {len(cache)} audio entries from database")
            return cache
        except Exception as e:
            logger.error(f"Failed to initialize audio cache: {str(e)}")
            return {}
        
    
    def _get_cache_key(self, text: str, voice: str = None) -> str:
        """Generate cache key for text and voice combination."""
        v = voice or self.voice
        text_hash = str(abs(hash(text)))
        return f"{v}_{text_hash}"
    
    def _is_cached(self, text: str, voice: str = None) -> bool:
        """Check if text is cached."""
        if not self.cache_enabled:
            return False
        cache_key = self._get_cache_key(text, voice)
        return cache_key in self.cache
    
    def _get_cached_audio(self, text: str, voice: str = None) -> Optional[bytes]:
        """Get cached audio data."""
        if not self.cache_enabled:
            return None
        
        # First check in-memory cache
        cache_key = self._get_cache_key(text, voice)
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # If not in memory, try database
        v = voice or self.voice
        try:
            audio_data = self.db.load_audio(text, v)
            if audio_data:
                # Add to in-memory cache
                self.cache[cache_key] = audio_data
                return audio_data
        except Exception as e:
            logger.warning(f"Failed to load audio from database: {str(e)}")
        
        return None
    
    def _cache_audio(self, text: str, audio_data: bytes, voice: str = None) -> None:
        """Cache audio data."""
        if not self.cache_enabled:
            return
        cache_key = self._get_cache_key(text, voice)
        self.cache[cache_key] = audio_data
        
        # Limit cache size
        if len(self.cache) > 1000:
            # Remove oldest entries
            oldest_keys = list(self.cache.keys())[:100]
            for key in oldest_keys:
                del self.cache[key]
    
    @log_performance
    async def synthesize_speech(self, text: str, use_streaming: bool = True, voice: str = None) -> Dict[str, Any]:
        """
        Synthesize speech from text using Edge-TTS.
        
        Args:
            text: Text to synthesize
            use_streaming: Whether to use streaming synthesis
            voice: Voice name to use (optional, e.g. "en-IN-PrabhatNeural")
            
        Returns:
            Dict with audio data and metadata
        """
        start_time = time.time()
        
        try:
            self.performance_stats["total_syntheses"] += 1
            
            # Check cache first
            cached_audio = self._get_cached_audio(text, voice)
            if cached_audio:
                self.performance_stats["cache_hits"] += 1
                latency = time.time() - start_time
                self._update_stats(latency, True)
                
                return {
                    "audio_data": cached_audio,
                    "model": "edge_tts_cached",
                    "latency": latency,
                    "cached": True
                }
            
            # Synthesize with edge-tts
            result = await self._synthesize(text, voice)
            
            if "error" in result:
                self._update_stats(time.time() - start_time, False)
                return result
            
            # Cache the result
            self._cache_audio(text, result["audio_data"], voice)
            
            # Save to database
            try:
                v = voice or self.voice
                self.db.save_audio(text, result["audio_data"], v)
            except Exception as e:
                logger.warning(f"Failed to save audio to database: {str(e)}")
            
            self._update_stats(result["latency"], True)
            return result
            
        except Exception as e:
            latency = time.time() - start_time
            self._update_stats(latency, False)
            log_error_with_context(logger, e, {"method": "synthesize_speech", "text_length": len(text)})
            return {"error": f"Speech synthesis failed: {str(e)}"}
    
    async def _synthesize(self, text: str, voice: str = None) -> Dict[str, Any]:
        """Synthesize speech using Edge-TTS."""
        start_time = time.time()
        
        try:
            v = voice or self.voice
            communicate = edge_tts.Communicate(text, v)
            
            # Collect all audio chunks
            audio_chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])
            
            audio_data = b"".join(audio_chunks)
            latency = time.time() - start_time
            
            logger.debug(f"Edge-TTS synthesis completed in {latency:.3f}s ({len(audio_data)} bytes)")
            
            return {
                "audio_data": audio_data,
                "model": "edge_tts",
                "latency": latency,
                "cached": False
            }
                    
        except Exception as e:
            raise
    
    async def synthesize_streaming_chunks(self, text: str, voice: str = None) -> AsyncGenerator[bytes, None]:
        """
        Synthesize speech in streaming chunks for real-time playback.
        
        Args:
            text: Text to synthesize
            voice: Voice name to use (optional)
            
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
                result = await self.synthesize_speech(sentence, use_streaming=True, voice=voice)
                
                if "error" in result:
                    logger.error(f"Failed to synthesize sentence: {result['error']}")
                    continue
                
                # Create audio chunks using AudioStreamProcessor
                audio_chunks = audio_stream_processor.create_audio_chunks(result["audio_data"], chunk_size=1024)
                
                for chunk in audio_chunks:
                    yield chunk
                    
                # Small delay between sentences for natural flow
                await asyncio.sleep(0.1)
                
        except Exception as e:
            log_error_with_context(logger, e, {"method": "synthesize_streaming_chunks", "text_length": len(text)})
            raise
        

    
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
            
            # Synthesize common phrases
            for phrase in common_phrases:
                try:
                    result = await self.synthesize_speech(phrase, use_streaming=False, voice=self.voice)
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