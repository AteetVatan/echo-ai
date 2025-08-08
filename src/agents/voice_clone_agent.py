"""
Voice Clone Agent for EchoAI voice chat system.

This module defines the main agent that orchestrates STT, LLM, and TTS services
for real-time voice chat with streaming audio support.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from agno.agent import Agent
from agno.tools import tool

from src.services.stt_service import stt_service
from src.services.llm_service import llm_service
from src.services.tts_service import tts_service
from src.utils.audio import audio_processor, stream_processor
from src.utils import get_logger, log_performance, log_error_with_context


logger = get_logger(__name__)


class VoiceCloneAgent(Agent):
    """Main agent for orchestrating voice chat pipeline with streaming support."""
    
    def __init__(self):
        super().__init__(
            tools=[
                self.stt_tool,
                self.llm_tool,
                self.tts_tool,
                self.process_audio_tool,
                self.generate_response_tool,
                self.synthesize_speech_tool,
                self.process_streaming_audio_tool,
            ]
        )
        self.conversation_active = False
        self.current_session_id = None
        self.performance_monitor = {
            "metrics": {},
            "session_stats": {}
        }
        

    
    @tool("Transcribe audio using STT service")
    async def stt_tool(self, audio_data: bytes, use_fallback: bool = False) -> Dict[str, Any]:
        """
        Transcribe audio to text using STT service.
        
        Args:
            audio_data: Audio data in bytes
            use_fallback: Whether to use fallback STT service
            
        Returns:
            Dict with transcription result
        """
        try:
            result = await stt_service.transcribe_audio(audio_data, use_fallback)
            return result
        except Exception as e:
            log_error_with_context(logger, e, {"tool": "stt_tool", "audio_size": len(audio_data)})
            return {"error": f"STT failed: {str(e)}"}
    
    @tool("Generate LLM response")
    async def llm_tool(self, user_input: str, use_fallback: bool = False) -> Dict[str, Any]:
        """
        Generate response using LLM service.
        
        Args:
            user_input: User input text
            use_fallback: Whether to use fallback LLM service
            
        Returns:
            Dict with LLM response
        """
        try:
            result = await llm_service.generate_response(user_input, use_fallback)
            return result
        except Exception as e:
            log_error_with_context(logger, e, {"tool": "llm_tool", "input_length": len(user_input)})
            return {"error": f"LLM failed: {str(e)}"}
    
    @tool("Synthesize speech using TTS service")
    async def tts_tool(self, text: str, use_streaming: bool = True) -> Dict[str, Any]:
        """
        Synthesize speech using TTS service.
        
        Args:
            text: Text to synthesize
            use_streaming: Whether to use streaming TTS
            
        Returns:
            Dict with TTS result
        """
        try:
            result = await tts_service.synthesize_speech(text, use_streaming)
            return result
        except Exception as e:
            log_error_with_context(logger, e, {"tool": "tts_tool", "text_length": len(text)})
            return {"error": f"TTS failed: {str(e)}"}
    
    @tool("Process audio for STT compatibility")
    async def process_audio_tool(self, audio_data: bytes, format: str = "webm") -> bytes:
        """
        Process audio data for STT compatibility.
        
        Args:
            audio_data: Raw audio data
            format: Audio format
            
        Returns:
            Processed audio data
        """
        try:
            processed_audio = await audio_processor.process_audio_for_stt(audio_data, format)
            return processed_audio
        except Exception as e:
            log_error_with_context(logger, e, {"tool": "process_audio_tool", "format": format})
            raise
    
    @tool("Process streaming audio chunks")
    async def process_streaming_audio_tool(self, audio_chunks: List[bytes]) -> List[bytes]:
        """
        Process streaming audio chunks for optimal STT performance.
        
        Args:
            audio_chunks: List of audio chunk bytes
            
        Returns:
            List of processed audio chunks
        """
        try:
            processed_chunks = []
            for chunk in audio_chunks:
                # Use AudioStreamProcessor to create optimal chunks
                chunk_generator = stream_processor.create_audio_chunks(chunk, chunk_size=1024)
                processed_chunk = b''.join(chunk_generator)
                processed_chunks.append(processed_chunk)
            
            logger.debug(f"Processed {len(audio_chunks)} audio chunks for streaming")
            return processed_chunks
        except Exception as e:
            log_error_with_context(logger, e, {"tool": "process_streaming_audio_tool", "chunks_count": len(audio_chunks)})
            raise
    
    @tool("Generate complete response pipeline")
    async def generate_response_tool(self, user_input: str) -> Dict[str, Any]:
        """
        Generate complete response for text input.
        
        Args:
            user_input: User input text
            
        Returns:
            Dict with complete response
        """
        pipeline_start = time.time()
        
        try:
            # Add to conversation history
            llm_service.add_to_conversation("user", user_input)
            
            # Generate response
            llm_result = await llm_service.generate_response(user_input)
            
            if "error" in llm_result:
                return llm_result
            
            response_text = llm_result["text"]
            llm_latency = llm_result["latency"]
            
            # Add response to conversation
            llm_service.add_to_conversation("assistant", response_text)
            
            pipeline_latency = time.time() - pipeline_start
            
            return {
                "response_text": response_text,
                "latency": llm_latency,
                "pipeline_latency": pipeline_latency,
                "model": llm_result["model"]
            }
            
        except Exception as e:
            pipeline_latency = time.time() - pipeline_start
            log_error_with_context(logger, e, {"tool": "generate_response_tool", "input": user_input})
            return {"error": f"Response generation failed: {str(e)}"}
    
    @tool("Synthesize complete speech response")
    async def synthesize_speech_tool(self, text: str) -> Dict[str, Any]:
        """
        Synthesize complete speech response.
        
        Args:
            text: Text to synthesize
            
        Returns:
            Dict with speech synthesis result
        """
        pipeline_start = time.time()
        
        try:
            # Synthesize speech
            tts_result = await tts_service.synthesize_speech(text)
            
            if "error" in tts_result:
                return tts_result
            
            pipeline_latency = time.time() - pipeline_start
            
            return {
                "audio_data": tts_result["audio_data"],
                "latency": tts_result["latency"],
                "pipeline_latency": pipeline_latency,
                "model": tts_result["model"]
            }
            
        except Exception as e:
            pipeline_latency = time.time() - pipeline_start
            log_error_with_context(logger, e, {"tool": "synthesize_speech_tool", "text_length": len(text)})
            return {"error": f"Speech synthesis failed: {str(e)}"}
    
    @log_performance
    async def process_voice_input(self, audio_data: bytes, session_id: str = None) -> Dict[str, Any]:
        """
        Process complete voice input through the full pipeline.
        
        Args:
            audio_data: Complete audio data
            session_id: Session identifier
            
        Returns:
            Dict with complete pipeline result
        """
        pipeline_start = time.time()
        
        try:
            self.current_session_id = session_id
            self.conversation_active = True
            
            logger.info(f"Processing voice input for session {session_id}")
            
            # Process audio for STT
            stt_start = time.time()
            processed_audio = await audio_processor.process_audio_for_stt(audio_data)
            stt_process_time = time.time() - stt_start
            
            # Transcribe audio
            stt_result = await stt_service.transcribe_audio(processed_audio)
            stt_latency = time.time() - stt_start
            
            if "error" in stt_result:
                return {
                    "error": stt_result["error"],
                    "pipeline_latency": time.time() - pipeline_start
                }
            
            transcription = stt_result["text"]
            
            if not transcription.strip():
                return {
                    "error": "No speech detected",
                    "transcription": "",
                    "response_text": "",
                    "audio_data": b"",
                    "pipeline_latency": time.time() - pipeline_start
                }
            
            # Generate LLM response
            llm_start = time.time()
            llm_result = await llm_service.generate_response(transcription)
            llm_latency = time.time() - llm_start
            
            if "error" in llm_result:
                return {
                    "error": llm_result["error"],
                    "transcription": transcription,
                    "pipeline_latency": time.time() - pipeline_start
                }
            
            response_text = llm_result["text"]
            
            # Synthesize speech
            tts_start = time.time()
            tts_result = await tts_service.synthesize_speech(response_text)
            tts_latency = time.time() - tts_start
            
            if "error" in tts_result:
                return {
                    "error": tts_result["error"],
                    "transcription": transcription,
                    "response_text": response_text,
                    "pipeline_latency": time.time() - pipeline_start
                }
            
            audio_data = tts_result["audio_data"]
            pipeline_latency = time.time() - pipeline_start
            
            logger.info(f"Voice processing completed in {pipeline_latency:.3f}s")
            
            return {
                "transcription": transcription,
                "response_text": response_text,
                "audio_data": audio_data,
                "pipeline_latency": pipeline_latency,
                "stt_latency": stt_latency,
                "llm_latency": llm_latency,
                "tts_latency": tts_latency,
                "models_used": {
                    "stt": stt_result["model"],
                    "llm": llm_result["model"],
                    "tts": tts_result["model"]
                }
            }
            
        except Exception as e:
            pipeline_latency = time.time() - pipeline_start
            log_error_with_context(logger, e, {"session_id": session_id, "audio_size": len(audio_data)})
            return {
                "error": f"Voice processing failed: {str(e)}",
                "pipeline_latency": pipeline_latency
            }
    
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
            
            # Process audio chunks using AudioStreamProcessor
            processed_chunks = await self.process_streaming_audio_tool(audio_chunks)
            
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
    
    async def process_audio_stream(self, audio_stream: asyncio.StreamReader, session_id: str = None) -> Dict[str, Any]:
        """
        Process real-time audio stream for ultra-low latency.
        
        Args:
            audio_stream: Async stream reader for audio data
            session_id: Session identifier
            
        Returns:
            Dict with complete pipeline result
        """
        pipeline_start = time.time()
        
        try:
            self.current_session_id = session_id
            self.conversation_active = True
            
            logger.info(f"Starting real-time audio stream processing for session {session_id}")
            
            # Use AudioStreamProcessor to handle the stream
            audio_chunks = []
            async for chunk in stream_processor.process_audio_stream(audio_stream):
                audio_chunks.append(chunk)
                
                # Process chunks in batches for optimal performance
                if len(audio_chunks) >= 10:  # Process every 10 chunks
                    break
            
            if not audio_chunks:
                return {
                    "error": "No audio data received from stream",
                    "pipeline_latency": time.time() - pipeline_start
                }
            
            # Process the accumulated chunks
            return await self.process_streaming_voice(audio_chunks, session_id)
            
        except Exception as e:
            pipeline_latency = time.time() - pipeline_start
            logger.error(f"Stream processing failed after {pipeline_latency:.3f}s: {str(e)}")
            raise
    
    async def warm_up_services(self) -> None:
        """Warm up all services for optimal performance."""
        try:
            logger.info("Warming up all services...")

            # Warm up async services in parallel
            await asyncio.gather(
                stt_service.warm_up_models(),
                llm_service.warm_up_models()
            )
            
            # Warm up TTS cache synchronously
            await tts_service.warm_up_cache()
            
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
                "metrics": self.performance_monitor["metrics"]
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