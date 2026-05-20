"""
Text-to-Speech service for EchoAI voice chat system.

This module provides TTS functionality using Microsoft Edge neural TTS
(via edge-tts) with streaming support and caching for optimal performance.

Caching strategy:
  - Background warmup on startup: loads metadata index (<1s, no MP3 data)
  - L1 in-memory dict: instant (<1ms)
  - L2 Supabase Storage: on-demand MP3 download (~100ms), then cached in L1
"""

import asyncio
import re
import time
from typing import Dict, Any, List, Optional, AsyncGenerator
import edge_tts

from backend.utils import get_settings
from backend.utils import get_logger, log_performance, log_error_with_context
from backend.utils.audio import audio_stream_processor
from backend.db import AudioCacheRecord, DBOperations
from backend.exceptions import DatabaseError, TTSError
from backend.constants import (
    ModelName,
    LATENCY_WINDOW_SIZE,
    IN_MEMORY_CACHE_MAX_SIZE,
    IN_MEMORY_CACHE_EVICT_COUNT,
)

logger = get_logger(__name__)
settings = get_settings()


class TTSService:
    """Text-to-Speech service with streaming and caching support."""

    def __init__(self, db: Optional[DBOperations] = None):
        """Initialise TTS service.

        Args:
            db: Shared async DBOperations instance. If None, a new one is
                created (but initialize() must still be called before use).
        """
        self.voice = settings.EDGE_TTS_VOICE

        self.db = db or DBOperations()

        # L1 in-memory cache: cache_key → audio bytes
        self.cache: Dict[str, bytes] = {}
        self.cache_enabled = settings.TTS_CACHE_ENABLED

        # Metadata index: text_hash → storage_path (populated by warmup)
        self._metadata_index: Dict[str, str] = {}

        self.streaming_enabled = settings.TTS_STREAMING

        # Performance tracking
        self.performance_stats = {
            "total_syntheses": 0,
            "successful_syntheses": 0,
            "failed_syntheses": 0,
            "cache_hits": 0,
            "avg_latency": 0.0,
            "latencies": [],
        }

    async def initialize(self) -> None:
        """Ensure DB is initialised; call once at startup."""
        if not self.db._initialized:
            await self.db.initialize()

    async def warmup_cache(self) -> None:
        """Background warmup: load metadata index (no MP3 downloads).

        Should be launched as ``asyncio.create_task(tts.warmup_cache())``
        after ``await tts.initialize()``.
        """
        try:
            rows = await self.db.load_audio_metadata(self.voice)
            for row in rows:
                self._metadata_index[row["text_hash"]] = row["storage_path"]
            logger.info("TTS cache warmup: %d entries indexed", len(rows))
        except (DatabaseError, OSError, RuntimeError, ValueError) as exc:
            logger.warning("TTS cache warmup failed: %s", exc)

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

    async def _get_cached_audio(self, text: str, voice: str = None) -> Optional[bytes]:
        """Get cached audio data.

        L1: in-memory dict (instant)
        L2: Supabase Storage (on-demand download, ~100ms)
        """
        if not self.cache_enabled:
            return None

        # L1: in-memory cache
        cache_key = self._get_cache_key(text, voice)
        if cache_key in self.cache:
            return self.cache[cache_key]

        # L2: Supabase
        v = voice or self.voice
        try:
            audio_data = await self.db.load_audio(text, v)
            if audio_data:
                # Promote to L1
                self.cache[cache_key] = audio_data
                return audio_data
        except (DatabaseError, OSError, RuntimeError, ValueError) as exc:
            logger.warning("Failed to load audio from Supabase: %s", exc)

        return None

    def _cache_audio(self, text: str, audio_data: bytes, voice: str = None) -> None:
        """Cache audio data in L1 in-memory dict."""
        if not self.cache_enabled:
            return
        cache_key = self._get_cache_key(text, voice)
        self.cache[cache_key] = audio_data

        # Limit cache size
        if len(self.cache) > IN_MEMORY_CACHE_MAX_SIZE:
            oldest_keys = list(self.cache.keys())[:IN_MEMORY_CACHE_EVICT_COUNT]
            for key in oldest_keys:
                del self.cache[key]

    @staticmethod
    def _sanitize_for_tts(text: str) -> str:
        """Strip markdown / special chars that TTS should not vocalise.

        Keeps natural speech punctuation:  ? . @ , : ; ! ' " and whitespace.
        """
        # Remove markdown bold/italic markers (**, *, __, _)
        text = re.sub(r"\*{1,2}", "", text)
        text = re.sub(r"_{1,2}", "", text)
        # Remove markdown headings (### etc.)
        text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
        # Remove markdown list bullets (- or * at line start)
        text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.MULTILINE)
        # Remove backticks (inline code / code blocks)
        text = re.sub(r"`{1,3}", "", text)
        # Remove markdown links [text](url) → keep text
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        # Remove remaining special chars except ? . @ , : ; ! ' "
        text = re.sub(r"[~|>\\#\[\](){}]", "", text)
        # Collapse multiple spaces / blank lines
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @log_performance
    async def synthesize_speech(
        self, text: str, *, use_streaming: bool = True, voice: str = None
    ) -> Dict[str, Any]:
        """
        Synthesize speech from text using Edge-TTS.

        Args:
            text: Text to synthesize
            use_streaming: Whether to use streaming synthesis
            voice: Voice name to use (optional, e.g. "en-IN-PrabhatNeural")

        Returns:
            Dict with audio data and metadata
        """
        # Clean markdown/special chars before synthesis
        text = self._sanitize_for_tts(text)

        start_time = time.time()

        try:
            self.performance_stats["total_syntheses"] += 1

            # Check cache first (async — may hit Supabase on L1 miss)
            cached_audio = await self._get_cached_audio(text, voice)
            if cached_audio:
                self.performance_stats["cache_hits"] += 1
                latency = time.time() - start_time
                self._update_stats(latency, success=True)

                return {
                    "audio_data": cached_audio,
                    "model": ModelName.EDGE_TTS_CACHED,
                    "latency": latency,
                    "cached": True,
                }

            # Synthesize with edge-tts
            result = await self._synthesize(text, voice)

            if "error" in result:
                self._update_stats(time.time() - start_time, success=False)
                return result

            # Cache the result in L1
            self._cache_audio(text, result["audio_data"], voice)

            # Save to Supabase (async)
            try:
                v = voice or self.voice
                await self.db.save_audio(
                    AudioCacheRecord(
                        text=text, audio_data=result["audio_data"], voice_id=v
                    )
                )
            except (DatabaseError, OSError, RuntimeError, ValueError) as exc:
                logger.warning("Failed to save audio to Supabase: %s", exc)

            self._update_stats(result["latency"], success=True)
            return result

        except TTSError as e:
            latency = time.time() - start_time
            self._update_stats(latency, success=False)
            log_error_with_context(
                logger, e, {"method": "synthesize_speech", "text_length": len(text)}
            )
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

            logger.debug(
                "Edge-TTS synthesis completed in %.3fs (%d bytes)",
                latency,
                len(audio_data),
            )

            return {
                "audio_data": audio_data,
                "model": ModelName.EDGE_TTS,
                "latency": latency,
                "cached": False,
            }

        except (OSError, RuntimeError, ValueError) as exc:
            raise TTSError("Edge-TTS synthesis failed") from exc

    async def synthesize_streaming_chunks(
        self, text: str, voice: str = None
    ) -> AsyncGenerator[bytes, None]:
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
                result = await self.synthesize_speech(
                    sentence, use_streaming=True, voice=voice
                )

                if "error" in result:
                    logger.error("Failed to synthesize sentence: %s", result["error"])
                    continue

                # Create audio chunks using AudioStreamProcessor
                audio_chunks = audio_stream_processor.create_audio_chunks(
                    result["audio_data"], chunk_size=1024
                )

                for chunk in audio_chunks:
                    yield chunk

                # Small delay between sentences for natural flow
                await asyncio.sleep(0.1)

        except TTSError as e:
            log_error_with_context(
                logger,
                e,
                {"method": "synthesize_streaming_chunks", "text_length": len(text)},
            )
            raise

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences for chunked synthesis."""
        import re

        # Simple sentence splitting (can be enhanced with NLP libraries)
        sentences = re.split(r"[.!?]+", text)
        return [s.strip() for s in sentences if s.strip()]

    async def warm_up_cache(self) -> None:
        """Warm up TTS cache with metadata index + common phrases."""
        try:
            logger.info("Warming up TTS cache...")

            # Background warmup: load metadata index
            if self.cache_enabled:
                await self.warmup_cache()

            common_phrases = [
                "Hello, how can I help you?",
                "I understand.",
                "That's interesting.",
                "Let me think about that.",
                "Thank you for sharing.",
                "I'm here to help.",
                "That's a great question.",
                "I appreciate your input.",
            ]

            # Synthesize common phrases
            for phrase in common_phrases:
                try:
                    result = await self.synthesize_speech(
                        phrase, use_streaming=False, voice=self.voice
                    )
                    if "error" in result:
                        logger.warning(
                            "Failed to synthesize phrase: %s", result["error"]
                        )
                except TTSError as exc:
                    logger.warning("Failed to synthesize phrase '%s': %s", phrase, exc)

            logger.info("TTS cache warmed up with %d phrases", len(common_phrases))

        except (DatabaseError, TTSError, OSError, RuntimeError, ValueError) as exc:
            logger.warning("Failed to warm up TTS cache: %s", exc)

    def _update_stats(self, latency: float, *, success: bool) -> None:
        """Update performance statistics."""
        self.performance_stats["latencies"].append(latency)

        if success:
            self.performance_stats["successful_syntheses"] += 1
        else:
            self.performance_stats["failed_syntheses"] += 1

        # Keep only last 100 latencies
        if len(self.performance_stats["latencies"]) > LATENCY_WINDOW_SIZE:
            self.performance_stats["latencies"] = self.performance_stats["latencies"][
                -LATENCY_WINDOW_SIZE:
            ]

        # Update average latency
        if self.performance_stats["latencies"]:
            self.performance_stats["avg_latency"] = sum(
                self.performance_stats["latencies"]
            ) / len(self.performance_stats["latencies"])

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
            "cache_size": len(self.cache),
        }

    def clear_cache(self) -> None:
        """Clear TTS cache."""
        self.cache.clear()
        self._metadata_index.clear()
        logger.info("TTS cache cleared")

    async def cleanup(self) -> None:
        """Clean up database connections."""
        try:
            await self.db.close()
            logger.info("TTS service cleanup completed")
        except (DatabaseError, OSError, RuntimeError, ValueError) as exc:
            logger.error("Failed to cleanup TTS service: %s", exc)


# Global service instance — deferred initialisation
# Call `await tts_service.initialize()` at startup
tts_service = TTSService()
