import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, Optional

from src.utils import get_logger

class DBOperations:
    AUDIO_DIR = "audio_cache"
    DB_PATH = "src/db/audio_cache.db"
    TABLE_PREFIX = "audio_cache"

    def __init__(self):
        self.logger = get_logger(__name__)
        os.makedirs(self.AUDIO_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(self.DB_PATH), exist_ok=True)

        self.conn = sqlite3.connect(self.DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.logger.info(f"SQLite DB initialized at {self.DB_PATH}")

    def _sanitize_table_name(self, voice_id: str) -> str:
        return f"{self.TABLE_PREFIX}_{''.join(c if c.isalnum() else '_' for c in voice_id)}"

    def init_voice_table(self, voice_id: str):
        """Create a table for the given voice_id if not exists."""
        table_name = self._sanitize_table_name(voice_id)
        try:
            with self.conn:
                self.conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        text TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        json_path TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
            self.logger.info(f"Table ensured: {table_name}")
        except Exception as e:
            self.logger.error(f"Failed to create table for {voice_id}: {str(e)}")

    def save_audio(self, text: str, audio_data: bytes, voice_id: str) -> str:
        """Save audio and JSON metadata locally, store entry in voice-specific table."""
        table_name = self._sanitize_table_name(voice_id)
        self.init_voice_table(voice_id)

        try:
            text_hash = abs(hash(text))
            file_name = f"{voice_id}_{text_hash}.mp3"
            json_name = f"{voice_id}_{text_hash}.json"
            file_path = os.path.join(self.AUDIO_DIR, file_name)
            json_path = os.path.join(self.AUDIO_DIR, json_name)

            with open(file_path, "wb") as f:
                f.write(audio_data)

            metadata = {
                "text": text,
                "voice_id": voice_id,
                "file_path": file_path,
                "created_at": datetime.utcnow().isoformat()
            }
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=4)

            with self.conn:
                self.conn.execute(
                    f"INSERT INTO {table_name} (text, file_path, json_path) VALUES (?, ?, ?);",
                    (text, file_path, json_path)
                )

            self.logger.info(f"Saved audio for voice_id='{voice_id}'")
            return file_path
        except Exception as e:
            self.logger.error(f"Failed to save audio for {voice_id}: {str(e)}")
            raise

    def load_audio(self, text: str, voice_id: str) -> Optional[bytes]:
        table_name = self._sanitize_table_name(voice_id)
        try:
            cur = self.conn.execute(
                f"SELECT file_path FROM {table_name} WHERE text=? ORDER BY created_at DESC LIMIT 1;",
                (text,)
            )
            row = cur.fetchone()
            if row and os.path.exists(row["file_path"]):
                with open(row["file_path"], "rb") as f:
                    return f.read()
            return None
        except Exception as e:
            self.logger.error(f"Failed to load audio for {voice_id}: {str(e)}")
            return None

    def load_metadata(self, text: str, voice_id: str) -> Optional[Dict]:
        table_name = self._sanitize_table_name(voice_id)
        try:
            cur = self.conn.execute(
                f"SELECT json_path FROM {table_name} WHERE text=? ORDER BY created_at DESC LIMIT 1;",
                (text,)
            )
            row = cur.fetchone()
            if row and os.path.exists(row["json_path"]):
                with open(row["json_path"], "r", encoding="utf-8") as f:
                    return json.load(f)
            return None
        except Exception as e:
            self.logger.error(f"Failed to load metadata for {voice_id}: {str(e)}")
            return None

    def load_all_audio(self, voice_id: str) -> Dict[str, bytes]:
        table_name = self._sanitize_table_name(voice_id)
        cache = {}
        try:
            cur = self.conn.execute(f"SELECT text, file_path FROM {table_name};")
            rows = cur.fetchall()
            for row in rows:
                if os.path.exists(row["file_path"]):
                    with open(row["file_path"], "rb") as f:
                        audio_data = f.read()
                        text_hash = str(abs(hash(row["text"])))
                        cache_key = f"{voice_id}_{text_hash}"
                        cache[cache_key] = audio_data
            return cache
        except Exception as e:
            self.logger.error(f"Failed to load all audio for {voice_id}: {str(e)}")
            return {}

    def close(self):
        self.conn.close()
        self.logger.info("SQLite connection closed.")
