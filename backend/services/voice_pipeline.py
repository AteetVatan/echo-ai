"""
Voice Processing Pipeline for EchoAI voice chat system.

This module provides a deterministic pipeline for processing voice input through
STT→(RAG+LLM)→TTS stages with semantic caching and comprehensive error handling.
"""

import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from langdetect import detect, LangDetectException, DetectorFactory

from backend.services.stt_service import stt_service
from backend.services.llm_service import llm_service
from backend.services.tts_service import tts_service
from backend.agents.langchain_rag_agent import get_rag_agent
from backend.utils.audio import audio_processor, audio_stream_processor
from backend.utils import get_logger, log_performance, log_error_with_context
from backend.constants import (
    ModelName,
    PipelineSource,
    LATENCY_WINDOW_SIZE,
    STREAM_PROCESSING_BATCH_SIZE,
    REPLY_CACHE_SIMILARITY_THRESHOLD,
)
from backend.exceptions import EchoAIError


logger = get_logger(__name__)

# Make langdetect deterministic (without this, same text can return different results)
DetectorFactory.seed = 0


@dataclass
class PipelineResult:
    """Result from voice processing pipeline."""

    transcription: str = ""
    response_text: str = ""
    audio_data: bytes = b""
    audio_file_path: str = ""
    detected_language: str = "en"
    pipeline_latency: float = 0.0
    stt_latency: float = 0.0
    rag_latency: float = 0.0
    llm_latency: float = 0.0
    tts_latency: float = 0.0
    models_used: Optional[Dict[str, str]] = None
    error: Optional[str] = None
    chunks_processed: Optional[int] = None
    cached: bool = False
    semantic_cache_hit: bool = False
    similarity_score: float = 0.0
    rag_used: bool = False
    source: str = PipelineSource.PIPELINE

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        result = {
            "transcription": self.transcription,
            "response_text": self.response_text,
            "audio_data": self.audio_data,
            "audio_file_path": self.audio_file_path,
            "detected_language": self.detected_language,
            "pipeline_latency": self.pipeline_latency,
            "stt_latency": self.stt_latency,
            "rag_latency": self.rag_latency,
            "llm_latency": self.llm_latency,
            "tts_latency": self.tts_latency,
            "cached": self.cached,
            "semantic_cache_hit": self.semantic_cache_hit,
            "similarity_score": self.similarity_score,
            "rag_used": self.rag_used,
            "source": self.source,
        }

        if self.models_used:
            result["models_used"] = self.models_used
        if self.error:
            result["error"] = self.error
        if self.chunks_processed is not None:
            result["chunks_processed"] = self.chunks_processed

        return result


class VoicePipeline:
    """
    Deterministic voice processing pipeline.

    Handles the complete STT→(RAG+LLM)→TTS flow with semantic caching,
    streaming support, error handling, and performance monitoring.
    """

    def __init__(self):
        self.conversation_active = False
        self.current_session_id = None
        self.performance_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "rag_queries": 0,
            "avg_pipeline_latency": 0.0,
            "latencies": [],
        }

        # Initialize RAG agent (lazy — deferred until first access)
        self._rag_agent = None

        # Strong-ref set for fire-and-forget persistence tasks so the
        # event loop doesn't garbage-collect them mid-flight.
        self._background_tasks: set[asyncio.Task] = set()

    @property
    def rag_agent(self):
        """Lazy accessor — initialises the RAG agent on first use."""
        if self._rag_agent is None:
            from backend.services.tts_service import tts_service

            self._rag_agent = get_rag_agent(tts_service.db)
        return self._rag_agent

    def _generate_audio_storage_path(self, session_id: str = None) -> str:
        """Generate a Supabase Storage path for session audio."""
        session_prefix = session_id[:8] if session_id else "default"
        unique_id = str(uuid.uuid4())[:8]
        return f"session_audio/{session_prefix}_{unique_id}.mp3"

    async def _load_cached_audio(self, audio_storage_path: str) -> Optional[bytes]:
        """Load audio data from Supabase Storage."""
        try:
            if not audio_storage_path:
                return None
            data = await tts_service.db.download_audio_bytes(audio_storage_path)
            return data
        except (EchoAIError, RuntimeError, ValueError, KeyError, TypeError) as e:
            logger.error("Failed to load cached audio %s: %s", audio_storage_path, e)
            return None

    def _persist_response_async(
        self,
        audio_file_path: str,
        audio_data: bytes,
        user_text: str,
        response_text: str,
    ) -> None:
        """Schedule post-response persistence as a background task.

        Used to move Supabase upload + cache-row insert off the request
        path so the user gets audio bytes back without waiting on
        storage I/O.
        """
        task = asyncio.create_task(
            self._persist_response(
                audio_file_path, audio_data, user_text, response_text
            )
        )
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _persist_response(
        self,
        audio_file_path: str,
        audio_data: bytes,
        user_text: str,
        response_text: str,
    ) -> None:
        """Upload audio then store the semantic-cache row. Best-effort."""
        try:
            await tts_service.db.upload_audio_bytes(audio_file_path, audio_data)
        except (EchoAIError, RuntimeError, ValueError, KeyError, TypeError) as e:
            logger.warning("Background audio upload failed: %s", e)

        try:
            await self.rag_agent.store_interaction(
                user_text, response_text, audio_file_path
            )
        except (EchoAIError, RuntimeError, ValueError, KeyError, TypeError) as e:
            logger.warning("Background cache write failed: %s", e)

    @log_performance
    async def process_voice_input(
        self, audio_data: bytes, session_id: str = None
    ) -> PipelineResult:
        """
        Process complete voice input through the hybrid STT→(RAG+LLM)→TTS pipeline.

        High-level flow:
        1. STT: Convert audio to text
        2. Semantic Cache Check: Look for similar cached responses
        3. RAG Agent: Use Agno agent for knowledge retrieval and reasoning
        4. TTS: Convert response to audio
        5. Cache: Store the interaction for future reuse

        Args:
            audio_data: Complete audio data in bytes
            session_id: Session identifier for tracking

        Returns:
            PipelineResult with complete processing results
        """
        pipeline_start = time.time()
        result = PipelineResult()

        try:
            self.current_session_id = session_id
            self.conversation_active = True
            self.performance_stats["total_requests"] += 1

            logger.info(f"Processing voice input for session {session_id}")

            # Stage 1: Audio Processing and STT
            stt_start = time.time()
            try:
                processed_audio = await audio_processor.process_audio_for_stt(
                    audio_data
                )
                stt_result = await stt_service.transcribe_audio(processed_audio)
                result.stt_latency = time.time() - stt_start

                if "error" in stt_result:
                    result.error = stt_result["error"]
                    result.pipeline_latency = time.time() - pipeline_start
                    self._update_stats(result.pipeline_latency, success=False)
                    return result

                result.transcription = stt_result["text"]
                result.detected_language = stt_result.get("detected_language", "en")

                if not result.transcription.strip():
                    result.error = "No speech detected"
                    result.pipeline_latency = time.time() - pipeline_start
                    self._update_stats(result.pipeline_latency, success=False)
                    return result

            except (EchoAIError, RuntimeError, ValueError, KeyError, TypeError) as e:
                result.error = f"STT processing failed: {str(e)}"
                result.stt_latency = time.time() - stt_start
                result.pipeline_latency = time.time() - pipeline_start
                self._update_stats(result.pipeline_latency, success=False)
                return result

            # Stage 2: RAG Agent Processing with Semantic Cache
            rag_start = time.time()
            try:
                rag_result = await self.rag_agent.process_query(
                    result.transcription, session_id, language=result.detected_language
                )
                result.rag_latency = time.time() - rag_start

                if "error" in rag_result:
                    result.error = rag_result["error"]
                    result.pipeline_latency = time.time() - pipeline_start
                    self._update_stats(result.pipeline_latency, success=False)
                    return result

                result.response_text = rag_result["response_text"]
                result.semantic_cache_hit = rag_result.get("cached", False)
                result.similarity_score = rag_result.get("similarity_score", 0.0)
                result.rag_used = rag_result.get("source") == PipelineSource.AGENT
                result.source = rag_result.get("source", PipelineSource.PIPELINE)

                # If we got a cached audio file, load it and return early
                if result.semantic_cache_hit and "audio_file_path" in rag_result:
                    cached_audio = await self._load_cached_audio(
                        rag_result["audio_file_path"]
                    )
                    if cached_audio:
                        result.audio_data = cached_audio
                        result.audio_file_path = rag_result["audio_file_path"]
                        result.cached = True
                        result.pipeline_latency = time.time() - pipeline_start

                        self.performance_stats["cache_hits"] += 1
                        self._update_stats(result.pipeline_latency, success=True)

                        logger.info(
                            f"Semantic cache hit: {result.similarity_score:.3f} similarity"
                        )
                        return result

                if result.rag_used:
                    self.performance_stats["rag_queries"] += 1

            except (EchoAIError, RuntimeError, ValueError, KeyError, TypeError) as e:
                result.error = f"RAG processing failed: {str(e)}"
                result.rag_latency = time.time() - rag_start
                result.pipeline_latency = time.time() - pipeline_start
                self._update_stats(result.pipeline_latency, success=False)
                return result

            # Stage 3: TTS Speech Synthesis
            tts_start = time.time()
            try:
                tts_result = await tts_service.synthesize_speech(result.response_text)
                result.tts_latency = time.time() - tts_start

                if "error" in tts_result:
                    result.error = tts_result["error"]
                    result.pipeline_latency = time.time() - pipeline_start
                    self._update_stats(result.pipeline_latency, success=False)
                    return result

                result.audio_data = tts_result["audio_data"]
                result.cached = tts_result.get("cached", False)
                result.audio_file_path = self._generate_audio_storage_path(session_id)

            except (EchoAIError, RuntimeError, ValueError, KeyError, TypeError) as e:
                result.error = f"TTS processing failed: {str(e)}"
                result.tts_latency = time.time() - tts_start
                result.pipeline_latency = time.time() - pipeline_start
                self._update_stats(result.pipeline_latency, success=False)
                return result

            # Stage 4: Persist audio + cache row in the background so storage
            # I/O doesn't add to user-visible latency.
            self._persist_response_async(
                result.audio_file_path,
                result.audio_data,
                result.transcription,
                result.response_text,
            )

            # Compile final results
            result.pipeline_latency = time.time() - pipeline_start
            result.models_used = {
                "stt": stt_result.get("model", ModelName.UNKNOWN),
                "rag": ModelName.LANGCHAIN_RAG,
                "tts": tts_result.get("model", ModelName.UNKNOWN),
            }

            self._update_stats(result.pipeline_latency, success=True)
            logger.info(f"Voice processing completed in {result.pipeline_latency:.3f}s")

            return result

        except (EchoAIError, RuntimeError, ValueError, KeyError, TypeError) as e:
            result.error = f"Pipeline failed: {str(e)}"
            result.pipeline_latency = time.time() - pipeline_start
            self._update_stats(result.pipeline_latency, success=False)
            log_error_with_context(
                logger,
                e,
                {
                    "session_id": session_id,
                    "audio_size": len(audio_data),
                    "pipeline_stage": "unknown",
                },
            )
            return result

    # -----------------------------------------------------------------------
    # Streaming variant: per-sentence MP3 frames
    # -----------------------------------------------------------------------
    # Sentence boundary = .!? followed by whitespace OR end-of-buffer at
    # stream completion. Apostrophes in contractions ("don't") and decimals
    # without trailing whitespace ("v1.0 release") do NOT trigger; "Dr. Smith"
    # does (acceptable — TTS just speaks two utterances).
    _SENTENCE_TERMINATORS = ".!?"

    @classmethod
    def _find_sentence_boundary(cls, text: str) -> int:
        """Return the cut index AFTER the first sentence boundary, or -1.

        A boundary is .!? followed by whitespace. End-of-buffer is handled
        separately by the caller at stream completion.
        """
        for i, ch in enumerate(text):
            if ch in cls._SENTENCE_TERMINATORS and i + 1 < len(text) and text[i + 1].isspace():
                return i + 1
        return -1

    async def _synth_sentence_bytes(self, sentence: str) -> bytes:
        """Synthesise one sentence to MP3 bytes. Best-effort; returns b'' on failure."""
        try:
            result = await tts_service.synthesize_speech(sentence)
            if "error" in result:
                logger.warning(
                    "Streaming TTS failed for sentence (%d chars): %s",
                    len(sentence),
                    result["error"],
                )
                return b""
            return result.get("audio_data", b"")
        except (EchoAIError, RuntimeError, ValueError, KeyError, TypeError) as exc:
            logger.warning("Streaming TTS exception: %s", exc)
            return b""

    async def _streaming_stt(
        self, audio_data: bytes
    ) -> Dict[str, Any]:
        """Run STT and return {text, language, latency} or {error}."""
        stt_start = time.time()
        try:
            processed_audio = await audio_processor.process_audio_for_stt(audio_data)
            stt_result = await stt_service.transcribe_audio(processed_audio)
        except (EchoAIError, RuntimeError, ValueError, KeyError, TypeError) as exc:
            return {"error": f"STT processing failed: {exc}"}

        latency = time.time() - stt_start
        if "error" in stt_result:
            return {"error": stt_result["error"]}

        transcription = stt_result.get("text", "")
        if not transcription.strip():
            return {"error": "No speech detected"}

        return {
            "text": transcription,
            "language": stt_result.get("detected_language", "en"),
            "latency": latency,
        }

    async def _try_streaming_cache_hit(
        self, transcription: str, session_id: str
    ):
        """If the reply cache has a near-match with audio, return (audio, reply); else None."""
        try:
            if self.rag_agent.is_contextual_query(transcription, session_id):
                return None
            cached_reply = await self.rag_agent.reply_cache.find_similar_reply(
                transcription
            )
        except (EchoAIError, RuntimeError, ValueError, KeyError, TypeError) as exc:
            logger.warning("Reply cache lookup failed: %s", exc)
            return None

        if not (
            cached_reply
            and cached_reply.similarity_score >= REPLY_CACHE_SIMILARITY_THRESHOLD
            and cached_reply.audio_file_path
        ):
            return None

        cached_audio = await self._load_cached_audio(cached_reply.audio_file_path)
        if not cached_audio:
            return None
        return cached_audio, cached_reply

    async def _try_emit_next_sentence(
        self, buffer: str, seq: int, accumulator: bytearray
    ):
        """Pop the next complete sentence (if any) from ``buffer`` and emit it.

        Returns ``(remaining_buffer, next_seq, frame_or_None)``. ``frame`` is
        None when there is no complete sentence yet (caller stops looping).
        Empty whitespace-only fragments before the next real sentence are
        skipped internally so the caller doesn't have to spin one outer
        iteration per skipped fragment.
        """
        while True:
            boundary = self._find_sentence_boundary(buffer)
            if boundary <= 0:
                return buffer, seq, None
            sentence = buffer[:boundary].strip()
            buffer = buffer[boundary:].lstrip()
            if not sentence:
                # Empty fragment — keep scanning the remaining buffer in this call.
                continue
            audio = await self._synth_sentence_bytes(sentence)
            if not audio:
                # Synth failed — drop this sentence and continue scanning.
                continue
            accumulator.extend(audio)
            return (
                buffer,
                seq + 1,
                {
                    "type": "audio_delta",
                    "audio": audio,
                    "seq": seq,
                    "sentence": sentence,
                },
            )

    async def _pump_llm_to_audio_events(
        self, transcription: str, session_id: str, language: str
    ):
        """Stream LLM tokens; yield audio_delta dicts then a final meta dict.

        Final yield is ``{"_meta": {...}, "_accumulated": bytes,
        "_sentence_count": int}``; the caller forwards audio_deltas to the
        WS and uses meta + accumulated for persistence.
        """
        accumulated = bytearray()
        buffer = ""
        seq = 0
        meta: Dict[str, Any] = {}

        async for chunk in self.rag_agent.process_query_streaming(
            transcription, session_id, language=language
        ):
            if isinstance(chunk, dict) and chunk.get("_done"):
                meta = chunk
                break
            if not isinstance(chunk, str):
                continue
            buffer += chunk
            while True:
                buffer, seq, frame = await self._try_emit_next_sentence(
                    buffer, seq, accumulated
                )
                if frame is None:
                    break
                yield frame

        # Flush trailing fragment (no terminator + whitespace at end-of-stream).
        tail = buffer.strip()
        if tail:
            audio = await self._synth_sentence_bytes(tail)
            if audio:
                accumulated.extend(audio)
                yield {
                    "type": "audio_delta",
                    "audio": audio,
                    "seq": seq,
                    "sentence": tail,
                }
                seq += 1

        yield {
            "_meta": meta,
            "_accumulated": bytes(accumulated),
            "_sentence_count": seq,
        }

    async def process_voice_input_streaming(
        self, audio_data: bytes, session_id: str = None
    ):
        """Streaming pipeline: yields per-sentence MP3 frames as the LLM generates.

        Yields a sequence of dict events:
          - {"type": "transcription", "text", "detected_language", "stt_latency"}
          - {"type": "audio_delta", "audio": bytes, "seq": int, "sentence": str}
          - {"type": "done", "response_text", "audio_file_path", "pipeline_latency",
              "stt_latency", "cached": bool, "source": str, "similarity_score": float?}
          - {"type": "error", "error": str}
        """
        pipeline_start = time.time()
        self.current_session_id = session_id
        self.conversation_active = True
        self.performance_stats["total_requests"] += 1

        stt = await self._streaming_stt(audio_data)
        if "error" in stt:
            self._update_stats(time.time() - pipeline_start, success=False)
            yield {"type": "error", "error": stt["error"]}
            return

        transcription = stt["text"]
        detected_language = stt["language"]
        stt_latency = stt["latency"]
        yield {
            "type": "transcription",
            "text": transcription,
            "detected_language": detected_language,
            "stt_latency": stt_latency,
        }

        cache_hit = await self._try_streaming_cache_hit(transcription, session_id)
        if cache_hit is not None:
            cached_audio, cached_reply = cache_hit
            await self.rag_agent.store_exchange(
                session_id, transcription, cached_reply.response_text
            )
            self.performance_stats["cache_hits"] += 1
            pipeline_latency = time.time() - pipeline_start
            self._update_stats(pipeline_latency, success=True)
            yield {
                "type": "audio_delta",
                "audio": cached_audio,
                "seq": 0,
                "sentence": cached_reply.response_text,
            }
            yield {
                "type": "done",
                "response_text": cached_reply.response_text,
                "audio_file_path": cached_reply.audio_file_path,
                "pipeline_latency": pipeline_latency,
                "stt_latency": stt_latency,
                "cached": True,
                "similarity_score": cached_reply.similarity_score,
                "source": PipelineSource.CACHE,
            }
            return

        rag_start = time.time()
        accumulated_audio = b""
        response_meta: Dict[str, Any] = {}
        sentence_count = 0
        try:
            async for evt in self._pump_llm_to_audio_events(
                transcription, session_id, detected_language
            ):
                if "_meta" in evt:
                    response_meta = evt["_meta"]
                    accumulated_audio = evt["_accumulated"]
                    sentence_count = evt["_sentence_count"]
                else:
                    yield evt
        except (EchoAIError, RuntimeError, ValueError, KeyError, TypeError) as exc:
            pipeline_latency = time.time() - pipeline_start
            self._update_stats(pipeline_latency, success=False)
            log_error_with_context(
                logger,
                exc,
                {
                    "session_id": session_id,
                    "audio_size": len(audio_data),
                    "pipeline_stage": "streaming_llm_tts",
                },
            )
            yield {"type": "error", "error": f"Streaming pipeline failed: {exc}"}
            return

        response_text = response_meta.get("response_text", "")
        source = response_meta.get("source", PipelineSource.PIPELINE)
        if source == PipelineSource.RAG_SELF_INFO:
            self.performance_stats["rag_queries"] += 1

        audio_file_path = ""
        if accumulated_audio and response_text:
            audio_file_path = self._generate_audio_storage_path(session_id)
            self._persist_response_async(
                audio_file_path, accumulated_audio, transcription, response_text
            )

        pipeline_latency = time.time() - pipeline_start
        rag_latency = time.time() - rag_start
        self._update_stats(pipeline_latency, success=True)
        logger.info(
            "Streaming voice pipeline completed: %d sentences, %.3fs (stt=%.3fs, rag+tts=%.3fs)",
            sentence_count,
            pipeline_latency,
            stt_latency,
            rag_latency,
        )
        yield {
            "type": "done",
            "response_text": response_text,
            "audio_file_path": audio_file_path,
            "pipeline_latency": pipeline_latency,
            "stt_latency": stt_latency,
            "rag_latency": rag_latency,
            "cached": False,
            "source": source,
            "sentences": sentence_count,
        }

    async def process_streaming_voice(
        self, audio_chunks: List[bytes], session_id: str = None
    ) -> PipelineResult:
        """
        Process voice input in streaming chunks for lower latency.

        Args:
            audio_chunks: List of audio chunk bytes
            session_id: Session identifier for tracking

        Returns:
            PipelineResult with streaming processing results
        """
        pipeline_start = time.time()
        result = PipelineResult()
        result.chunks_processed = len(audio_chunks)

        try:
            self.current_session_id = session_id
            self.conversation_active = True
            self.performance_stats["total_requests"] += 1

            logger.info(f"Starting streaming voice processing for session {session_id}")

            # Stage 1: Process Audio Chunks
            stt_start = time.time()
            try:
                # Combine and process audio chunks
                processed_audio = await self._process_audio_chunks(audio_chunks)

                # Transcribe the combined audio
                stt_result = await stt_service.transcribe_audio(processed_audio)
                result.stt_latency = time.time() - stt_start

                if "error" in stt_result:
                    result.error = stt_result["error"]
                    result.pipeline_latency = time.time() - pipeline_start
                    self._update_stats(result.pipeline_latency, success=False)
                    return result

                result.transcription = stt_result["text"]
                result.detected_language = stt_result.get("detected_language", "en")

                if not result.transcription.strip():
                    result.error = "No speech detected in audio chunks"
                    result.pipeline_latency = time.time() - pipeline_start
                    self._update_stats(result.pipeline_latency, success=False)
                    return result

            except (EchoAIError, RuntimeError, ValueError, KeyError, TypeError) as e:
                result.error = f"Streaming audio processing failed: {str(e)}"
                result.stt_latency = time.time() - stt_start
                result.pipeline_latency = time.time() - pipeline_start
                self._update_stats(result.pipeline_latency, success=False)
                return result

            # Stage 2: RAG Agent Processing with Semantic Cache
            rag_start = time.time()
            try:
                rag_result = await self.rag_agent.process_query(
                    result.transcription, session_id, language=result.detected_language
                )
                result.rag_latency = time.time() - rag_start

                if "error" in rag_result:
                    result.error = rag_result["error"]
                    result.pipeline_latency = time.time() - pipeline_start
                    self._update_stats(result.pipeline_latency, success=False)
                    return result

                result.response_text = rag_result["response_text"]
                result.semantic_cache_hit = rag_result.get("cached", False)
                result.similarity_score = rag_result.get("similarity_score", 0.0)
                result.rag_used = rag_result.get("source") == PipelineSource.AGENT
                result.source = rag_result.get("source", PipelineSource.PIPELINE)

                # If we got a cached audio file, load it and return early
                if result.semantic_cache_hit and "audio_file_path" in rag_result:
                    cached_audio = await self._load_cached_audio(
                        rag_result["audio_file_path"]
                    )
                    if cached_audio:
                        result.audio_data = cached_audio
                        result.audio_file_path = rag_result["audio_file_path"]
                        result.cached = True
                        result.pipeline_latency = time.time() - pipeline_start

                        self.performance_stats["cache_hits"] += 1
                        self._update_stats(result.pipeline_latency, success=True)

                        logger.info(
                            f"Streaming semantic cache hit: {result.similarity_score:.3f} similarity"
                        )
                        return result

                if result.rag_used:
                    self.performance_stats["rag_queries"] += 1

            except (EchoAIError, RuntimeError, ValueError, KeyError, TypeError) as e:
                result.error = f"RAG processing failed: {str(e)}"
                result.rag_latency = time.time() - rag_start
                result.pipeline_latency = time.time() - pipeline_start
                self._update_stats(result.pipeline_latency, success=False)
                return result

            # Stage 3: TTS Speech Synthesis
            tts_start = time.time()
            try:
                tts_result = await tts_service.synthesize_speech(result.response_text)
                result.tts_latency = time.time() - tts_start

                if "error" in tts_result:
                    result.error = tts_result["error"]
                    result.pipeline_latency = time.time() - pipeline_start
                    self._update_stats(result.pipeline_latency, success=False)
                    return result

                result.audio_data = tts_result["audio_data"]
                result.cached = tts_result.get("cached", False)
                result.audio_file_path = self._generate_audio_storage_path(session_id)

            except (EchoAIError, RuntimeError, ValueError, KeyError, TypeError) as e:
                result.error = f"TTS processing failed: {str(e)}"
                result.tts_latency = time.time() - tts_start
                result.pipeline_latency = time.time() - pipeline_start
                self._update_stats(result.pipeline_latency, success=False)
                return result

            # Stage 4: Persist audio + cache row in the background.
            self._persist_response_async(
                result.audio_file_path,
                result.audio_data,
                result.transcription,
                result.response_text,
            )

            # Finalize results
            result.pipeline_latency = time.time() - pipeline_start
            result.models_used = {
                "stt": stt_result.get("model", ModelName.UNKNOWN),
                "rag": ModelName.AGNO_AGENT,
                "tts": tts_result.get("model", ModelName.UNKNOWN),
            }

            self._update_stats(result.pipeline_latency, success=True)

            logger.info(
                f"Streaming pipeline completed in {result.pipeline_latency:.3f}s "
                f"(STT: {result.stt_latency:.3f}s, RAG: {result.rag_latency:.3f}s, "
                f"TTS: {result.tts_latency:.3f}s)"
            )

            return result

        except (EchoAIError, RuntimeError, ValueError, KeyError, TypeError) as e:
            result.error = f"Streaming pipeline failed: {str(e)}"
            result.pipeline_latency = time.time() - pipeline_start
            self._update_stats(result.pipeline_latency, success=False)
            log_error_with_context(
                logger,
                e,
                {
                    "session_id": session_id,
                    "chunks_count": len(audio_chunks),
                    "total_audio_size": sum(len(chunk) for chunk in audio_chunks),
                },
            )
            return result

    async def process_audio_stream(
        self, audio_stream: asyncio.StreamReader, session_id: str = None
    ) -> PipelineResult:
        """
        Process real-time audio stream for ultra-low latency.

        Args:
            audio_stream: Async stream reader for audio data
            session_id: Session identifier for tracking

        Returns:
            PipelineResult with stream processing results
        """
        pipeline_start = time.time()
        result = PipelineResult()

        try:
            self.current_session_id = session_id
            self.conversation_active = True

            logger.info(
                f"Starting real-time audio stream processing for session {session_id}"
            )

            # Collect audio chunks from stream
            audio_chunks = []
            async for chunk in audio_stream_processor.process_audio_stream(
                audio_stream
            ):
                audio_chunks.append(chunk)

                # Process chunks in batches for optimal performance
                if len(audio_chunks) >= STREAM_PROCESSING_BATCH_SIZE:
                    break

            if not audio_chunks:
                result.error = "No audio data received from stream"
                result.pipeline_latency = time.time() - pipeline_start
                self._update_stats(result.pipeline_latency, success=False)
                return result

            # Process the accumulated chunks using streaming pipeline
            return await self.process_streaming_voice(audio_chunks, session_id)

        except (EchoAIError, RuntimeError, ValueError, KeyError, TypeError) as e:
            result.error = f"Stream processing failed: {str(e)}"
            result.pipeline_latency = time.time() - pipeline_start
            self._update_stats(result.pipeline_latency, success=False)
            log_error_with_context(logger, e, {"session_id": session_id})
            return result

    async def process_text_input(
        self, text: str, session_id: str = None, *, skip_tts: bool = False
    ) -> PipelineResult:
        """
        Process text input through RAG→TTS pipeline.

        Args:
            text: Input text to process
            session_id: Session identifier for tracking
            skip_tts: If True, skip TTS synthesis (chat-only mode)

        Returns:
            PipelineResult with text processing results
        """
        pipeline_start = time.time()
        result = PipelineResult()
        result.transcription = text  # Input text as "transcription"

        # Detect language from typed text
        detected_language = self._detect_text_language(text)

        try:
            self.current_session_id = session_id
            self.performance_stats["total_requests"] += 1

            logger.info(
                f"Processing text input for session {session_id} (skip_tts={skip_tts})"
            )

            # Stage 1: RAG Agent Processing with Semantic Cache
            rag_start = time.time()
            try:
                rag_result = await self.rag_agent.process_query(
                    text, session_id, language=detected_language
                )
                result.rag_latency = time.time() - rag_start

                if "error" in rag_result:
                    result.error = rag_result["error"]
                    result.pipeline_latency = time.time() - pipeline_start
                    self._update_stats(result.pipeline_latency, success=False)
                    return result

                result.response_text = rag_result["response_text"]
                result.semantic_cache_hit = rag_result.get("cached", False)
                result.similarity_score = rag_result.get("similarity_score", 0.0)
                result.rag_used = rag_result.get("source") == PipelineSource.AGENT
                result.source = rag_result.get("source", PipelineSource.PIPELINE)

                # If we got a cached audio file and TTS is not skipped, load it and return early
                if (
                    not skip_tts
                    and result.semantic_cache_hit
                    and "audio_file_path" in rag_result
                ):
                    cached_audio = await self._load_cached_audio(
                        rag_result["audio_file_path"]
                    )
                    if cached_audio:
                        result.audio_data = cached_audio
                        result.audio_file_path = rag_result["audio_file_path"]
                        result.cached = True
                        result.pipeline_latency = time.time() - pipeline_start

                        self.performance_stats["cache_hits"] += 1
                        self._update_stats(result.pipeline_latency, success=True)

                        logger.info(
                            f"Text semantic cache hit: {result.similarity_score:.3f} similarity"
                        )
                        return result

                if result.rag_used:
                    self.performance_stats["rag_queries"] += 1

            except (EchoAIError, RuntimeError, ValueError, KeyError, TypeError) as e:
                result.error = f"RAG processing failed: {str(e)}"
                result.rag_latency = time.time() - rag_start
                result.pipeline_latency = time.time() - pipeline_start
                self._update_stats(result.pipeline_latency, success=False)
                return result

            # Stage 2: TTS Speech Synthesis (skipped in chat-only mode)
            if not skip_tts:
                tts_start = time.time()
                try:
                    tts_result = await tts_service.synthesize_speech(
                        result.response_text
                    )
                    result.tts_latency = time.time() - tts_start

                    if "error" in tts_result:
                        result.error = tts_result["error"]
                        result.pipeline_latency = time.time() - pipeline_start
                        self._update_stats(result.pipeline_latency, success=False)
                        return result

                    result.audio_data = tts_result["audio_data"]
                    result.cached = tts_result.get("cached", False)
                    result.audio_file_path = self._generate_audio_storage_path(
                        session_id
                    )

                except (
                    EchoAIError,
                    RuntimeError,
                    ValueError,
                    KeyError,
                    TypeError,
                ) as e:
                    result.error = f"TTS processing failed: {str(e)}"
                    result.tts_latency = time.time() - tts_start
                    result.pipeline_latency = time.time() - pipeline_start
                    self._update_stats(result.pipeline_latency, success=False)
                    return result

                # Stage 3: Persist audio + cache row in the background.
                self._persist_response_async(
                    result.audio_file_path,
                    result.audio_data,
                    text,
                    result.response_text,
                )

            # Finalize results
            result.pipeline_latency = time.time() - pipeline_start
            if not skip_tts:
                result.models_used = {
                    "rag": ModelName.AGNO_AGENT,
                    "tts": tts_result.get("model", ModelName.UNKNOWN),
                }
            else:
                result.models_used = {
                    "rag": ModelName.AGNO_AGENT,
                }

            self._update_stats(result.pipeline_latency, success=True)
            logger.info(
                f"Text processing completed in {result.pipeline_latency:.3f}s (skip_tts={skip_tts})"
            )

            return result

        except (EchoAIError, RuntimeError, ValueError, KeyError, TypeError) as e:
            result.error = f"Text pipeline failed: {str(e)}"
            result.pipeline_latency = time.time() - pipeline_start
            self._update_stats(result.pipeline_latency, success=False)
            log_error_with_context(
                logger, e, {"session_id": session_id, "text_length": len(text)}
            )
            return result

    # Common English function words that almost never appear in other languages.
    # If ANY of these appear in a short text, it's almost certainly English.
    _ENGLISH_MARKERS = frozenset(
        {
            "the",
            "is",
            "are",
            "was",
            "were",
            "have",
            "has",
            "had",
            "what",
            "which",
            "where",
            "when",
            "who",
            "whom",
            "whose",
            "how",
            "why",
            "can",
            "could",
            "would",
            "should",
            "will",
            "tell",
            "your",
            "you",
            "about",
            "my",
            "me",
            "him",
            "her",
            "this",
            "that",
            "these",
            "those",
            "do",
            "does",
            "did",
        }
    )

    def _detect_text_language(self, text: str) -> str:
        """Detect language from typed text input.

        langdetect is notoriously unreliable on short texts with
        cross-language cognates (e.g. 'tell me about your experience'
        → French 99.99%).  We guard against this by checking for
        common English function words first.
        """
        words = text.lower().strip().split()

        # Short text containing common English words → English
        if len(words) <= 12 and self._ENGLISH_MARKERS & set(words):
            return "en"

        try:
            lang = detect(text)
            return lang if lang else "en"
        except LangDetectException:
            return "en"

    async def _process_audio_chunks(self, audio_chunks: List[bytes]) -> bytes:
        """Combine and process streaming audio chunks for STT."""
        try:
            # Process the combined audio for STT compatibility
            processed_audio = await audio_processor.process_audio_chunks_for_stt(
                audio_chunks, "webm"
            )

            logger.debug(
                f"Combined {len(audio_chunks)} chunks into {len(processed_audio)} bytes, "
                f"processed to {len(processed_audio)} bytes"
            )

            return processed_audio

        except (EchoAIError, RuntimeError, ValueError, KeyError, TypeError) as e:
            log_error_with_context(
                logger,
                e,
                {
                    "chunks_count": len(audio_chunks),
                    "total_size": sum(len(chunk) for chunk in audio_chunks),
                },
            )
            raise

    def _update_stats(self, latency: float, *, success: bool) -> None:
        """Update performance statistics."""
        self.performance_stats["latencies"].append(latency)

        if success:
            self.performance_stats["successful_requests"] += 1
        else:
            self.performance_stats["failed_requests"] += 1

        # Keep only last 100 latencies
        if len(self.performance_stats["latencies"]) > LATENCY_WINDOW_SIZE:
            self.performance_stats["latencies"] = self.performance_stats["latencies"][
                -LATENCY_WINDOW_SIZE:
            ]

        # Update average latency
        if self.performance_stats["latencies"]:
            self.performance_stats["avg_pipeline_latency"] = sum(
                self.performance_stats["latencies"]
            ) / len(self.performance_stats["latencies"])

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get pipeline performance statistics."""
        total_requests = self.performance_stats["total_requests"]
        cache_hits = self.performance_stats["cache_hits"]
        rag_queries = self.performance_stats["rag_queries"]

        return {
            "total_requests": total_requests,
            "successful_requests": self.performance_stats["successful_requests"],
            "failed_requests": self.performance_stats["failed_requests"],
            "cache_hits": cache_hits,
            "rag_queries": rag_queries,
            "success_rate": (
                self.performance_stats["successful_requests"] / total_requests
                if total_requests > 0
                else 0
            ),
            "cache_hit_rate": (
                cache_hits / total_requests if total_requests > 0 else 0
            ),
            "rag_usage_rate": (
                rag_queries / total_requests if total_requests > 0 else 0
            ),
            "avg_pipeline_latency": self.performance_stats["avg_pipeline_latency"],
            "conversation_active": self.conversation_active,
            "current_session_id": self.current_session_id,
        }

    def clear_conversation(self) -> None:
        """Clear conversation state and history."""
        llm_service.clear_conversation()
        self.conversation_active = False
        self.current_session_id = None
        logger.info("Pipeline conversation cleared")


# Global pipeline instance
voice_pipeline = VoicePipeline()
