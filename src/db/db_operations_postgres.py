import asyncio
import os
from datetime import datetime
from typing import Optional, Dict
import asyncpg

from src.utils import get_logger, get_settings

class DBOperationsPostgres:
    """
    DBAudioOperations: Manages a single audio table with optional voice_id.
    """

    AUDIO_DIR = "audio_cache"
    TABLE_NAME = "audio_cache"

    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        self.pool: Optional[asyncpg.Pool] = None
        os.makedirs(self.AUDIO_DIR, exist_ok=True)
        # Remove asyncio.run() calls - will be initialized separately
        async def test():
            conn = await asyncpg.connect(self.settings.SUPABASE_DB_URL, ssl="require")
            print(await conn.fetchval("SELECT version()"))
            await conn.close()
                        
        asyncio.run(test())

    async def initialize(self):
        """Initialize database connection pool and table."""
        await self._init_pool()
        await self.init_audio_table()

    async def _init_pool(self):
        """Initialize asyncpg pool."""
        try:
            
            self.pool = await asyncpg.create_pool(
                self.settings.SUPABASE_DB_URL,
                min_size=1,
                max_size=5,
                command_timeout=60,
                server_settings={"application_name": "masx_ai_audio"},
            )
            self.logger.info("Database pool initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize database pool: {str(e)}")
            # Fallback to file-based caching only
            self.pool = None

    async def init_audio_table(self):
        """Create a single audio table if not exists."""
        if not self.pool:
            self.logger.warning("Database pool not available, skipping table creation")
            return
            
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
                        id SERIAL PRIMARY KEY,
                        text TEXT NOT NULL,
                        voice_id TEXT NULL,
                        file_path TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                """)
            self.logger.info(f"Table ensured: {self.TABLE_NAME}")
        except Exception as e:
            self.logger.error(f"Failed to create audio table: {str(e)}")

    async def save_audio(self, text: str, audio_data: bytes, voice_id: Optional[str] = None) -> str:
        """Save audio file and insert metadata into the single table."""
        try:
            # Save file locally
            safe_voice = voice_id or "default"
            file_name = f"{safe_voice}_{abs(hash(text))}.mp3"
            file_path = os.path.join(self.AUDIO_DIR, file_name)
            with open(file_path, "wb") as f:
                f.write(audio_data)

            # Insert record into DB if pool is available
            if self.pool:
                async with self.pool.acquire() as conn:
                    await conn.execute(
                        f"INSERT INTO {self.TABLE_NAME} (text, voice_id, file_path) VALUES ($1, $2, $3);",
                        text, voice_id, file_path
                    )

            self.logger.info(f"Audio saved: text='{text[:30]}...', voice_id='{voice_id}'")
            return file_path
        except Exception as e:
            self.logger.error(f"Failed to save audio: {str(e)}")
            raise

    async def load_audio(self, text: str, voice_id: Optional[str] = None) -> Optional[bytes]:
        """Retrieve audio by text (and optional voice_id) from the single table."""
        if not self.pool:
            self.logger.warning("Database pool not available, cannot load audio")
            return None
            
        try:
            async with self.pool.acquire() as conn:
                if voice_id:
                    row = await conn.fetchrow(
                        f"SELECT file_path FROM {self.TABLE_NAME} "
                        f"WHERE text=$1 AND voice_id=$2 ORDER BY created_at DESC LIMIT 1;",
                        text, voice_id
                    )
                else:
                    row = await conn.fetchrow(
                        f"SELECT file_path FROM {self.TABLE_NAME} "
                        f"WHERE text=$1 AND voice_id IS NULL ORDER BY created_at DESC LIMIT 1;",
                        text
                    )

            if row and os.path.exists(row["file_path"]):
                with open(row["file_path"], "rb") as f:
                    return f.read()

            self.logger.warning(f"No audio found for text='{text[:30]}...', voice_id='{voice_id}'")
            return None
        except Exception as e:
            self.logger.error(f"Failed to load audio: {str(e)}")
            return None

    async def load_all_audio(self) -> Dict[str, bytes]:
        """Load all cached audio files into memory."""
        cache = {}
        if not self.pool:
            self.logger.warning("Database pool not available, returning empty cache")
            return cache
            
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"SELECT text, voice_id, file_path FROM {self.TABLE_NAME};")
                
                for row in rows:
                    if os.path.exists(row["file_path"]):
                        with open(row["file_path"], "rb") as f:
                            audio_data = f.read()
                            # Create cache key similar to TTS service
                            voice = row["voice_id"] or "default"
                            text_hash = str(abs(hash(row["text"])))
                            cache_key = f"{voice}_{text_hash}"
                            cache[cache_key] = audio_data
                            
            self.logger.info(f"Loaded {len(cache)} audio files into cache")
            return cache
        except Exception as e:
            self.logger.error(f"Failed to load all audio: {str(e)}")
            return {}

    async def close(self):
        """Close database pool."""
        if self.pool:
            await self.pool.close()
            self.logger.info("Database pool closed")
