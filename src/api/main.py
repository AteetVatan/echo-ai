"""
FastAPI application with WebSocket endpoints for EchoAI voice chat system.

This module provides the main API server with WebSocket support for real-time
audio streaming and voice chat functionality.
"""

import asyncio
import json
import uuid
import base64
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

from src.agents.voice_clone_agent import voice_clone_agent
from src.utils.config import get_settings, validate_api_keys
from src.utils.logging import setup_logging, get_logger
from src.utils.audio import stream_processor


# Setup logging
setup_logging()
logger = get_logger(__name__)
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="EchoAI Voice Chat API",
    description="Real-time AI voice chat with STT→LLM→TTS pipeline",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionManager:
    """Manages WebSocket connections and sessions."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_data: Dict[str, Dict[str, Any]] = {}
        # Add audio buffers for streaming
        self.audio_buffers: Dict[str, List[bytes]] = {}
        self.streaming_sessions: Dict[str, bool] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Connect a new WebSocket client."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.session_data[session_id] = {
            "connected_at": asyncio.get_event_loop().time(),
            "message_count": 0,
            "last_activity": asyncio.get_event_loop().time()
        }
        # Initialize audio buffer for streaming
        self.audio_buffers[session_id] = []
        self.streaming_sessions[session_id] = False
        logger.info(f"WebSocket connected: {session_id}")
    
    def disconnect(self, session_id: str):
        """Disconnect a WebSocket client."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.session_data:
            del self.session_data[session_id]
        # Clean up audio buffers
        if session_id in self.audio_buffers:
            del self.audio_buffers[session_id]
        if session_id in self.streaming_sessions:
            del self.streaming_sessions[session_id]
        logger.info(f"WebSocket disconnected: {session_id}")
    
    async def send_message(self, session_id: str, message: Dict[str, Any]):
        """Send message to specific client."""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(json.dumps(message))
                self.session_data[session_id]["message_count"] += 1
                self.session_data[session_id]["last_activity"] = asyncio.get_event_loop().time()
            except Exception as e:
                logger.error(f"Failed to send message to {session_id}: {str(e)}")
                self.disconnect(session_id)
    
    def get_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get information about active sessions."""
        return self.session_data
    
    def add_audio_chunk(self, session_id: str, audio_chunk: bytes):
        """Add audio chunk to session buffer."""
        if session_id in self.audio_buffers:
            self.audio_buffers[session_id].append(audio_chunk)
    
    def get_audio_buffer(self, session_id: str) -> List[bytes]:
        """Get audio buffer for session."""
        return self.audio_buffers.get(session_id, [])
    
    def clear_audio_buffer(self, session_id: str):
        """Clear audio buffer for session."""
        if session_id in self.audio_buffers:
            self.audio_buffers[session_id].clear()
    
    def set_streaming_status(self, session_id: str, is_streaming: bool):
        """Set streaming status for session."""
        self.streaming_sessions[session_id] = is_streaming


# Global connection manager
manager = ConnectionManager()


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    try:
        logger.info("Starting EchoAI Voice Chat API...")
        
        # Validate API keys
        if not validate_api_keys():
            logger.warning("Some API keys are missing or invalid. Check your .env file.")
        
        # Warm up agent services
        await voice_clone_agent.warm_up_services()
        
        logger.info("EchoAI Voice Chat API started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start API: {str(e)}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down EchoAI Voice Chat API...")
    # Close all WebSocket connections
    for session_id in list(manager.active_connections.keys()):
        manager.disconnect(session_id)


@app.get("/")
async def root():
    """Root endpoint with basic info."""
    return {
        "name": "EchoAI Voice Chat API",
        "version": "1.0.0",
        "description": "Real-time AI voice chat with STT→LLM→TTS pipeline",
        "status": "running",
        "active_connections": len(manager.active_connections)
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check if services are available
        agent_stats = voice_clone_agent.get_performance_summary()
        
        return {
            "status": "healthy",
            "timestamp": asyncio.get_event_loop().time(),
            "active_connections": len(manager.active_connections),
            "services": {
                "agent": "available",
                "stt": "available" if agent_stats.get("stt") else "unavailable",
                "llm": "available" if agent_stats.get("llm") else "unavailable",
                "tts": "available" if agent_stats.get("tts") else "unavailable"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@app.get("/stats")
async def get_stats():
    """Get system statistics."""
    try:
        agent_stats = voice_clone_agent.get_performance_summary()
        active_sessions = manager.get_active_sessions()
        
        return {
            "active_connections": len(manager.active_connections),
            "active_sessions": active_sessions,
            "streaming_sessions": sum(manager.streaming_sessions.values()),
            "agent_performance": agent_stats,
            "server_info": {
                "version": "1.0.0",
                "uptime": asyncio.get_event_loop().time()
            }
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")


@app.post("/clear-conversation")
async def clear_conversation():
    """Clear conversation history."""
    try:
        voice_clone_agent.clear_conversation()
        return {"message": "Conversation cleared successfully"}
    except Exception as e:
        logger.error(f"Failed to clear conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to clear conversation")


@app.websocket("/ws/voice")
async def websocket_voice_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time voice chat with streaming support."""
    session_id = str(uuid.uuid4())
    
    try:
        await manager.connect(websocket, session_id)
        
        # Send welcome message
        await manager.send_message(session_id, {
            "type": "connection",
            "session_id": session_id,
            "message": "Connected to EchoAI Voice Chat",
            "features": ["streaming_audio", "real_time_processing"]
        })
        
        logger.info(f"Voice chat session started: {session_id}")
        
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                message_type = message.get("type")
                
                if message_type == "audio":
                    await handle_audio_message(session_id, message)
                elif message_type == "audio_chunk":
                    await handle_audio_chunk_message(session_id, message)
                elif message_type == "start_streaming":
                    await handle_start_streaming(session_id, message)
                elif message_type == "stop_streaming":
                    await handle_stop_streaming(session_id, message)
                elif message_type == "text":
                    await handle_text_message(session_id, message)
                elif message_type == "ping":
                    await manager.send_message(session_id, {"type": "pong"})
                else:
                    await manager.send_message(session_id, {
                        "type": "error",
                        "message": f"Unknown message type: {message_type}"
                    })
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {session_id}")
                break
            except json.JSONDecodeError:
                await manager.send_message(session_id, {
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                await manager.send_message(session_id, {
                    "type": "error",
                    "message": f"Processing error: {str(e)}"
                })
                
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {str(e)}")
    finally:
        manager.disconnect(session_id)


async def handle_audio_message(session_id: str, message: Dict[str, Any]):
    """Handle complete audio message from client (legacy support)."""
    try:
        # Extract audio data
        audio_data_b64 = message.get("audio")
        if not audio_data_b64:
            await manager.send_message(session_id, {
                "type": "error",
                "message": "No audio data provided"
            })
            return
        
        # Decode base64 audio data
        audio_data = base64.b64decode(audio_data_b64)
        
        # Send processing status
        await manager.send_message(session_id, {
            "type": "processing",
            "message": "Processing your voice input..."
        })
        
        # Process voice input through agent
        result = await voice_clone_agent.process_voice_input(audio_data, session_id)
        
        if "error" in result:
            await manager.send_message(session_id, {
                "type": "error",
                "message": result["error"]
            })
            return
        
        # Encode response audio
        response_audio_b64 = base64.b64encode(result["audio_data"]).decode()
        
        # Send response
        await manager.send_message(session_id, {
            "type": "response",
            "transcription": result["transcription"],
            "response_text": result["response_text"],
            "audio": response_audio_b64,
            "latency": {
                "pipeline": result["pipeline_latency"],
                "stt": result["stt_latency"],
                "llm": result["llm_latency"],
                "tts": result["tts_latency"]
            },
            "models_used": result["models_used"]
        })
        
        logger.info(f"Voice processing completed for session {session_id}")
        
    except Exception as e:
        logger.error(f"Failed to process audio for session {session_id}: {str(e)}")
        await manager.send_message(session_id, {
            "type": "error",
            "message": f"Failed to process audio: {str(e)}"
        })


async def handle_audio_chunk_message(session_id: str, message: Dict[str, Any]):
    """Handle streaming audio chunk from client."""
    try:
        # Extract audio chunk data
        audio_chunk_b64 = message.get("audio_chunk")
        if not audio_chunk_b64:
            await manager.send_message(session_id, {
                "type": "error",
                "message": "No audio chunk data provided"
            })
            return
        
        # Decode base64 audio chunk
        audio_chunk = base64.b64decode(audio_chunk_b64)
        
        # Add to session buffer
        manager.add_audio_chunk(session_id, audio_chunk)
        
        # Send acknowledgment
        await manager.send_message(session_id, {
            "type": "chunk_received",
            "chunk_size": len(audio_chunk),
            "buffer_size": len(manager.get_audio_buffer(session_id))
        })
        
        logger.debug(f"Audio chunk received for session {session_id}: {len(audio_chunk)} bytes")
        
    except Exception as e:
        logger.error(f"Failed to process audio chunk for session {session_id}: {str(e)}")
        await manager.send_message(session_id, {
            "type": "error",
            "message": f"Failed to process audio chunk: {str(e)}"
        })


async def handle_start_streaming(session_id: str, message: Dict[str, Any]):
    """Handle start streaming request."""
    try:
        # Set streaming status
        manager.set_streaming_status(session_id, True)
        
        # Clear any existing audio buffer
        manager.clear_audio_buffer(session_id)
        
        await manager.send_message(session_id, {
            "type": "streaming_started",
            "message": "Audio streaming started"
        })
        
        logger.info(f"Audio streaming started for session {session_id}")
        
    except Exception as e:
        logger.error(f"Failed to start streaming for session {session_id}: {str(e)}")
        await manager.send_message(session_id, {
            "type": "error",
            "message": f"Failed to start streaming: {str(e)}"
        })


async def handle_stop_streaming(session_id: str, message: Dict[str, Any]):
    """Handle stop streaming request and process accumulated audio."""
    try:
        # Set streaming status
        manager.set_streaming_status(session_id, False)
        
        # Get accumulated audio chunks
        audio_chunks = manager.get_audio_buffer(session_id)
        
        if not audio_chunks:
            await manager.send_message(session_id, {
                "type": "error",
                "message": "No audio data to process"
            })
            return
        
        # Send processing status
        await manager.send_message(session_id, {
            "type": "processing",
            "message": "Processing streaming audio...",
            "chunks_count": len(audio_chunks)
        })
        
        # Process streaming voice input through agent
        result = await voice_clone_agent.process_streaming_voice(audio_chunks, session_id)
        
        if "error" in result:
            await manager.send_message(session_id, {
                "type": "error",
                "message": result["error"]
            })
            return
        
        # Encode response audio
        response_audio_b64 = base64.b64encode(result["audio_data"]).decode()
        
        # Send response
        await manager.send_message(session_id, {
            "type": "streaming_response",
            "transcription": result["transcription"],
            "response_text": result["response_text"],
            "audio": response_audio_b64,
            "latency": {
                "pipeline": result["pipeline_latency"],
                "chunks_processed": result["chunks_processed"]
            }
        })
        
        # Clear audio buffer
        manager.clear_audio_buffer(session_id)
        
        logger.info(f"Streaming voice processing completed for session {session_id}")
        
    except Exception as e:
        logger.error(f"Failed to process streaming audio for session {session_id}: {str(e)}")
        await manager.send_message(session_id, {
            "type": "error",
            "message": f"Failed to process streaming audio: {str(e)}"
        })


async def handle_text_message(session_id: str, message: Dict[str, Any]):
    """Handle text message from client."""
    try:
        text = message.get("text", "").strip()
        if not text:
            await manager.send_message(session_id, {
                "type": "error",
                "message": "No text provided"
            })
            return
        
        # Send processing status
        await manager.send_message(session_id, {
            "type": "processing",
            "message": "Generating response..."
        })
        
        # Generate response through agent
        result = await voice_clone_agent.generate_response_tool(text)
        
        if "error" in result:
            await manager.send_message(session_id, {
                "type": "error",
                "message": result["error"]
            })
            return
        
        # Synthesize speech
        tts_result = await voice_clone_agent.synthesize_speech_tool(result["response_text"])
        
        if "error" in tts_result:
            await manager.send_message(session_id, {
                "type": "error",
                "message": tts_result["error"]
            })
            return
        
        # Encode response audio
        response_audio_b64 = base64.b64encode(tts_result["audio_data"]).decode()
        
        # Send response
        await manager.send_message(session_id, {
            "type": "text_response",
            "response_text": result["response_text"],
            "audio": response_audio_b64,
            "latency": {
                "llm": result["latency"],
                "tts": tts_result["latency"]
            }
        })
        
        logger.info(f"Text processing completed for session {session_id}")
        
    except Exception as e:
        logger.error(f"Failed to process text for session {session_id}: {str(e)}")
        await manager.send_message(session_id, {
            "type": "error",
            "message": f"Failed to process text: {str(e)}"
        })


if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    ) 