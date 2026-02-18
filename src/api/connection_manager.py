import asyncio
import json
import time
from collections import defaultdict, deque
from typing import Dict, Any, List
from fastapi import WebSocket
from src.utils import get_logger, get_settings


settings = get_settings()


class ConnectionManager:
    """Manages WebSocket connections, sessions, per-IP limits, and rate limiting."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_data: Dict[str, Dict[str, Any]] = {}
        # Audio buffers for streaming
        self.audio_buffers: Dict[str, List[bytes]] = {}
        self.streaming_sessions: Dict[str, bool] = {}
        # Per-IP tracking: ip -> set of session_ids
        self._ip_sessions: Dict[str, set] = defaultdict(set)
        # Session -> IP mapping (for cleanup)
        self._session_ip: Dict[str, str] = {}
        # Per-IP WS message rate limiting: ip -> deque of timestamps
        self._ip_msg_timestamps: Dict[str, deque] = defaultdict(lambda: deque(maxlen=200))
    
    # ── Connection lifecycle ──────────────────────────────────────────

    def can_accept(self, ip: str) -> bool:
        """Check whether *ip* is below the max-connections-per-IP cap."""
        return len(self._ip_sessions[ip]) < settings.MAX_WS_CONNECTIONS_PER_IP

    async def connect(self, websocket: WebSocket, session_id: str, ip: str = "unknown"):
        """Connect a new WebSocket client and track its IP."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.session_data[session_id] = {
            "connected_at": asyncio.get_event_loop().time(),
            "message_count": 0,
            "last_activity": asyncio.get_event_loop().time(),
            "ip": ip,
        }
        # Audio buffer
        self.audio_buffers[session_id] = []
        self.streaming_sessions[session_id] = False
        # IP tracking
        self._ip_sessions[ip].add(session_id)
        self._session_ip[session_id] = ip
        self.logger.info(f"WebSocket connected: {session_id} (IP: {ip})")
    
    def disconnect(self, session_id: str):
        """Disconnect a WebSocket client and clean up IP tracking."""
        # IP cleanup
        ip = self._session_ip.pop(session_id, None)
        if ip and session_id in self._ip_sessions.get(ip, set()):
            self._ip_sessions[ip].discard(session_id)
            if not self._ip_sessions[ip]:
                del self._ip_sessions[ip]
                self._ip_msg_timestamps.pop(ip, None)

        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.session_data:
            del self.session_data[session_id]
        if session_id in self.audio_buffers:
            del self.audio_buffers[session_id]
        if session_id in self.streaming_sessions:
            del self.streaming_sessions[session_id]
        self.logger.info(f"WebSocket disconnected: {session_id}")
    
    # ── Rate limiting ─────────────────────────────────────────────────

    def check_rate_limit(self, session_id: str) -> bool:
        """Return True if the message is ALLOWED (under rate limit).

        Uses per-IP sliding-window counter (messages in the last 60 s).
        """
        ip = self._session_ip.get(session_id, "unknown")
        now = time.monotonic()
        window = self._ip_msg_timestamps[ip]

        # Evict entries older than 60 s
        while window and window[0] < now - 60:
            window.popleft()

        if len(window) >= settings.WS_MSG_RATE_LIMIT:
            self.logger.warning(
                f"WS rate limit exceeded for IP {ip} "
                f"({len(window)}/{settings.WS_MSG_RATE_LIMIT} msgs/min)"
            )
            return False

        window.append(now)
        return True
    
    # ── Messaging ─────────────────────────────────────────────────────

    async def send_message(self, session_id: str, message: Dict[str, Any]):
        """Send message to specific client."""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(json.dumps(message))
                self.session_data[session_id]["message_count"] += 1
                self.session_data[session_id]["last_activity"] = asyncio.get_event_loop().time()
            except Exception as e:
                self.logger.error(f"Failed to send message to {session_id}: {str(e)}", exc_info=True)
                self.disconnect(session_id)
    
    def get_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get information about active sessions."""
        return self.session_data
    
    # ── Audio buffer helpers ──────────────────────────────────────────

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