import asyncio
import json
from typing import Dict, Any,  List
from fastapi import  WebSocket
from src.utils import get_logger


class ConnectionManager:
    """Manages WebSocket connections and sessions."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
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
        self.logger.info(f"WebSocket connected: {session_id}")
    
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
        self.logger.info(f"WebSocket disconnected: {session_id}")
    
    async def send_message(self, session_id: str, message: Dict[str, Any]):
        """Send message to specific client."""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(json.dumps(message))
                self.session_data[session_id]["message_count"] += 1
                self.session_data[session_id]["last_activity"] = asyncio.get_event_loop().time()
            except Exception as e:
                self.logger.error(f"Failed to send message to {session_id}: {str(e)}")
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