"""
Speech-to-Text service for EchoAI voice chat system.

This module provides STT functionality using Hugging Face Whisper as primary
and OpenAI Whisper as fallback, with streaming audio support.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
import aiohttp
import openai
from transformers import pipeline

from src.utils.config import get_settings
from src.utils.logging import get_logger, log_performance, log_error_with_context
from src.utils.audio import audio_processor, stream_processor


logger = get_logger(__name__)
settings = get_settings()


class STTService:
    """Speech-to-Text service with streaming support."""
    
    def __init__(self):
        self.hf_pipeline = None
        self.openai_client = None
        self.models_warmed_up = False
        self.performance_stats = {
            "total_transcriptions": 0,
            "successful_transcriptions": 0,
            "failed_transcriptions": 0,
            "avg_latency": 0.0,
            "latencies": []
        }
    
    async def warm_up_models(self) -> None:
        """Warm up STT models for optimal performance."""
        try:
            logger.info("Warming up STT models...")
            
            # Warm up Hugging Face model
            if settings.HUGGINGFACE_API_KEY:
                try:
                    self.hf_pipeline = pipeline(
                        "automatic-speech-recognition",
                        model=settings.DEFAULT_STT_MODEL,
                        token=settings.HUGGINGFACE_API_KEY
                    )
                    logger.info(f"Hugging Face model {settings.DEFAULT_STT_MODEL} loaded")
                except Exception as e:
                    logger.warning(f"Failed to load Hugging Face model: {str(e)}")
            
            # Warm up OpenAI client
            if settings.OPENAI_API_KEY:
                try:
                    self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                    logger.info("OpenAI client initialized")
                except Exception as e:
                    logger.warning(f"Failed to initialize OpenAI client: {str(e)}")
            
            self.models_warmed_up = True
            logger.info("STT models warmed up successfully")
            
        except Exception as e:
            logger.error(f"Failed to warm up STT models: {str(e)}")
    
    async def _transcribe_with_hf(self, audio_data: bytes) -> Dict[str, Any]:
        """Transcribe audio using Hugging Face Whisper."""
        start_time = time.time()
        
        try:
            if not self.hf_pipeline:
                raise Exception("Hugging Face model not loaded")
            
            # Process audio for HF model
            processed_audio = await audio_processor.process_audio_for_stt(audio_data, "wav")
            
            # Transcribe
            result = self.hf_pipeline(processed_audio)
            transcription = result["text"].strip()
            
            latency = time.time() - start_time
            
            logger.debug(f"HF transcription completed in {latency:.3f}s")
            
            return {
                "text": transcription,
                "model": "huggingface_whisper",
                "latency": latency,
                "confidence": result.get("confidence", 0.0)
            }
            
        except Exception as e:
            latency = time.time() - start_time
            log_error_with_context(logger, e, {"method": "_transcribe_with_hf", "latency": latency})
            raise
    
    async def _transcribe_with_openai(self, audio_data: bytes) -> Dict[str, Any]:
        """Transcribe audio using OpenAI Whisper."""
        start_time = time.time()
        
        try:
            if not self.openai_client:
                raise Exception("OpenAI client not initialized")
            
            # Process audio for OpenAI
            processed_audio = await audio_processor.process_audio_for_stt(audio_data, "wav")
            
            # Transcribe using OpenAI
            response = await self.openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=("audio.wav", processed_audio, "audio/wav"),
                response_format="json"
            )
            
            transcription = response.text.strip()
            latency = time.time() - start_time
            
            logger.debug(f"OpenAI transcription completed in {latency:.3f}s")
            
            return {
                "text": transcription,
                "model": "openai_whisper",
                "latency": latency,
                "confidence": 1.0  # OpenAI doesn't provide confidence scores
            }
            
        except Exception as e:
            latency = time.time() - start_time
            log_error_with_context(logger, e, {"method": "_transcribe_with_openai", "latency": latency})
            raise
    
    @log_performance
    async def transcribe_audio(self, audio_data: bytes, use_fallback: bool = False) -> Dict[str, Any]:
        """
        Transcribe audio using primary or fallback STT service.
        
        Args:
            audio_data: Audio data in bytes
            use_fallback: Whether to use fallback service
            
        Returns:
            Dict with transcription result
        """
        start_time = time.time()
        
        try:
            self.performance_stats["total_transcriptions"] += 1
            
            # Try primary service first (unless fallback is explicitly requested)
            if not use_fallback and self.hf_pipeline:
                try:
                    result = await self._transcribe_with_hf(audio_data)
                    self._update_stats(result["latency"], True)
                    return result
                except Exception as e:
                    logger.warning(f"Primary STT failed, trying fallback: {str(e)}")
            
            # Use fallback service
            if self.openai_client:
                try:
                    result = await self._transcribe_with_openai(audio_data)
                    self._update_stats(result["latency"], True)
                    return result
                except Exception as e:
                    logger.error(f"Fallback STT also failed: {str(e)}")
                    self._update_stats(time.time() - start_time, False)
                    return {"error": f"STT failed: {str(e)}"}
            else:
                error_msg = "No STT services available"
                self._update_stats(time.time() - start_time, False)
                return {"error": error_msg}
                
        except Exception as e:
            latency = time.time() - start_time
            self._update_stats(latency, False)
            log_error_with_context(logger, e, {"method": "transcribe_audio", "audio_size": len(audio_data)})
            return {"error": f"Transcription failed: {str(e)}"}
    
    async def transcribe_chunked_audio(self, audio_chunks: List[bytes]) -> str:
        """
        Transcribe audio from multiple chunks for streaming support.
        
        Args:
            audio_chunks: List of audio chunk bytes
            
        Returns:
            Combined transcription text
        """
        try:
            logger.debug(f"Transcribing {len(audio_chunks)} audio chunks")
            
            if not audio_chunks:
                return ""
            
            # Combine chunks if they're small
            if len(audio_chunks) == 1:
                result = await self.transcribe_audio(audio_chunks[0])
                return result.get("text", "") if "error" not in result else ""
            
            # For multiple chunks, process them efficiently
            combined_audio = b''.join(audio_chunks)
            
            # Use AudioStreamProcessor to optimize chunk processing
            optimized_chunks = []
            for chunk in audio_chunks:
                # Create optimal chunks using AudioStreamProcessor
                chunk_generator = stream_processor.create_audio_chunks(chunk, chunk_size=1024)
                optimized_chunk = b''.join(chunk_generator)
                optimized_chunks.append(optimized_chunk)
            
            # Combine optimized chunks
            final_audio = b''.join(optimized_chunks)
            
            # Transcribe combined audio
            result = await self.transcribe_audio(final_audio)
            
            if "error" in result:
                logger.error(f"Chunked transcription failed: {result['error']}")
                return ""
            
            transcription = result["text"]
            logger.debug(f"Chunked transcription completed: '{transcription[:50]}...'")
            
            return transcription
            
        except Exception as e:
            log_error_with_context(logger, e, {"method": "transcribe_chunked_audio", "chunks_count": len(audio_chunks)})
            return ""
    
    async def transcribe_streaming_audio(self, audio_stream: asyncio.StreamReader) -> str:
        """
        Transcribe real-time audio stream for ultra-low latency.
        
        Args:
            audio_stream: Async stream reader for audio data
            
        Returns:
            Transcription text
        """
        try:
            logger.debug("Starting streaming audio transcription")
            
            # Use AudioStreamProcessor to handle the stream
            audio_chunks = []
            async for chunk in stream_processor.process_audio_stream(audio_stream):
                audio_chunks.append(chunk)
                
                # Process in batches for optimal performance
                if len(audio_chunks) >= 5:  # Process every 5 chunks
                    break
            
            if not audio_chunks:
                return ""
            
            # Transcribe accumulated chunks
            return await self.transcribe_chunked_audio(audio_chunks)
            
        except Exception as e:
            log_error_with_context(logger, e, {"method": "transcribe_streaming_audio"})
            return ""
    
    def _update_stats(self, latency: float, success: bool) -> None:
        """Update performance statistics."""
        self.performance_stats["latencies"].append(latency)
        
        if success:
            self.performance_stats["successful_transcriptions"] += 1
        else:
            self.performance_stats["failed_transcriptions"] += 1
        
        # Keep only last 100 latencies
        if len(self.performance_stats["latencies"]) > 100:
            self.performance_stats["latencies"] = self.performance_stats["latencies"][-100:]
        
        # Update average latency
        if self.performance_stats["latencies"]:
            self.performance_stats["avg_latency"] = sum(self.performance_stats["latencies"]) / len(self.performance_stats["latencies"])
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            "total_transcriptions": self.performance_stats["total_transcriptions"],
            "successful_transcriptions": self.performance_stats["successful_transcriptions"],
            "failed_transcriptions": self.performance_stats["failed_transcriptions"],
            "avg_latency": self.performance_stats["avg_latency"],
            "models_warmed_up": self.models_warmed_up,
            "primary_model": "huggingface_whisper" if self.hf_pipeline else "none",
            "fallback_model": "openai_whisper" if self.openai_client else "none"
        }


# Global service instance
stt_service = STTService() 