import asyncio
import json
import time
from collections import defaultdict, deque
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from backend.utils import get_logger, get_settings


settings = get_settings()


class ConnectionManager:
    """Manages WebSocket connections, sessions, per-IP limits, and rate limiting."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.active_connections: dict[str, WebSocket] = {}
        self.session_data: dict[str, dict[str, Any]] = {}
        self.audio_buffers: dict[str, list[bytes]] = {}
        self.streaming_sessions: dict[str, bool] = {}
        self._ip_sessions: dict[str, set] = defaultdict(set)
        self._session_ip: dict[str, str] = {}
        self._ip_msg_timestamps: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=200)
        )

    def can_accept(self, ip: str) -> bool:
        """Check whether *ip* is below the max-connections-per-IP cap."""
        return len(self._ip_sessions[ip]) < settings.MAX_WS_CONNECTIONS_PER_IP

    async def connect(
        self, websocket: WebSocket, session_id: str, *, ip: str = "unknown"
    ) -> None:
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
        self._ip_sessions[ip].add(session_id)
        self._session_ip[session_id] = ip
        self.logger.info("WebSocket connected: %s (IP: %s)", session_id, ip)

    def disconnect(self, session_id: str) -> None:
        """Disconnect a WebSocket client and clean up IP tracking."""
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
        self.logger.info("WebSocket disconnected: %s", session_id)

    def check_rate_limit(self, session_id: str) -> bool:
        """Return True if the message is ALLOWED (under rate limit).

        Uses per-IP sliding-window counter (messages in the last 60 s).
        """
        ip = self._session_ip.get(session_id, "unknown")
        now = time.monotonic()
        window = self._ip_msg_timestamps[ip]

        while window and window[0] < now - 60:
            window.popleft()

        if len(window) >= settings.WS_MSG_RATE_LIMIT:
            self.logger.warning(
                "WS rate limit exceeded for IP %s (%d/%d msgs/min)",
                ip,
                len(window),
                settings.WS_MSG_RATE_LIMIT,
            )
            return False

        window.append(now)
        return True

    async def send_message(self, session_id: str, message: dict[str, Any]) -> None:
        """Send message to specific client."""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(json.dumps(message))
                self.session_data[session_id]["message_count"] += 1
                self.session_data[session_id]["last_activity"] = (
                    asyncio.get_event_loop().time()
                )
            except (RuntimeError, TypeError, ValueError, WebSocketDisconnect) as e:
                self.logger.error(
                    "Failed to send message to %s: %s",
                    session_id,
                    e,
                    exc_info=True,
                )
                self.disconnect(session_id)

    def get_active_sessions(self) -> dict[str, dict[str, Any]]:
        """Get information about active sessions."""
        return self.session_data

    def add_audio_chunk(self, session_id: str, audio_chunk: bytes) -> None:
        """Add audio chunk to session buffer."""
        if session_id in self.audio_buffers:
            self.audio_buffers[session_id].append(audio_chunk)

    def get_audio_buffer(self, session_id: str) -> list[bytes]:
        """Get audio buffer for session."""
        return self.audio_buffers.get(session_id, [])

    def clear_audio_buffer(self, session_id: str) -> None:
        """Clear audio buffer for session."""
        if session_id in self.audio_buffers:
            self.audio_buffers[session_id].clear()

    def set_streaming_status(self, session_id: str, *, is_streaming: bool) -> None:
        """Set streaming status for session."""
        self.streaming_sessions[session_id] = is_streaming
