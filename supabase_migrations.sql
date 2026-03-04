-- ============================================================
-- EchoAI: Supabase Table Migration
-- Migrates from local SQLite to Supabase Postgres
-- Run this in the Supabase SQL Editor (Dashboard → SQL Editor)
-- ============================================================

-- ── 1. Alter existing audio_cache table ─────────────────────
-- The table already exists with (id, text, voice_id, file_path, created_at).
-- We add: storage_path, file_size_bytes, text_hash and update constraints.

ALTER TABLE audio_cache
    ADD COLUMN IF NOT EXISTS storage_path TEXT,
    ADD COLUMN IF NOT EXISTS file_size_bytes INTEGER,
    ADD COLUMN IF NOT EXISTS text_hash TEXT;

-- Make voice_id NOT NULL (default existing NULLs to 'default')
UPDATE audio_cache SET voice_id = 'default' WHERE voice_id IS NULL;

-- Add unique constraint (idempotent: skip if already exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'audio_cache_text_hash_voice_id_key'
    ) THEN
        ALTER TABLE audio_cache ADD CONSTRAINT audio_cache_text_hash_voice_id_key UNIQUE (text_hash, voice_id);
    END IF;
END $$;

-- Add lookup index
CREATE INDEX IF NOT EXISTS idx_audio_cache_lookup ON audio_cache(text_hash, voice_id);


-- ── 2. Create reply_cache table ─────────────────────────────
CREATE TABLE IF NOT EXISTS reply_cache (
    id SERIAL PRIMARY KEY,
    user_text TEXT NOT NULL,
    response_text TEXT NOT NULL,
    audio_storage_path TEXT,
    text_hash TEXT NOT NULL UNIQUE,
    vector_id TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reply_cache_hash ON reply_cache(text_hash);


-- ── 3. Create Storage bucket (must be done via Dashboard or API) ──
-- Go to Supabase Dashboard → Storage → Create bucket:
--   Name: audio-cache
--   Public: No (private)
--   File size limit: 10MB
-- 
-- Or use the Python migration script which creates it automatically.


-- ── Verify ──────────────────────────────────────────────────
SELECT 'audio_cache columns:' AS info;
SELECT column_name, data_type FROM information_schema.columns 
WHERE table_name = 'audio_cache' AND table_schema = 'public' ORDER BY ordinal_position;

SELECT 'reply_cache columns:' AS info;
SELECT column_name, data_type FROM information_schema.columns 
WHERE table_name = 'reply_cache' AND table_schema = 'public' ORDER BY ordinal_position;
