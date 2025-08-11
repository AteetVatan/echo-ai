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
import platform
import subprocess
import os

from src.services.voice_pipeline import voice_pipeline
from src.services.stt_service import stt_service
from src.services.llm_service import llm_service
from src.services.tts_service import tts_service
from src.utils import get_settings, validate_api_keys
from src.utils import setup_logging, get_logger
from src.utils.audio import audio_stream_processor
from src.api.connection_manager import ConnectionManager


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

# Add static file serving for frontend
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pathlib

#frontend directory path
frontend_path = pathlib.Path(__file__).parent.parent.parent / "frontend"

# Serve static files if frontend directory exists
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


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
        await asyncio.gather(
            stt_service.warm_up_models(),
            llm_service.warm_up_models()
        )
        await tts_service.warm_up_cache()
        
        logger.info("EchoAI Voice Chat API started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start API: {str(e)}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down EchoAI Voice Chat API...")
    logger.info("Closing all WebSocket connections...")
    for session_id in list(manager.active_connections.keys()):
        manager.disconnect(session_id)
    
    # Cleanup services
    try:
        tts_service.cleanup()
        logger.info("Services cleanup completed")
    except Exception as e:
        logger.error(f"Failed to cleanup services: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint with basic info."""
    return {
        "name": "EchoAI Voice Chat API",
        "version": "1.0.0",
        "description": "Real-time AI voice chat with STT→LLM→TTS pipeline",
        "status": "running",
        "active_connections": len(manager.active_connections),
        "frontend_url": "/static/index.html"
    }

@app.get("/frontend")
@app.head("/frontend")
async def serve_frontend():
    """Serve the frontend HTML file."""
    if frontend_path.exists():
        return FileResponse(str(frontend_path / "index.html"))
    else:
        raise HTTPException(status_code=404, detail="Frontend not found")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check if services are available
        pipeline_stats = voice_pipeline.get_performance_stats()
        
        return {
            "status": "healthy",
            "timestamp": asyncio.get_event_loop().time(),
            "active_connections": len(manager.active_connections),
            "services": {
                "pipeline": "available",
                "stt": "available",
                "llm": "available", 
                "tts": "available"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@app.get("/stats")
async def get_stats():
    """Get system statistics."""
    try:
        # Get pipeline and service statistics
        pipeline_stats = voice_pipeline.get_performance_stats()
        stt_stats = stt_service.get_performance_stats()
        llm_stats = llm_service.get_performance_stats()
        tts_stats = tts_service.get_performance_stats()
        active_sessions = manager.get_active_sessions()
        
        return {
            "active_connections": len(manager.active_connections),
            "active_sessions": active_sessions,
            "streaming_sessions": sum(manager.streaming_sessions.values()),
            "pipeline_performance": pipeline_stats,
            "service_performance": {
                "stt": stt_stats,
                "llm": llm_stats,
                "tts": tts_stats
            },
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
        voice_pipeline.clear_conversation()
        return {"message": "Conversation cleared successfully"}
    except Exception as e:
        logger.error(f"Failed to clear conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to clear conversation")


@app.websocket("/ws/voice")
async def websocket_voice_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time voice chat with streaming support."""
    
    #unique session ID for each client.
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
        
        while True: # WebSocket connections are open indefinitely.
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                logger.info(f"session_id: {session_id}")
                logger.info(f"message: {message}")
                message_type = message.get("type")
                logger.info(f"message_type: {message_type}")
                
                if message_type == "audio":
                    #Full audio file is sent in one message.
                    await handle_audio_message(session_id, message)
                elif message_type == "audio_chunk":
                    #Streaming audio chunks
                    await handle_audio_chunk_message(session_id, message)
                elif message_type == "start_streaming":
                    # real-time audio stream.
                    await handle_start_streaming(session_id, message)
                elif message_type == "stop_streaming":
                    # real-time audio stream.
                    await handle_stop_streaming(session_id, message)
                elif message_type == "text":
                    await handle_text_message(session_id, message)
                elif message_type == "ping":
                    #Health check 
                    await manager.send_message(session_id, {"type": "pong"})
                elif message_type == "streaming_buffer":
                    # Process streaming buffer in real-time
                    await handle_streaming_buffer(session_id, message)
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
        
        # Process voice input through pipeline
        result = await voice_pipeline.process_voice_input(audio_data, session_id)
        
        # Check for errors
        if result.error:
            await manager.send_message(session_id, {
                "type": "error",
                "message": result.error
            })
            return
        
        # Encode response audio
        response_audio_b64 = base64.b64encode(result.audio_data).decode()
        
        # Send response
        await manager.send_message(session_id, {
            "type": "response",
            "transcription": result.transcription,
            "response_text": result.response_text,
            "audio": response_audio_b64,
            "latency": {
                "pipeline": result.pipeline_latency,
                "stt": result.stt_latency,
                "rag": result.rag_latency,
                "llm": result.llm_latency,
                "tts": result.tts_latency
            },
            "models_used": result.models_used
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
        # Check if session is in streaming mode
        if not manager.streaming_sessions.get(session_id, False):
            await manager.send_message(session_id, {
                "type": "error",
                "message": "Not in streaming mode. Send 'start_streaming' first."
            })
            return
        
        # Extract audio chunk data
        audio_chunk_b64 = message.get("audio_chunk")
        if not audio_chunk_b64:
            await manager.send_message(session_id, {
                "type": "error",
                "message": "No audio chunk data provided"
            })
            return
        
        # Decode base64 audio chunk
        try:
            audio_chunk = base64.b64decode(audio_chunk_b64)
        except Exception as e:
            await manager.send_message(session_id, {
                "type": "error",
                "message": f"Invalid base64 audio data: {str(e)}"
            })
            return
        
        # Validate chunk size (prevent memory abuse)
        if len(audio_chunk) > 1024 * 1024:  # 1MB limit per chunk
            await manager.send_message(session_id, {
                "type": "error",
                "message": "Audio chunk too large (max 1MB per chunk)"
            })
            return
        
        # Check total buffer size (prevent memory overflow)
        current_buffer = manager.get_audio_buffer(session_id)
        total_size = sum(len(chunk) for chunk in current_buffer) + len(audio_chunk)
        if total_size > 10 * 1024 * 1024:  # 10MB total buffer limit
            await manager.send_message(session_id, {
                "type": "error",
                "message": "Audio buffer full (max 10MB total). Stop streaming to process."
            })
            return
        
        # Add to session buffer
        manager.add_audio_chunk(session_id, audio_chunk)
        
        # Send acknowledgment
        await manager.send_message(session_id, {
            "type": "chunk_received",
            "chunk_size": len(audio_chunk),
            "buffer_size": len(manager.get_audio_buffer(session_id)),
            "total_bytes": total_size + len(audio_chunk)
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
        # Check if session was actually streaming
        if not manager.streaming_sessions.get(session_id, False):
            await manager.send_message(session_id, {
                "type": "error",
                "message": "Not in streaming mode. No audio to process."
            })
            return
        
        # Set streaming status to false
        manager.set_streaming_status(session_id, False)
        
        # Get accumulated audio chunks
        audio_chunks = manager.get_audio_buffer(session_id)
        
        if not audio_chunks:
            await manager.send_message(session_id, {
                "type": "streaming_stopped",
                "message": "Streaming stopped, but no audio data was received",
                "chunks_count": 0
            })
            return
        
        # Calculate total audio size
        total_audio_size = sum(len(chunk) for chunk in audio_chunks)
        
        # Send processing status
        await manager.send_message(session_id, {
            "type": "processing",
            "message": "Processing streaming audio...",
            "chunks_count": len(audio_chunks),
            "total_audio_bytes": total_audio_size
        })
        
        # Process streaming voice input through pipeline
        result = await voice_pipeline.process_streaming_voice(audio_chunks, session_id)
        
        if result.error:
            await manager.send_message(session_id, {
                "type": "error",
                "message": result.error
            })
            # Clear buffer even on error to prevent memory leak
            manager.clear_audio_buffer(session_id)
            return
        
        # Encode response audio
        response_audio_b64 = base64.b64encode(result.audio_data).decode()
        
        # Send response with enhanced metadata
        await manager.send_message(session_id, {
            "type": "streaming_response",
            "transcription": result.transcription,
            "response_text": result.response_text,
            "audio": response_audio_b64,
            "latency": {
                "pipeline": result.pipeline_latency,
                "stt": result.stt_latency,
                "rag": result.rag_latency,
                "tts": result.tts_latency,
                "chunks_processed": result.chunks_processed
            },
            "audio_info": {
                "input_chunks": len(audio_chunks),
                "input_bytes": total_audio_size,
                "output_bytes": len(result.audio_data)
            },
            "cache_info": {
                "semantic_cache_hit": result.semantic_cache_hit,
                "similarity_score": result.similarity_score,
                "rag_used": result.rag_used
            }
        })
        
        # Clear audio buffer after successful processing
        manager.clear_audio_buffer(session_id)
        
        logger.info(f"Streaming voice processing completed for session {session_id}: "
                   f"{len(audio_chunks)} chunks, {total_audio_size} bytes, "
                   f"{result.pipeline_latency:.3f}s latency")
        
    except Exception as e:
        logger.error(f"Failed to process streaming audio for session {session_id}: {str(e)}")
        await manager.send_message(session_id, {
            "type": "error",
            "message": f"Failed to process streaming audio: {str(e)}"
        })
        # Clear buffer on error to prevent memory leak
        manager.clear_audio_buffer(session_id)


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
        
        # Process text input through pipeline
        result = await voice_pipeline.process_text_input(text, session_id)
        
        # Check for errors
        if result.error:
            await manager.send_message(session_id, {
                "type": "error",
                "message": result.error
            })
            return
        
        # Encode response audio
        response_audio_b64 = base64.b64encode(result.audio_data).decode()
        
        # Send response
        await manager.send_message(session_id, {
            "type": "text_response",
            "response_text": result.response_text,
            "audio": response_audio_b64,
            "latency": {
                "pipeline": result.pipeline_latency,
                "rag": result.rag_latency,
                "tts": result.tts_latency
            }
        })
        
        logger.info(f"Text processing completed for session {session_id}")
        
    except Exception as e:
        logger.error(f"Failed to process text for session {session_id}: {str(e)}")
        await manager.send_message(session_id, {
            "type": "error",
            "message": f"Failed to process text: {str(e)}"
        })


async def handle_streaming_buffer(session_id: str, message: Dict[str, Any]):
    """Handle real-time streaming buffer from client."""
    try:
        # Extract audio data
        audio_b64 = message.get("audio")
        if not audio_b64:
            await manager.send_message(session_id, {
                "type": "error",
                "message": "No audio data provided"
            })
            return
        
        # Decode audio
        audio_data = base64.b64decode(audio_b64)
        
        # Process immediately (don't buffer)
        result = await voice_pipeline.process_streaming_voice([audio_data], session_id)
        
        if result.error:
            await manager.send_message(session_id, {
                "type": "error",
                "message": result.error
            })
            return
        
        # Send immediate response
        response_audio_b64 = base64.b64encode(result.audio_data).decode()
        
        await manager.send_message(session_id, {
            "type": "streaming_response",
            "transcription": result.transcription,
            "response_text": result.response_text,
            "audio": response_audio_b64,
            "latency": result.pipeline_latency
        })
        
        logger.info(f"Real-time streaming response sent for session {session_id}")
        
    except Exception as e:
        logger.error(f"Failed to process streaming buffer: {str(e)}")
        await manager.send_message(session_id, {
            "type": "error",
            "message": f"Failed to process streaming buffer: {str(e)}"
        })


def free_port(port):
    """
    Frees the given TCP port by finding and killing the process that uses it.
    Works on Windows, macOS, and Linux.
    """
    try:
        if platform.system() == "Windows":
            # Find PID
            result = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True).decode()
            for line in result.strip().split("\n"):
                if f":{port}" in line and "LISTENING" in line:
                    pid = int(line.strip().split()[-1])
                    print(f"Port {port} in use by PID {pid}, killing...")
                    subprocess.call(f"taskkill /PID {pid} /F", shell=True)
                    print(f"Port {port} freed")
        else:
            # macOS / Linux
            result = subprocess.check_output(f"lsof -t -i:{port}", shell=True).decode().strip().split("\n")
            for pid in result:
                if pid.strip():
                    print(f"Port {port} in use by PID {pid}, killing...")
                    os.system(f"kill -9 {pid}")
                    print(f"Port {port} freed")
    except subprocess.CalledProcessError:
        print(f"Port {port} is already free")


def run_server():
    # Free port if already in use
    free_port(settings.PORT)
    
    uvicorn.run(
        "src.api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    ) 