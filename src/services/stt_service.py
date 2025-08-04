"""
Speech-to-Text (STT) service for EchoAI voice chat system.

This module provides STT functionality using Hugging Face Whisper as the primary
service with OpenAI Whisper as a fallback for reliability and low latency.
"""

import asyncio
import io
import time
from typing import Optional, Dict, Any
import aiohttp
import openai
from transformers import pipeline
from src.utils.config import get_settings
from src.utils.logging import get_logger, log_performance, log_error_with_context
from src.utils.audio import audio_processor


logger = get_logger(__name__)
settings = get_settings()


class STTService:
    """Handles Speech-to-Text conversion with fallback mechanisms."""
    
    def __init__(self):
        self.hf_api_key = settings.huggingface_api_key
        self.openai_api_key = settings.openai_api_key
        self.default_model = settings.default_stt_model
        self.fallback_model = settings.fallback_stt_model
        self.timeout = settings.stt_timeout
        
        # Initialize OpenAI client
        self.openai_client = openai.AsyncOpenAI(api_key=self.openai_api_key)
        
        # Performance monitoring
        self.hf_latency = []
        self.openai_latency = []
        self.fallback_count = 0
        
        # Model warm-up flag
        self._models_warmed_up = False
    
    async def warm_up_models(self) -> None:
        """Pre-load models to reduce latency on first use."""
        if self._models_warmed_up:
            return
        
        try:
            logger.info("Warming up STT models...")
            
            # Warm up Hugging Face model
            if "huggingface" in self.default_model.lower():
                await self._warm_up_hf_model()
            
            # Warm up OpenAI model
            await self._warm_up_openai_model()
            
            self._models_warmed_up = True
            logger.info("STT models warmed up successfully")
            
        except Exception as e:
            logger.warning(f"Failed to warm up models: {str(e)}")
    
    async def _warm_up_hf_model(self) -> None:
        """Warm up Hugging Face Whisper model."""
        try:
            # Create a small test audio (silence)
            test_audio = self._create_test_audio()
            
            # Test transcription
            result = await self._transcribe_with_hf(test_audio)
            logger.debug(f"HF model warm-up test result: {result}")
            
        except Exception as e:
            logger.warning(f"Failed to warm up HF model: {str(e)}")
    
    async def _warm_up_openai_model(self) -> None:
        """Warm up OpenAI Whisper model."""
        try:
            # Create a small test audio (silence)
            test_audio = self._create_test_audio()
            
            # Test transcription
            result = await self._transcribe_with_openai(test_audio)
            logger.debug(f"OpenAI model warm-up test result: {result}")
            
        except Exception as e:
            logger.warning(f"Failed to warm up OpenAI model: {str(e)}")
    
    def _create_test_audio(self) -> bytes:
        """Create a small test audio file for model warm-up."""
        import wave
        import numpy as np
        
        # Create 1 second of silence
        sample_rate = 16000
        duration = 1.0
        samples = int(sample_rate * duration)
        
        # Generate silence (zeros)
        audio_data = np.zeros(samples, dtype=np.int16)
        
        # Create WAV file in memory
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data.tobytes())
        
        buffer.seek(0)
        return buffer.getvalue()
    
    @log_performance
    async def transcribe_audio(self, audio_data: bytes, use_fallback: bool = False) -> Dict[str, Any]:
        """
        Transcribe audio using STT services with fallback logic.
        
        Args:
            audio_data: Raw audio bytes (WAV format)
            use_fallback: Force use of fallback model
            
        Returns:
            Dict containing transcription result and metadata
        """
        try:
            # Process audio for STT
            processed_audio = await audio_processor.process_audio_for_stt(audio_data)
            
            # Choose model based on fallback flag
            if use_fallback or "openai" in self.default_model.lower():
                return await self._transcribe_with_openai(processed_audio)
            else:
                return await self._transcribe_with_hf(processed_audio)
                
        except Exception as e:
            logger.error(f"Primary STT failed, trying fallback: {str(e)}")
            return await self._transcribe_with_openai(processed_audio)
    
    async def _transcribe_with_hf(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Transcribe using Hugging Face Whisper.
        
        Args:
            audio_data: Processed audio bytes
            
        Returns:
            Dict with transcription result and metadata
        """
        start_time = time.time()
        
        try:
            # Use Hugging Face Inference API
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.hf_api_key}",
                    "Content-Type": "audio/wav"
                }
                
                async with session.post(
                    f"https://api-inference.huggingface.co/models/{self.default_model}",
                    headers=headers,
                    data=audio_data,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        latency = time.time() - start_time
                        self.hf_latency.append(latency)
                        
                        transcription = result.get("text", "").strip()
                        
                        logger.info(f"HF STT completed in {latency:.3f}s: '{transcription[:50]}...'")
                        
                        return {
                            "text": transcription,
                            "model": self.default_model,
                            "latency": latency,
                            "confidence": result.get("confidence", 0.0),
                            "language": result.get("language", "en")
                        }
                    else:
                        raise Exception(f"HF API error: {response.status}")
                        
        except Exception as e:
            latency = time.time() - start_time
            log_error_with_context(logger, e, {"model": self.default_model, "latency": latency})
            raise
    
    async def _transcribe_with_openai(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Transcribe using OpenAI Whisper.
        
        Args:
            audio_data: Processed audio bytes
            
        Returns:
            Dict with transcription result and metadata
        """
        start_time = time.time()
        
        try:
            # Create file-like object for OpenAI API
            audio_file = io.BytesIO(audio_data)
            audio_file.name = "audio.wav"
            
            # Call OpenAI Whisper API
            response = await self.openai_client.audio.transcriptions.create(
                model=self.fallback_model,
                file=audio_file,
                response_format="verbose_json"
            )
            
            latency = time.time() - start_time
            self.openai_latency.append(latency)
            self.fallback_count += 1
            
            transcription = response.text.strip()
            
            logger.info(f"OpenAI STT completed in {latency:.3f}s: '{transcription[:50]}...'")
            
            return {
                "text": transcription,
                "model": self.fallback_model,
                "latency": latency,
                "confidence": getattr(response, 'confidence', 0.0),
                "language": getattr(response, 'language', 'en'),
                "fallback_used": True
            }
            
        except Exception as e:
            latency = time.time() - start_time
            log_error_with_context(logger, e, {"model": self.fallback_model, "latency": latency})
            raise
    
    async def transcribe_chunked_audio(self, audio_chunks: list) -> str:
        """
        Transcribe audio processed in chunks for lower latency.
        
        Args:
            audio_chunks: List of audio chunk bytes
            
        Returns:
            str: Combined transcription text
        """
        transcriptions = []
        
        for i, chunk in enumerate(audio_chunks):
            try:
                result = await self.transcribe_audio(chunk)
                transcriptions.append(result["text"])
                logger.debug(f"Chunk {i+1} transcribed: '{result['text'][:30]}...'")
                
            except Exception as e:
                logger.error(f"Failed to transcribe chunk {i+1}: {str(e)}")
                transcriptions.append("")  # Empty string for failed chunks
        
        # Combine transcriptions
        combined_text = " ".join(transcriptions).strip()
        logger.info(f"Combined transcription from {len(audio_chunks)} chunks: '{combined_text[:100]}...'")
        
        return combined_text
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for monitoring.
        
        Returns:
            Dict with performance metrics
        """
        return {
            "hf_average_latency": sum(self.hf_latency) / len(self.hf_latency) if self.hf_latency else 0,
            "openai_average_latency": sum(self.openai_latency) / len(self.openai_latency) if self.openai_latency else 0,
            "fallback_count": self.fallback_count,
            "total_transcriptions": len(self.hf_latency) + len(self.openai_latency)
        }


# Global STT service instance
stt_service = STTService() 