"""
Voice Processing Pipeline for EchoAI voice chat system.

This module provides a deterministic pipeline for processing voice input through
STT→(RAG+LLM)→TTS stages with semantic caching and comprehensive error handling.
"""

import asyncio
import time
import os
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from src.services.stt_service import stt_service
from src.services.llm_service import llm_service
from src.services.tts_service import tts_service
from src.services.langchain_rag_agent import rag_agent
from src.utils.audio import audio_processor, stream_processor
from src.utils import get_logger, log_performance, log_error_with_context


logger = get_logger(__name__)


@dataclass
class PipelineResult:
    """Result from voice processing pipeline."""
    transcription: str = ""
    response_text: str = ""
    audio_data: bytes = b""
    audio_file_path: str = ""
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
    source: str = "pipeline"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        result = {
            "transcription": self.transcription,
            "response_text": self.response_text,
            "audio_data": self.audio_data,
            "audio_file_path": self.audio_file_path,
            "pipeline_latency": self.pipeline_latency,
            "stt_latency": self.stt_latency,
            "rag_latency": self.rag_latency,
            "llm_latency": self.llm_latency,
            "tts_latency": self.tts_latency,
            "cached": self.cached,
            "semantic_cache_hit": self.semantic_cache_hit,
            "similarity_score": self.similarity_score,
            "rag_used": self.rag_used,
            "source": self.source
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
        self.audio_cache_dir = "audio_cache"
        self.performance_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "rag_queries": 0,
            "avg_pipeline_latency": 0.0,
            "latencies": []
        }
        
        # Initialize RAG agent
        self.rag_agent = rag_agent
        
        # Ensure audio cache directory exists
        os.makedirs(self.audio_cache_dir, exist_ok=True)
    
    def _generate_audio_file_path(self, session_id: str = None) -> str:
        """Generate unique audio file path."""
        session_prefix = session_id[:8] if session_id else "default"
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{session_prefix}_{unique_id}.mp3"
        return os.path.join(self.audio_cache_dir, filename)
    
    async def _load_cached_audio(self, audio_file_path: str) -> Optional[bytes]:
        """Load audio data from cached file."""
        try:
            if os.path.exists(audio_file_path):
                with open(audio_file_path, 'rb') as f:
                    return f.read()
            return None
        except Exception as e:
            logger.error(f"Failed to load cached audio {audio_file_path}: {str(e)}")
            return None
    
    async def _save_audio_file(self, audio_data: bytes, audio_file_path: str) -> bool:
        """Save audio data to file."""
        try:
            with open(audio_file_path, 'wb') as f:
                f.write(audio_data)
            return True
        except Exception as e:
            logger.error(f"Failed to save audio file {audio_file_path}: {str(e)}")
            return False
    
    @log_performance
    async def process_voice_input(self, audio_data: bytes, session_id: str = None) -> PipelineResult:
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
                processed_audio = await audio_processor.process_audio_for_stt(audio_data)
                stt_result = await stt_service.transcribe_audio(processed_audio)
                result.stt_latency = time.time() - stt_start
                
                if "error" in stt_result:
                    result.error = stt_result["error"]
                    result.pipeline_latency = time.time() - pipeline_start
                    self._update_stats(result.pipeline_latency, False)
                    return result
                
                result.transcription = stt_result["text"]
                
                if not result.transcription.strip():
                    result.error = "No speech detected"
                    result.pipeline_latency = time.time() - pipeline_start
                    self._update_stats(result.pipeline_latency, False)
                    return result
                
            except Exception as e:
                result.error = f"STT processing failed: {str(e)}"
                result.stt_latency = time.time() - stt_start
                result.pipeline_latency = time.time() - pipeline_start
                self._update_stats(result.pipeline_latency, False)
                return result
            
            # Stage 2: RAG Agent Processing with Semantic Cache
            rag_start = time.time()
            try:
                rag_result = await self.rag_agent.process_query(result.transcription, session_id)
                result.rag_latency = time.time() - rag_start
                
                if "error" in rag_result:
                    result.error = rag_result["error"]
                    result.pipeline_latency = time.time() - pipeline_start
                    self._update_stats(result.pipeline_latency, False)
                    return result
                
                result.response_text = rag_result["response_text"]
                result.semantic_cache_hit = rag_result.get("cached", False)
                result.similarity_score = rag_result.get("similarity_score", 0.0)
                result.rag_used = rag_result.get("source") == "agent"
                result.source = rag_result.get("source", "pipeline")
                
                # If we got a cached audio file, load it and return early
                if result.semantic_cache_hit and "audio_file_path" in rag_result:
                    cached_audio = await self._load_cached_audio(rag_result["audio_file_path"])
                    if cached_audio:
                        result.audio_data = cached_audio
                        result.audio_file_path = rag_result["audio_file_path"]
                        result.cached = True
                        result.pipeline_latency = time.time() - pipeline_start
                        
                        self.performance_stats["cache_hits"] += 1
                        self._update_stats(result.pipeline_latency, True)
                        
                        logger.info(f"Semantic cache hit: {result.similarity_score:.3f} similarity")
                        return result
                
                if result.rag_used:
                    self.performance_stats["rag_queries"] += 1
                
            except Exception as e:
                result.error = f"RAG processing failed: {str(e)}"
                result.rag_latency = time.time() - rag_start
                result.pipeline_latency = time.time() - pipeline_start
                self._update_stats(result.pipeline_latency, False)
                return result
            
            # Stage 3: TTS Speech Synthesis
            tts_start = time.time()
            try:
                tts_result = await tts_service.synthesize_speech(result.response_text)
                result.tts_latency = time.time() - tts_start
                
                if "error" in tts_result:
                    result.error = tts_result["error"]
                    result.pipeline_latency = time.time() - pipeline_start
                    self._update_stats(result.pipeline_latency, False)
                    return result
                
                result.audio_data = tts_result["audio_data"]
                result.cached = tts_result.get("cached", False)
                
                # Generate audio file path and save
                result.audio_file_path = self._generate_audio_file_path(session_id)
                await self._save_audio_file(result.audio_data, result.audio_file_path)
                
            except Exception as e:
                result.error = f"TTS processing failed: {str(e)}"
                result.tts_latency = time.time() - tts_start
                result.pipeline_latency = time.time() - pipeline_start
                self._update_stats(result.pipeline_latency, False)
                return result
            
            # Stage 4: Store interaction in cache for future semantic reuse
            try:
                await self.rag_agent.store_interaction(
                    result.transcription, 
                    result.response_text, 
                    result.audio_file_path
                )
            except Exception as e:
                logger.warning(f"Failed to store interaction in cache: {str(e)}")
            
            # Compile final results
            result.pipeline_latency = time.time() - pipeline_start
            result.models_used = {
                "stt": stt_result.get("model", "unknown"),
                "rag": "langchain_rag_agent",
                "tts": tts_result.get("model", "unknown")
            }
            
            self._update_stats(result.pipeline_latency, True)
            logger.info(f"Voice processing completed in {result.pipeline_latency:.3f}s")
            
            return result
            
        except Exception as e:
            result.error = f"Pipeline failed: {str(e)}"
            result.pipeline_latency = time.time() - pipeline_start
            self._update_stats(result.pipeline_latency, False)
            log_error_with_context(logger, e, {
                "session_id": session_id, 
                "audio_size": len(audio_data),
                "pipeline_stage": "unknown"
            })
            return result
    
    async def process_streaming_voice(self, audio_chunks: List[bytes], session_id: str = None) -> PipelineResult:
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
                    self._update_stats(result.pipeline_latency, False)
                    return result
                
                result.transcription = stt_result["text"]
                
                if not result.transcription.strip():
                    result.error = "No speech detected in audio chunks"
                    result.pipeline_latency = time.time() - pipeline_start
                    self._update_stats(result.pipeline_latency, False)
                    return result
                
            except Exception as e:
                result.error = f"Streaming audio processing failed: {str(e)}"
                result.stt_latency = time.time() - stt_start
                result.pipeline_latency = time.time() - pipeline_start
                self._update_stats(result.pipeline_latency, False)
                return result
            
            # Stage 2: RAG Agent Processing with Semantic Cache
            rag_start = time.time()
            try:
                rag_result = await self.rag_agent.process_query(result.transcription, session_id)
                result.rag_latency = time.time() - rag_start
                
                if "error" in rag_result:
                    result.error = rag_result["error"]
                    result.pipeline_latency = time.time() - pipeline_start
                    self._update_stats(result.pipeline_latency, False)
                    return result
                
                result.response_text = rag_result["response_text"]
                result.semantic_cache_hit = rag_result.get("cached", False)
                result.similarity_score = rag_result.get("similarity_score", 0.0)
                result.rag_used = rag_result.get("source") == "agent"
                result.source = rag_result.get("source", "pipeline")
                
                # If we got a cached audio file, load it and return early
                if result.semantic_cache_hit and "audio_file_path" in rag_result:
                    cached_audio = await self._load_cached_audio(rag_result["audio_file_path"])
                    if cached_audio:
                        result.audio_data = cached_audio
                        result.audio_file_path = rag_result["audio_file_path"]
                        result.cached = True
                        result.pipeline_latency = time.time() - pipeline_start
                        
                        self.performance_stats["cache_hits"] += 1
                        self._update_stats(result.pipeline_latency, True)
                        
                        logger.info(f"Streaming semantic cache hit: {result.similarity_score:.3f} similarity")
                        return result
                
                if result.rag_used:
                    self.performance_stats["rag_queries"] += 1
                
            except Exception as e:
                result.error = f"RAG processing failed: {str(e)}"
                result.rag_latency = time.time() - rag_start
                result.pipeline_latency = time.time() - pipeline_start
                self._update_stats(result.pipeline_latency, False)
                return result
            
            # Stage 3: TTS Speech Synthesis
            tts_start = time.time()
            try:
                tts_result = await tts_service.synthesize_speech(result.response_text)
                result.tts_latency = time.time() - tts_start
                
                if "error" in tts_result:
                    result.error = tts_result["error"]
                    result.pipeline_latency = time.time() - pipeline_start
                    self._update_stats(result.pipeline_latency, False)
                    return result
                
                result.audio_data = tts_result["audio_data"]
                result.cached = tts_result.get("cached", False)
                
                # Generate audio file path and save
                result.audio_file_path = self._generate_audio_file_path(session_id)
                await self._save_audio_file(result.audio_data, result.audio_file_path)
                
            except Exception as e:
                result.error = f"TTS processing failed: {str(e)}"
                result.tts_latency = time.time() - tts_start
                result.pipeline_latency = time.time() - pipeline_start
                self._update_stats(result.pipeline_latency, False)
                return result
            
            # Stage 4: Store interaction in cache for future semantic reuse
            try:
                await self.rag_agent.store_interaction(
                    result.transcription, 
                    result.response_text, 
                    result.audio_file_path
                )
            except Exception as e:
                logger.warning(f"Failed to store streaming interaction in cache: {str(e)}")
            
            # Finalize results
            result.pipeline_latency = time.time() - pipeline_start
            result.models_used = {
                "stt": stt_result.get("model", "unknown"),
                "rag": "agno_agent",
                "tts": tts_result.get("model", "unknown")
            }
            
            self._update_stats(result.pipeline_latency, True)
            
            logger.info(f"Streaming pipeline completed in {result.pipeline_latency:.3f}s "
                       f"(STT: {result.stt_latency:.3f}s, RAG: {result.rag_latency:.3f}s, "
                       f"TTS: {result.tts_latency:.3f}s)")
            
            return result
            
        except Exception as e:
            result.error = f"Streaming pipeline failed: {str(e)}"
            result.pipeline_latency = time.time() - pipeline_start
            self._update_stats(result.pipeline_latency, False)
            log_error_with_context(logger, e, {
                "session_id": session_id,
                "chunks_count": len(audio_chunks),
                "total_audio_size": sum(len(chunk) for chunk in audio_chunks)
            })
            return result
    
    async def process_audio_stream(self, audio_stream: asyncio.StreamReader, session_id: str = None) -> PipelineResult:
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
            
            logger.info(f"Starting real-time audio stream processing for session {session_id}")
            
            # Collect audio chunks from stream
            audio_chunks = []
            async for chunk in stream_processor.process_audio_stream(audio_stream):
                audio_chunks.append(chunk)
                
                # Process chunks in batches for optimal performance
                if len(audio_chunks) >= 10:  # Process every 10 chunks
                    break
            
            if not audio_chunks:
                result.error = "No audio data received from stream"
                result.pipeline_latency = time.time() - pipeline_start
                self._update_stats(result.pipeline_latency, False)
                return result
            
            # Process the accumulated chunks using streaming pipeline
            return await self.process_streaming_voice(audio_chunks, session_id)
            
        except Exception as e:
            result.error = f"Stream processing failed: {str(e)}"
            result.pipeline_latency = time.time() - pipeline_start
            self._update_stats(result.pipeline_latency, False)
            log_error_with_context(logger, e, {"session_id": session_id})
            return result
    
    async def process_text_input(self, text: str, session_id: str = None) -> PipelineResult:
        """
        Process text input through RAG→TTS pipeline.
        
        Args:
            text: Input text to process
            session_id: Session identifier for tracking
            
        Returns:
            PipelineResult with text processing results
        """
        pipeline_start = time.time()
        result = PipelineResult()
        result.transcription = text  # Input text as "transcription"
        
        try:
            self.current_session_id = session_id
            self.performance_stats["total_requests"] += 1
            
            logger.info(f"Processing text input for session {session_id}")
            
            # Stage 1: RAG Agent Processing with Semantic Cache
            rag_start = time.time()
            try:
                rag_result = await self.rag_agent.process_query(text, session_id)
                result.rag_latency = time.time() - rag_start
                
                if "error" in rag_result:
                    result.error = rag_result["error"]
                    result.pipeline_latency = time.time() - pipeline_start
                    self._update_stats(result.pipeline_latency, False)
                    return result
                
                result.response_text = rag_result["response_text"]
                result.semantic_cache_hit = rag_result.get("cached", False)
                result.similarity_score = rag_result.get("similarity_score", 0.0)
                result.rag_used = rag_result.get("source") == "agent"
                result.source = rag_result.get("source", "pipeline")
                
                # If we got a cached audio file, load it and return early
                if result.semantic_cache_hit and "audio_file_path" in rag_result:
                    cached_audio = await self._load_cached_audio(rag_result["audio_file_path"])
                    if cached_audio:
                        result.audio_data = cached_audio
                        result.audio_file_path = rag_result["audio_file_path"]
                        result.cached = True
                        result.pipeline_latency = time.time() - pipeline_start
                        
                        self.performance_stats["cache_hits"] += 1
                        self._update_stats(result.pipeline_latency, True)
                        
                        logger.info(f"Text semantic cache hit: {result.similarity_score:.3f} similarity")
                        return result
                
                if result.rag_used:
                    self.performance_stats["rag_queries"] += 1
                
            except Exception as e:
                result.error = f"RAG processing failed: {str(e)}"
                result.rag_latency = time.time() - rag_start
                result.pipeline_latency = time.time() - pipeline_start
                self._update_stats(result.pipeline_latency, False)
                return result
            
            # Stage 2: TTS Speech Synthesis
            tts_start = time.time()
            try:
                tts_result = await tts_service.synthesize_speech(result.response_text)
                result.tts_latency = time.time() - tts_start
                
                if "error" in tts_result:
                    result.error = tts_result["error"]
                    result.pipeline_latency = time.time() - pipeline_start
                    self._update_stats(result.pipeline_latency, False)
                    return result
                
                result.audio_data = tts_result["audio_data"]
                result.cached = tts_result.get("cached", False)
                
                # Generate audio file path and save
                result.audio_file_path = self._generate_audio_file_path(session_id)
                await self._save_audio_file(result.audio_data, result.audio_file_path)
                
            except Exception as e:
                result.error = f"TTS processing failed: {str(e)}"
                result.tts_latency = time.time() - tts_start
                result.pipeline_latency = time.time() - pipeline_start
                self._update_stats(result.pipeline_latency, False)
                return result
            
            # Stage 3: Store interaction in cache for future semantic reuse
            try:
                await self.rag_agent.store_interaction(
                    text, 
                    result.response_text, 
                    result.audio_file_path
                )
            except Exception as e:
                logger.warning(f"Failed to store text interaction in cache: {str(e)}")
            
            # Finalize results
            result.pipeline_latency = time.time() - pipeline_start
            result.models_used = {
                "rag": "agno_agent",
                "tts": tts_result.get("model", "unknown")
            }
            
            self._update_stats(result.pipeline_latency, True)
            logger.info(f"Text processing completed in {result.pipeline_latency:.3f}s")
            
            return result
            
        except Exception as e:
            result.error = f"Text pipeline failed: {str(e)}"
            result.pipeline_latency = time.time() - pipeline_start
            self._update_stats(result.pipeline_latency, False)
            log_error_with_context(logger, e, {"session_id": session_id, "text_length": len(text)})
            return result
    
    async def _process_audio_chunks(self, audio_chunks: List[bytes]) -> bytes:
        """Combine and process streaming audio chunks for STT."""
        try:
            # Combine all chunks into a single audio stream
            combined_audio = b''.join(audio_chunks)
            
            # Process the combined audio for STT compatibility
            processed_audio = await audio_processor.process_audio_for_stt(combined_audio, "webm")
            
            logger.debug(f"Combined {len(audio_chunks)} chunks into {len(combined_audio)} bytes, "
                        f"processed to {len(processed_audio)} bytes")
            
            return processed_audio
            
        except Exception as e:
            log_error_with_context(logger, e, {
                "chunks_count": len(audio_chunks),
                "total_size": sum(len(chunk) for chunk in audio_chunks)
            })
            raise
    
    def _update_stats(self, latency: float, success: bool) -> None:
        """Update performance statistics."""
        self.performance_stats["latencies"].append(latency)
        
        if success:
            self.performance_stats["successful_requests"] += 1
        else:
            self.performance_stats["failed_requests"] += 1
        
        # Keep only last 100 latencies
        if len(self.performance_stats["latencies"]) > 100:
            self.performance_stats["latencies"] = self.performance_stats["latencies"][-100:]
        
        # Update average latency
        if self.performance_stats["latencies"]:
            self.performance_stats["avg_pipeline_latency"] = sum(self.performance_stats["latencies"]) / len(self.performance_stats["latencies"])
    
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
                if total_requests > 0 else 0
            ),
            "cache_hit_rate": (
                cache_hits / total_requests
                if total_requests > 0 else 0
            ),
            "rag_usage_rate": (
                rag_queries / total_requests
                if total_requests > 0 else 0
            ),
            "avg_pipeline_latency": self.performance_stats["avg_pipeline_latency"],
            "conversation_active": self.conversation_active,
            "current_session_id": self.current_session_id
        }
    
    def clear_conversation(self) -> None:
        """Clear conversation state and history."""
        llm_service.clear_conversation()
        self.conversation_active = False
        self.current_session_id = None
        logger.info("Pipeline conversation cleared")


# Global pipeline instance
voice_pipeline = VoicePipeline()