"""
Speech-to-Text service for EchoAI voice chat system.

This module provides STT functionality using Hugging Face Whisper as primary
and OpenAI Whisper as fallback, with streaming audio support.
"""
import os
import io
import asyncio
import time
from typing import Dict, Any, List, Optional
import aiohttp
import openai
from faster_whisper import WhisperModel
import wave
from imageio_ffmpeg import get_ffmpeg_exe
import soundfile as sf
import torch
import numpy as np
from src.utils import get_settings
from src.utils import get_logger, log_performance, log_error_with_context
from src.utils.audio import audio_processor, audio_stream_processor
from src.constants import ModelName, LATENCY_WINDOW_SIZE, STREAMING_BATCH_SIZE
from src.exceptions import STTError


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
        
        #to ensure any library (like Hugging Face) that calls ffmpeg without a full path will still find it.
        # Ensure ffmpeg is discoverable by libs expecting it on PATH
        try:
            ffmpeg_path = get_ffmpeg_exe()
            ffmpeg_dir = os.path.dirname(ffmpeg_path)
            path_parts = os.environ.get("PATH", "").split(os.pathsep)
            if ffmpeg_dir not in path_parts:
                os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
            logger.info(f"FFmpeg available at: {ffmpeg_path}")
        except Exception as e:
            logger.warning(f"Could not initialize ffmpeg from imageio-ffmpeg: {e}")
        
        
    
    async def warm_up_models(self) -> None:
        """Warm up STT models for optimal performance."""
        try:
            logger.info("Warming up STT models...")
            
            # Dynamic hardware detection
            if torch.cuda.is_available():
                device = "cuda"
                compute_type = "float16"  # GPU-friendly
                model_size = "medium"     # use larger model for accuracy on GPU
                logger.info("CUDA detected — using GPU with float16 and medium model")
            else:
                device = "cpu"
                compute_type = "int8"     # fastest for CPU
                model_size = "small"      # small model for speed on CPU
                logger.info("No GPU detected — using CPU with int8 and small model")

            # Load Faster-Whisper model (offload to thread — it's a heavy sync call)
            try:
                self.fw_model = await asyncio.to_thread(
                    WhisperModel,
                    model_size,   # dynamic based on hardware
                    device=device,
                    compute_type=compute_type,
                )
                logger.info(f"Faster-Whisper model loaded ({model_size}, {device}, {compute_type})")
            except Exception as e:
                logger.warning(f"Failed to load Faster-Whisper model: {e}")
                
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
    
    async def _transcribe_with_whisper(self, audio_data: bytes) -> Dict[str, Any]:
        """Transcribe audio using Faster-Whisper (local)."""
        start_time = time.time()
        try:
            if not self.fw_model:
                raise STTError("Faster-Whisper model not loaded")

            # Process audio to standard mono/16k WAV
            processed_audio = await audio_processor.process_audio_for_stt(audio_data, "wav")

            # Decode WAV -> float32 mono [-1, 1]
            with wave.open(io.BytesIO(processed_audio), "rb") as w:
                sr = w.getframerate()
                ch = w.getnchannels()
                sw = w.getsampwidth()
                frames = w.readframes(w.getnframes())
            if sw != 2:
                raise ValueError(f"Expected 16-bit WAV, got {sw*8}-bit")
            arr = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            if ch > 1:
                arr = arr.reshape(-1, ch).mean(axis=1)

            # Transcribe with Faster-Whisper
            segments, info = self.fw_model.transcribe(
                arr,
                beam_size=5,
                language="en",  # set None for auto-detect
            )
            text = " ".join(seg.text for seg in segments).strip()

            latency = time.time() - start_time
            logger.debug(f"Faster-Whisper transcription completed in {latency:.3f}s")

            return {
                "text": text,
                "model": ModelName.FASTER_WHISPER_SMALL,
                "latency": latency,
                "confidence": 1.0  # FW doesn't return confidence
            }
        except Exception as e:
            latency = time.time() - start_time
            log_error_with_context(logger, e, {"method": "_transcribe_with_whisper", "latency": latency})
            raise
        
    
    async def _transcribe_with_openai(self, audio_data: bytes) -> Dict[str, Any]:
        """Transcribe audio using OpenAI Whisper."""
        start_time = time.time()
        
        try:
            if not self.openai_client:
                raise STTError("OpenAI client not initialized")
            
            # Process audio for OpenAI
            processed_audio = await audio_processor.process_audio_for_stt(audio_data, "wav")
            
            # Transcribe using OpenAI
            file_obj = io.BytesIO(processed_audio)
            file_obj.name = "audio.wav"  # OpenAI SDK reads filename from file-like

            response = await self.openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=file_obj,
                response_format="json",
            )
            
            transcription = (getattr(response, "text", "") or "").strip()
            latency = time.time() - start_time
            
            logger.debug(f"OpenAI transcription completed in {latency:.3f}s")
            
            return {
                "text": transcription,
                "model": ModelName.OPENAI_WHISPER,
                "latency": latency,
                "confidence": 1.0  # OpenAI doesn't provide confidence scores
            }
            
        except Exception as e:
            latency = time.time() - start_time
            log_error_with_context(logger, e, {"method": "_transcribe_with_openai", "latency": latency})
            raise
    
    @log_performance
    async def transcribe_audio(self, audio_data: bytes, *, use_fallback: bool = False) -> Dict[str, Any]:
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
            if not use_fallback:# and self.hf_pipeline:
                try:
                    result = await self._transcribe_with_whisper(audio_data)
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
                chunk_generator = audio_stream_processor.create_audio_chunks(chunk, chunk_size=1024)
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
            async for chunk in audio_stream_processor.process_audio_stream(audio_stream):
                audio_chunks.append(chunk)
                
                # Process in batches for optimal performance
                if len(audio_chunks) >= STREAMING_BATCH_SIZE:
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
        if len(self.performance_stats["latencies"]) > LATENCY_WINDOW_SIZE:
            self.performance_stats["latencies"] = self.performance_stats["latencies"][-LATENCY_WINDOW_SIZE:]
        
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
            "primary_model": ModelName.FASTER_WHISPER_SMALL if self.hf_pipeline else ModelName.NONE,
            "fallback_model": ModelName.OPENAI_WHISPER if self.openai_client else ModelName.NONE
        }


# Global service instance
stt_service = STTService() 