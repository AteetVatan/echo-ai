"""
FastAPI application with WebSocket endpoints for EchoAI voice chat system.

This module provides the main API server with WebSocket support for real-time
audio streaming and voice chat functionality.
"""

import asyncio
import json
import uuid
import base64
from typing import Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

from src.agents.voice_clone_agent import voice_clone_agent
from src.utils.config import get_settings, validate_api_keys
from src.utils.logging import setup_logging, get_logger


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
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Connect a new WebSocket client."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.session_data[session_id] = {
            "connected_at": asyncio.get_event_loop().time(),
            "message_count": 0,
            "last_activity": asyncio.get_event_loop().time()
        }
        logger.info(f"WebSocket connected: {session_id}")
    
    def disconnect(self, session_id: str):
        """Disconnect a WebSocket client."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.session_data:
            del self.session_data[session_id]
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
        
        # Warm up services
        await voice_clone_agent.warm_up_services()
        
        logger.info("EchoAI Voice Chat API started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start API: {str(e)}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down EchoAI Voice Chat API...")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "EchoAI Voice Chat API",
        "version": "1.0.0",
        "status": "running",
        "websocket_endpoint": "/ws/voice",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "services": {
            "stt": "available",
            "llm": "available", 
            "tts": "available"
        },
        "active_sessions": len(manager.get_active_sessions())
    }


@app.get("/stats")
async def get_stats():
    """Get performance statistics."""
    try:
        performance_summary = voice_clone_agent.get_performance_summary()
        active_sessions = manager.get_active_sessions()
        
        return {
            "performance": performance_summary,
            "active_sessions": len(active_sessions),
            "session_details": active_sessions
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


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
    """WebSocket endpoint for real-time voice chat."""
    session_id = str(uuid.uuid4())
    
    try:
        await manager.connect(websocket, session_id)
        
        # Send welcome message
        await manager.send_message(session_id, {
            "type": "connection",
            "session_id": session_id,
            "message": "Connected to EchoAI Voice Chat"
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
    """Handle audio message from client."""
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
        
        # Generate LLM response
        llm_result = await voice_clone_agent.llm_tool(text)
        response_text = llm_result["text"]
        
        # Synthesize speech
        tts_result = await voice_clone_agent.tts_tool(response_text)
        audio_data = tts_result["audio_data"]
        
        # Encode response audio
        response_audio_b64 = base64.b64encode(audio_data).decode()
        
        # Send response
        await manager.send_message(session_id, {
            "type": "response",
            "transcription": text,
            "response_text": response_text,
            "audio": response_audio_b64,
            "latency": {
                "llm": llm_result["latency"],
                "tts": tts_result["latency"]
            },
            "models_used": {
                "llm": llm_result["model"],
                "tts": tts_result["model"]
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
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    ) 