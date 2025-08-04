"""
VoiceCloneAgent - Agno agent for orchestrating the AI voice chat pipeline.

This module defines the main agent that coordinates Speech-to-Text, Language Model,
and Text-to-Speech services to create a seamless voice conversation experience.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from agno import Agent, Tool
from src.services.stt_service import stt_service
from src.services.llm_service import llm_service
from src.services.tts_service import tts_service
from src.utils.audio_utils import audio_processor
from src.utils.logging import get_logger, log_performance, PerformanceMonitor


logger = get_logger(__name__)


class VoiceCloneAgent(Agent):
    """Agno agent for orchestrating the complete voice chat pipeline."""
    
    def __init__(self):
        super().__init__(
            name="VoiceCloneAgent",
            description="Orchestrates STT→LLM→TTS pipeline for real-time voice chat"
        )
        
        # Initialize performance monitor
        self.performance_monitor = PerformanceMonitor("VoiceCloneAgent")
        
        # Pipeline state
        self.conversation_active = False
        self.current_session_id = None
        
        # Register tools
        self.register_tools([
            self.stt_tool,
            self.llm_tool,
            self.tts_tool,
            self.process_audio_tool,
            self.generate_response_tool,
            self.synthesize_speech_tool
        ])
    
    @Tool("Transcribe audio using STT service")
    async def stt_tool(self, audio_data: bytes, use_fallback: bool = False) -> Dict[str, Any]:
        """
        Transcribe audio using STT service with fallback.
        
        Args:
            audio_data: Raw audio bytes
            use_fallback: Use fallback model
            
        Returns:
            Dict with transcription result
        """
        try:
            result = await stt_service.transcribe_audio(audio_data, use_fallback)
            self.performance_monitor.record_metric("stt_latency", result["latency"])
            return result
        except Exception as e:
            logger.error(f"STT tool failed: {str(e)}")
            raise
    
    @Tool("Generate LLM response")
    async def llm_tool(self, user_input: str, use_fallback: bool = False) -> Dict[str, Any]:
        """
        Generate LLM response with fallback.
        
        Args:
            user_input: User's input text
            use_fallback: Use fallback model
            
        Returns:
            Dict with LLM response
        """
        try:
            result = await llm_service.generate_response(user_input, use_fallback)
            self.performance_monitor.record_metric("llm_latency", result["latency"])
            return result
        except Exception as e:
            logger.error(f"LLM tool failed: {str(e)}")
            raise
    
    @Tool("Synthesize speech using TTS service")
    async def tts_tool(self, text: str, use_streaming: bool = True) -> Dict[str, Any]:
        """
        Synthesize speech using TTS service.
        
        Args:
            text: Text to synthesize
            use_streaming: Use streaming synthesis
            
        Returns:
            Dict with audio data
        """
        try:
            result = await tts_service.synthesize_speech(text, use_streaming)
            self.performance_monitor.record_metric("tts_latency", result["latency"])
            return result
        except Exception as e:
            logger.error(f"TTS tool failed: {str(e)}")
            raise
    
    @Tool("Process audio for STT compatibility")
    async def process_audio_tool(self, audio_data: bytes, format: str = "webm") -> bytes:
        """
        Process audio for optimal STT performance.
        
        Args:
            audio_data: Raw audio bytes
            format: Input audio format
            
        Returns:
            bytes: Processed audio
        """
        try:
            processed_audio = await audio_processor.process_audio_for_stt(audio_data, format)
            return processed_audio
        except Exception as e:
            logger.error(f"Audio processing tool failed: {str(e)}")
            raise
    
    @Tool("Generate complete response pipeline")
    async def generate_response_tool(self, user_input: str) -> Dict[str, Any]:
        """
        Generate complete response using LLM.
        
        Args:
            user_input: User's input text
            
        Returns:
            Dict with response text and metadata
        """
        try:
            result = await llm_service.generate_response(user_input)
            return {
                "response_text": result["text"],
                "model_used": result["model"],
                "latency": result["latency"],
                "tokens_used": result.get("tokens_used", 0)
            }
        except Exception as e:
            logger.error(f"Response generation tool failed: {str(e)}")
            raise
    
    @Tool("Synthesize complete speech response")
    async def synthesize_speech_tool(self, text: str) -> Dict[str, Any]:
        """
        Synthesize complete speech from text.
        
        Args:
            text: Text to synthesize
            
        Returns:
            Dict with audio data and metadata
        """
        try:
            result = await tts_service.synthesize_speech(text)
            return {
                "audio_data": result["audio_data"],
                "model_used": result["model"],
                "latency": result["latency"],
                "cached": result.get("cached", False)
            }
        except Exception as e:
            logger.error(f"Speech synthesis tool failed: {str(e)}")
            raise
    
    @log_performance
    async def process_voice_input(self, audio_data: bytes, session_id: str = None) -> Dict[str, Any]:
        """
        Process complete voice input pipeline: STT → LLM → TTS.
        
        Args:
            audio_data: Raw audio bytes
            session_id: Session identifier
            
        Returns:
            Dict with complete pipeline result
        """
        pipeline_start = time.time()
        
        try:
            self.current_session_id = session_id
            self.conversation_active = True
            
            logger.info(f"Starting voice processing pipeline for session {session_id}")
            
            # Step 1: Process audio for STT
            processed_audio = await audio_processor.process_audio_for_stt(audio_data)
            
            # Step 2: Transcribe audio
            stt_result = await stt_service.transcribe_audio(processed_audio)
            transcription = stt_result["text"]
            
            if not transcription.strip():
                return {
                    "error": "No speech detected",
                    "transcription": "",
                    "response_text": "",
                    "audio_data": b"",
                    "pipeline_latency": time.time() - pipeline_start
                }
            
            # Step 3: Generate LLM response
            llm_result = await llm_service.generate_response(transcription)
            response_text = llm_result["text"]
            
            # Step 4: Synthesize speech
            tts_result = await tts_service.synthesize_speech(response_text)
            audio_data = tts_result["audio_data"]
            
            # Calculate total pipeline latency
            pipeline_latency = time.time() - pipeline_start
            
            # Record performance metrics
            self.performance_monitor.record_metric("pipeline_latency", pipeline_latency)
            self.performance_monitor.record_metric("stt_latency", stt_result["latency"])
            self.performance_monitor.record_metric("llm_latency", llm_result["latency"])
            self.performance_monitor.record_metric("tts_latency", tts_result["latency"])
            
            logger.info(f"Pipeline completed in {pipeline_latency:.3f}s: '{transcription[:30]}...' → '{response_text[:30]}...'")
            
            return {
                "transcription": transcription,
                "response_text": response_text,
                "audio_data": audio_data,
                "pipeline_latency": pipeline_latency,
                "stt_latency": stt_result["latency"],
                "llm_latency": llm_result["latency"],
                "tts_latency": tts_result["latency"],
                "models_used": {
                    "stt": stt_result["model"],
                    "llm": llm_result["model"],
                    "tts": tts_result["model"]
                }
            }
            
        except Exception as e:
            pipeline_latency = time.time() - pipeline_start
            logger.error(f"Pipeline failed after {pipeline_latency:.3f}s: {str(e)}")
            raise
    
    async def process_streaming_voice(self, audio_chunks: List[bytes], session_id: str = None) -> Dict[str, Any]:
        """
        Process voice input in streaming chunks for lower latency.
        
        Args:
            audio_chunks: List of audio chunk bytes
            session_id: Session identifier
            
        Returns:
            Dict with complete pipeline result
        """
        pipeline_start = time.time()
        
        try:
            self.current_session_id = session_id
            self.conversation_active = True
            
            logger.info(f"Starting streaming voice processing for session {session_id}")
            
            # Process audio chunks
            processed_chunks = []
            for chunk in audio_chunks:
                processed_chunk = await audio_processor.process_audio_for_stt(chunk)
                processed_chunks.append(processed_chunk)
            
            # Transcribe chunks
            transcription = await stt_service.transcribe_chunked_audio(processed_chunks)
            
            if not transcription.strip():
                return {
                    "error": "No speech detected in chunks",
                    "transcription": "",
                    "response_text": "",
                    "audio_data": b"",
                    "pipeline_latency": time.time() - pipeline_start
                }
            
            # Generate response
            llm_result = await llm_service.generate_response(transcription)
            response_text = llm_result["text"]
            
            # Synthesize speech
            tts_result = await tts_service.synthesize_speech(response_text)
            audio_data = tts_result["audio_data"]
            
            pipeline_latency = time.time() - pipeline_start
            
            logger.info(f"Streaming pipeline completed in {pipeline_latency:.3f}s")
            
            return {
                "transcription": transcription,
                "response_text": response_text,
                "audio_data": audio_data,
                "pipeline_latency": pipeline_latency,
                "chunks_processed": len(audio_chunks)
            }
            
        except Exception as e:
            pipeline_latency = time.time() - pipeline_start
            logger.error(f"Streaming pipeline failed after {pipeline_latency:.3f}s: {str(e)}")
            raise
    
    async def warm_up_services(self) -> None:
        """Warm up all services for optimal performance."""
        try:
            logger.info("Warming up all services...")
            
            # Warm up services in parallel
            await asyncio.gather(
                stt_service.warm_up_models(),
                llm_service.warm_up_models(),
                tts_service.warm_up_cache()
            )
            
            logger.info("All services warmed up successfully")
            
        except Exception as e:
            logger.warning(f"Service warm-up failed: {str(e)}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive performance summary.
        
        Returns:
            Dict with performance metrics from all services
        """
        stt_stats = stt_service.get_performance_stats()
        llm_stats = llm_service.get_performance_stats()
        tts_stats = tts_service.get_performance_stats()
        
        return {
            "agent": {
                "conversation_active": self.conversation_active,
                "current_session_id": self.current_session_id
            },
            "stt": stt_stats,
            "llm": llm_stats,
            "tts": tts_stats,
            "performance_monitor": {
                "metrics": self.performance_monitor.metrics
            }
        }
    
    def clear_conversation(self) -> None:
        """Clear conversation state and history."""
        llm_service.clear_conversation()
        self.conversation_active = False
        self.current_session_id = None
        logger.info("Conversation cleared")


# Global agent instance
voice_clone_agent = VoiceCloneAgent() 