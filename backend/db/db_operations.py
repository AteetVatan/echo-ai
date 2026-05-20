"""
Supabase-backed database operations for EchoAI.

Replaces the previous SQLite + filesystem implementation with:
  - asyncpg connection pool  → Supabase Postgres
  - supabase-py Storage API  → Supabase Storage (audio files)

No raw connection (`self.conn`) is exposed. All access is via typed async
methods so that consumers (TTSService, ReplyCacheManager) never touch SQL.
"""

import hashlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import asyncpg
from supabase import create_client, Client as SupabaseClient
from storage3.utils import StorageException

from backend.exceptions import DatabaseError
from backend.utils import get_logger, get_settings

logger = get_logger(__name__)
settings = get_settings()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
STORAGE_BUCKET = "audio-cache"


@dataclass(frozen=True)
class AudioCacheRecord:
    """Audio cache write request."""

    text: str
    audio_data: bytes
    voice_id: str


@dataclass(frozen=True)
class ReplyCacheRecord:
    """Reply cache write request."""

    user_text: str
    response_text: str
    audio_storage_path: str
    text_hash: str
    vector_id: str


def _text_hash(text: str) -> str:
    """Deterministic MD5 hash of normalised text."""
    return hashlib.md5(text.lower().strip().encode()).hexdigest()


class DBOperations:
    """Async Supabase Postgres + Storage operations.

    Usage::

        db = DBOperations()
        await db.initialize()   # call once at FastAPI startup
        ...
        await db.close()        # call at shutdown
    """

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def __init__(self) -> None:
        self._pool: Optional[asyncpg.Pool] = None
        self._supabase: Optional[SupabaseClient] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Create the asyncpg pool and Supabase client.

        Must be called once before any other method (typically in a
        FastAPI ``@app.on_event("startup")`` handler).
        """
        if self._initialized:
            return

        db_url = settings.SUPABASE_DB_URL
        if not db_url:
            raise DatabaseError("SUPABASE_DB_URL is not set in environment")

        self._pool = await asyncpg.create_pool(
            db_url,
            min_size=2,
            max_size=10,
            command_timeout=30,
            statement_cache_size=0,  # Required for Supabase pgBouncer (transaction mode)
        )

        self._supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
        )

        self._initialized = True
        logger.info("DBOperations initialised (asyncpg pool + Supabase client)")

    async def close(self) -> None:
        """Shut down the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
        self._initialized = False
        logger.info("DBOperations closed")

    def _ensure_initialised(self) -> None:
        if not self._initialized:
            raise DatabaseError(
                "DBOperations not initialised – call await db.initialize() first"
            )

    # ------------------------------------------------------------------
    # Audio cache — used by TTSService
    # ------------------------------------------------------------------

    async def save_audio(self, record: AudioCacheRecord) -> str:
        """Upload audio to Storage and insert metadata into Postgres.

        Returns the Supabase Storage path.
        """
        self._ensure_initialised()
        th = _text_hash(record.text)
        storage_path = f"{record.voice_id}/{th}.mp3"
        self._upload_or_update(storage_path, record.audio_data)

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO audio_cache
                    (text, voice_id, storage_path, file_path, file_size_bytes, text_hash)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (text_hash, voice_id) DO UPDATE
                    SET storage_path    = EXCLUDED.storage_path,
                        file_path       = EXCLUDED.file_path,
                        file_size_bytes = EXCLUDED.file_size_bytes
                """,
                record.text,
                record.voice_id,
                storage_path,
                storage_path,  # file_path (legacy NOT NULL column)
                len(record.audio_data),
                th,
            )

        logger.debug("Saved audio: %s (%d bytes)", storage_path, len(record.audio_data))
        return storage_path

    def _upload_or_update(self, storage_path: str, audio_data: bytes) -> None:
        """Upload audio bytes and update duplicates when Supabase reports one."""
        try:
            self._upload_storage_object(storage_path, audio_data)
        except StorageException as exc:
            if not self._is_duplicate_storage_error(exc):
                raise DatabaseError("Supabase Storage upload failed") from exc
            self._update_storage_object(storage_path, audio_data)

    def _upload_storage_object(self, storage_path: str, audio_data: bytes) -> None:
        """Upload an object to the configured audio bucket."""
        self._supabase.storage.from_(STORAGE_BUCKET).upload(
            storage_path,
            audio_data,
            file_options={"content-type": "audio/mpeg", "upsert": "true"},
        )

    def _update_storage_object(self, storage_path: str, audio_data: bytes) -> None:
        """Update an existing object in the configured audio bucket."""
        self._supabase.storage.from_(STORAGE_BUCKET).update(
            storage_path,
            audio_data,
            file_options={"content-type": "audio/mpeg"},
        )

    @staticmethod
    def _is_duplicate_storage_error(exc: StorageException) -> bool:
        """Return True when a StorageException represents a duplicate object."""
        message = str(exc)
        return "Duplicate" in message or "already exists" in message

    async def load_audio(self, text: str, voice_id: str) -> Optional[bytes]:
        """Download a single audio file from Storage.

        Returns the MP3 bytes, or ``None`` if not found.
        """
        self._ensure_initialised()
        th = _text_hash(text)

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT storage_path FROM audio_cache WHERE text_hash = $1 AND voice_id = $2",
                th,
                voice_id,
            )

        if not row:
            return None

        try:
            data = self._supabase.storage.from_(STORAGE_BUCKET).download(
                row["storage_path"]
            )
            return data
        except StorageException as exc:
            logger.warning(
                "Storage download failed for %s: %s", row["storage_path"], exc
            )
            return None

    async def load_audio_metadata(self, voice_id: str) -> List[Dict[str, Any]]:
        """Load all audio metadata rows for a given voice (no MP3 download).

        Used by TTSService.warmup_cache() for background index building.
        """
        self._ensure_initialised()

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT text_hash, storage_path, text FROM audio_cache WHERE voice_id = $1",
                voice_id,
            )

        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Reply cache — used by ReplyCacheManager
    # ------------------------------------------------------------------

    async def find_reply_by_hash(self, text_hash: str) -> Optional[Dict[str, Any]]:
        """Exact-match lookup by text hash."""
        self._ensure_initialised()

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT user_text, response_text, audio_storage_path, created_at
                FROM reply_cache
                WHERE text_hash = $1
                """,
                text_hash,
            )
        return dict(row) if row else None

    async def find_reply_by_text(self, user_text: str) -> Optional[Dict[str, Any]]:
        """Lookup by exact user_text value."""
        self._ensure_initialised()

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT user_text, response_text, audio_storage_path, created_at
                FROM reply_cache
                WHERE user_text = $1
                """,
                user_text,
            )
        return dict(row) if row else None

    async def upsert_reply(self, record: ReplyCacheRecord) -> None:
        """Insert or update a reply cache entry."""
        self._ensure_initialised()

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO reply_cache
                    (user_text, response_text, audio_storage_path, text_hash, vector_id)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (text_hash) DO UPDATE
                    SET response_text      = EXCLUDED.response_text,
                        audio_storage_path = EXCLUDED.audio_storage_path,
                        vector_id          = EXCLUDED.vector_id
                """,
                record.user_text,
                record.response_text,
                record.audio_storage_path,
                record.text_hash,
                record.vector_id,
            )

    # ------------------------------------------------------------------
    # Storage helpers (used by migration scripts / prebuild)
    # ------------------------------------------------------------------

    async def upload_audio_bytes(self, storage_path: str, audio_data: bytes) -> str:
        """Upload raw bytes to the audio-cache bucket. Returns the path."""
        self._ensure_initialised()

        self._upload_or_update(storage_path, audio_data)
        return storage_path

    async def download_audio_bytes(self, storage_path: str) -> Optional[bytes]:
        """Download raw bytes from the audio-cache bucket."""
        self._ensure_initialised()

        try:
            return self._supabase.storage.from_(STORAGE_BUCKET).download(storage_path)
        except StorageException as exc:
            logger.warning("Storage download failed: %s — %s", storage_path, exc)
            return None
