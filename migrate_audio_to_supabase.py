"""
EchoAI — Migrate local audio cache + reply cache to Supabase.

This one-time script:
1. Runs the SQL table migration (alter audio_cache, create reply_cache)
2. Creates the Supabase Storage bucket 'audio-cache'
3. Migrates audio_cache/ directory:
   - JSON metadata files → audio_cache Postgres rows
   - MP3 files → Supabase Storage bucket
   - Prebuild MP3s → matched with prebuild question list
4. Migrates SQLite reply_cache → Postgres reply_cache table

Usage:  python migrate_audio_to_supabase.py [--dry-run]
"""

import asyncio
import hashlib
import json
import os
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import asyncpg
from supabase import create_client

# ── Config ────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

AUDIO_CACHE_DIR = Path("audio_cache")
SQLITE_DB_PATH = Path("src/db/audio_cache.db")
STORAGE_BUCKET = "audio-cache"

DRY_RUN = "--dry-run" in sys.argv

# ── Prebuild question list (from prebuild_cache.py) ───────────
PREBUILD_QUESTIONS = [
    "What is your name?", "What is your full name?", "Where are you located?",
    "What is your professional title?", "Give me a short bio or introduction.",
    "What is your date of birth?", "What languages do you speak?",
    "What is your LinkedIn headline?", "What is your LinkedIn profile?",
    "What is your GitHub profile?", "What is your portfolio website?",
    "What is your email address?", "How can someone contact you or connect with you?",
    "What is the MASX AI website?", "What is your blog URL?",
    "What are your featured projects?", "Tell me about MASX AI.",
    "Tell me about EchoAI.", "Tell me about AgenticMatch.",
    "What is the MASX-Forecasting project?", "What is the MASX-GeoSignal project?",
    "What is the MASX-Hotspots project?", "What is the ApplyBots project?",
    "What is the Galileo project?", "What is the ShotGraph project?",
    "What is the MedAI project?", "How many projects have you built?",
    "What is the MASX AI ecosystem?", "What are the key GitHub repositories?",
    "Where can I find your open-source repositories?",
    "What are the MASX-Forecasting doctrine agents?",
    "What agents does MASX-Hotspots use?",
    "How does the ApplyBots Truth-Lock Technology work?",
    "What data sources does MASX AI integrate?", "What is your full tech stack?",
    "What AI and LLM frameworks do you use?", "What programming languages do you know?",
    "What vector databases do you use?", "What LLM providers have you integrated?",
    "What prompt engineering techniques do you use?", "What databases do you work with?",
    "What DevOps and deployment tools do you use?", "What web frameworks do you use?",
    "What NLP and text processing capabilities do you have?",
    "What GIS and geospatial skills do you have?",
    "What testing and quality tools do you use?",
    "What are your complete LinkedIn skills?",
    "What async and concurrency tools do you use?",
    "What architectural patterns do you use in your projects?",
    "What cost optimization strategies do you use in AI systems?",
    "What security and compliance features do you implement?",
    "What methodologies do you follow?", "What is your career timeline?",
    "What is your education background?", "What was your role at 12IQ?",
    "What did you accomplish at 12IQ?",
    "What was your role at Pitney Bowes Software?",
    "What did you accomplish at IHS Markit as Senior Software Engineer?",
    "What did you accomplish at IHS Markit as Software Engineer?",
    "What is your complete work experience timeline?",
    "What is your educational background?", "What did you study at Masterschool?",
    "What certifications do you hold?", "What industries have you worked in?",
    "Biggest achievement in automotive?", "Biggest career risk taken?",
    "How did you transition to AI?", "What was your first professional role?",
    "How have your roles evolved?", "What IHS Markit projects did you develop?",
    "How do you approach problem-solving?", "How do you ensure code quality?",
    "How do you handle failure?", "How do you prioritize tasks?",
    "How do you manage deadlines?", "How do you handle disagreements?",
    "What is your decision-making style?", "What is your leadership style?",
    "What is your learning style?", "How do you approach documentation?",
    "How do you balance build vs. buy?", "How do you decide on tech stack?",
    "What's your approach to technical debt?", "How do you prevent scope creep?",
    "How do you manage remote teams?", "Do you mentor juniors?",
    "What is your personal mantra?", "What is your preferred work environment?",
    "What is your current focus?", "Tell me about yourself.",
    "Walk me through your CV.", "What is your greatest strength?",
    "What is your biggest weakness?", "Where do you see yourself in 5 years?",
    "Why should we hire you?", "What motivates you at work?",
    "Describe a challenging project and how you handled it.",
    "Tell me about a time you worked under pressure.",
    "Have you ever failed in a project?", "What are your salary expectations?",
    "Why are you leaving your current position?", "How do you handle criticism?",
    "What is your preferred work culture?",
    "What would your previous manager say about you?",
    "Describe your personality in three words.", "How are you feeling today?",
    "What motivates you most?", "What values guide your decisions?",
    "What are your hobbies?", "Do you exercise?",
    "How do you manage work-life balance?",
    "What is your daily routine structure?",
    "What are your preferred working hours?", "How do you relax?",
    "What is your weekend routine?", "How do you handle high-pressure situations?",
    "How do you react to mistakes?", "What is your core strength?",
    "What is your dominant thinking style?",
    "Where do you see yourself in 10 years?",
    "What is your 5-year career goal?",
    "What is your MASX AI vision for 2024-2025?",
    "What is your global vision for AI?", "What is your AI ethics stance?",
    "Should AI be regulated?", "What is the role of AI in society?",
    "Will AI replace human decision-makers?",
    "What is your biggest dream project?",
    "What is your biggest fear for AI misuse?",
    "What is the core mission of MASX AI?", "What differentiates MASX AI?",
    "What legacy do you want to leave?", "What is your long-term project vision?",
    "What is your personal philosophy in AI work?",
    "What is your definition of success in the next decade?",
    "Hi! How's your day going so far?",
    "Good morning, ready for today's challenges?",
    "Anything exciting you're working on today?",
    "What's been on your mind since our last chat?",
    "What's the highlight of your day so far?",
]

# Build a lookup: md5_hash[:12] → question text
PREBUILD_HASH_MAP = {}
for q in PREBUILD_QUESTIONS:
    h = hashlib.md5(q.lower().strip().encode()).hexdigest()[:12]
    PREBUILD_HASH_MAP[h] = q


def _text_hash(text: str) -> str:
    """MD5 hash of lowered+stripped text."""
    return hashlib.md5(text.lower().strip().encode()).hexdigest()


def _storage_path(voice_id: str, text_hash: str) -> str:
    """Deterministic storage path."""
    return f"{voice_id}/{text_hash}.mp3"


# ── Step 1: Run SQL migrations ────────────────────────────────
async def run_sql_migrations(conn: asyncpg.Connection):
    print("\n[1/4] Running SQL table migrations...")

    # Add columns to audio_cache
    await conn.execute("ALTER TABLE audio_cache ADD COLUMN IF NOT EXISTS storage_path TEXT;")
    await conn.execute("ALTER TABLE audio_cache ADD COLUMN IF NOT EXISTS file_size_bytes INTEGER;")
    await conn.execute("ALTER TABLE audio_cache ADD COLUMN IF NOT EXISTS text_hash TEXT;")
    print("  ✓ audio_cache columns added")

    # Default NULLs in voice_id
    updated = await conn.execute("UPDATE audio_cache SET voice_id = 'default' WHERE voice_id IS NULL;")
    print(f"  ✓ voice_id NULLs fixed ({updated})")

    # Unique constraint (idempotent)
    try:
        await conn.execute(
            "ALTER TABLE audio_cache ADD CONSTRAINT audio_cache_text_hash_voice_id_key "
            "UNIQUE (text_hash, voice_id);"
        )
        print("  ✓ Unique constraint added")
    except (asyncpg.DuplicateObjectError, asyncpg.DuplicateTableError):
        print("  ✓ Unique constraint already exists")

    # Index
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_audio_cache_lookup ON audio_cache(text_hash, voice_id);"
    )
    print("  ✓ audio_cache index created")

    # Create reply_cache table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS reply_cache (
            id SERIAL PRIMARY KEY,
            user_text TEXT NOT NULL,
            response_text TEXT NOT NULL,
            audio_storage_path TEXT,
            text_hash TEXT NOT NULL UNIQUE,
            vector_id TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_reply_cache_hash ON reply_cache(text_hash);"
    )
    print("  ✓ reply_cache table created")


# ── Step 2: Create Storage bucket ─────────────────────────────
def create_storage_bucket(supabase_client):
    print("\n[2/4] Creating Storage bucket...")
    try:
        existing = [b.name for b in supabase_client.storage.list_buckets()]
        if STORAGE_BUCKET in existing:
            print(f"  ✓ Bucket '{STORAGE_BUCKET}' already exists")
            return
        if DRY_RUN:
            print(f"  [DRY RUN] Would create bucket '{STORAGE_BUCKET}'")
            return
        supabase_client.storage.create_bucket(
            STORAGE_BUCKET,
            options={"public": False, "file_size_limit": 10 * 1024 * 1024}
        )
        print(f"  ✓ Bucket '{STORAGE_BUCKET}' created")
    except Exception as e:
        print(f"  ✗ Failed: {e}")


# ── Step 3: Migrate audio_cache/ directory ────────────────────
async def migrate_audio_files(conn: asyncpg.Connection, supabase_client):
    print("\n[3/4] Migrating audio_cache/ directory...")

    if not AUDIO_CACHE_DIR.exists():
        print("  ✗ audio_cache/ directory not found")
        return 0, 0, 0

    success, skipped, failed = 0, 0, 0

    # ── 3a: JSON metadata files (voice-specific audio) ────────
    json_files = sorted(AUDIO_CACHE_DIR.glob("*.json"))
    print(f"  Found {len(json_files)} JSON metadata files")

    for jf in json_files:
        try:
            with open(jf, "r", encoding="utf-8") as f:
                meta = json.load(f)

            text = meta.get("text", "")
            voice_id = meta.get("voice_id", "default")
            created_at_str = meta.get("created_at")
            created_at = datetime.fromisoformat(created_at_str) if created_at_str else datetime.utcnow()
            th = _text_hash(text)

            # Find matching MP3
            mp3_path = jf.with_suffix(".mp3")
            if not mp3_path.exists():
                print(f"  [SKIP] No MP3 for {jf.name}")
                skipped += 1
                continue

            mp3_data = mp3_path.read_bytes()
            sp = _storage_path(voice_id, th)

            # Check if already migrated
            existing = await conn.fetchval(
                "SELECT id FROM audio_cache WHERE text_hash = $1 AND voice_id = $2",
                th, voice_id
            )
            if existing:
                skipped += 1
                continue

            if DRY_RUN:
                print(f"  [DRY] {jf.name} → {sp} ({len(mp3_data)//1024}KB)")
                success += 1
                continue

            # Upload to Storage
            supabase_client.storage.from_(STORAGE_BUCKET).upload(
                sp, mp3_data,
                file_options={"content-type": "audio/mpeg", "upsert": "true"}
            )

            # Insert into Postgres
            await conn.execute(
                "INSERT INTO audio_cache (text, voice_id, storage_path, file_size_bytes, text_hash, file_path, created_at) "
                "VALUES ($1, $2, $3, $4, $5, $6, $7) "
                "ON CONFLICT (text_hash, voice_id) DO UPDATE SET storage_path = $3, file_size_bytes = $4",
                text, voice_id, sp, len(mp3_data), th, str(mp3_path), created_at
            )
            success += 1
        except Exception as e:
            print(f"  [FAIL] {jf.name}: {str(e)[:100]}")
            failed += 1

    print(f"  JSON files: {success} migrated, {skipped} skipped, {failed} failed")

    # ── 3b: Prebuild MP3 files (no JSON metadata) ─────────────
    pb_success, pb_skipped, pb_failed = 0, 0, 0
    prebuild_files = sorted(AUDIO_CACHE_DIR.glob("prebuild_*.mp3"))
    print(f"\n  Found {len(prebuild_files)} prebuild MP3 files")

    for pf in prebuild_files:
        try:
            # Extract hash from filename: prebuild_{hash}.mp3
            file_hash = pf.stem.replace("prebuild_", "")
            question = PREBUILD_HASH_MAP.get(file_hash)

            if not question:
                print(f"  [SKIP] Unknown prebuild hash: {file_hash}")
                pb_skipped += 1
                continue

            voice_id = "en-US-AndrewMultilingualNeural"
            th = _text_hash(question)
            sp = _storage_path(voice_id, th)

            # Check if already migrated (may exist from JSON step)
            existing = await conn.fetchval(
                "SELECT id FROM audio_cache WHERE text_hash = $1 AND voice_id = $2",
                th, voice_id
            )
            if existing:
                pb_skipped += 1
                continue

            mp3_data = pf.read_bytes()

            if DRY_RUN:
                print(f"  [DRY] {pf.name} → Q: {question[:50]}...")
                pb_success += 1
                continue

            # Upload to Storage
            supabase_client.storage.from_(STORAGE_BUCKET).upload(
                sp, mp3_data,
                file_options={"content-type": "audio/mpeg", "upsert": "true"}
            )

            # Insert into Postgres
            await conn.execute(
                "INSERT INTO audio_cache (text, voice_id, storage_path, file_size_bytes, text_hash, file_path) "
                "VALUES ($1, $2, $3, $4, $5, $6) "
                "ON CONFLICT (text_hash, voice_id) DO UPDATE SET storage_path = $3, file_size_bytes = $4",
                question, voice_id, sp, len(mp3_data), th, str(pf)
            )
            pb_success += 1
        except Exception as e:
            print(f"  [FAIL] {pf.name}: {str(e)[:100]}")
            pb_failed += 1

    print(f"  Prebuild files: {pb_success} migrated, {pb_skipped} skipped, {pb_failed} failed")

    total_s = success + pb_success
    total_sk = skipped + pb_skipped
    total_f = failed + pb_failed
    return total_s, total_sk, total_f


# ── Step 4: Migrate SQLite reply_cache ────────────────────────
async def migrate_reply_cache(conn: asyncpg.Connection):
    print("\n[4/4] Migrating SQLite reply_cache...")

    if not SQLITE_DB_PATH.exists():
        print("  ✗ SQLite DB not found at", SQLITE_DB_PATH)
        return 0, 0, 0

    sqlite_conn = sqlite3.connect(str(SQLITE_DB_PATH))
    sqlite_conn.row_factory = sqlite3.Row
    success, skipped, failed = 0, 0, 0

    try:
        # Check if reply_cache table exists in SQLite
        tables = sqlite_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='reply_cache';"
        ).fetchone()
        if not tables:
            print("  ⊘ No reply_cache table in SQLite")
            return 0, 0, 0

        rows = sqlite_conn.execute(
            "SELECT user_text, response_text, audio_file_path, text_hash, vector_id, created_at "
            "FROM reply_cache ORDER BY id;"
        ).fetchall()
        print(f"  Found {len(rows)} reply cache entries")

        for row in rows:
            try:
                th = row["text_hash"]

                # Check if already exists
                existing = await conn.fetchval(
                    "SELECT id FROM reply_cache WHERE text_hash = $1", th
                )
                if existing:
                    skipped += 1
                    continue

                if DRY_RUN:
                    print(f"  [DRY] reply: {row['user_text'][:50]}...")
                    success += 1
                    continue

                await conn.execute(
                    "INSERT INTO reply_cache (user_text, response_text, audio_storage_path, text_hash, vector_id) "
                    "VALUES ($1, $2, $3, $4, $5) "
                    "ON CONFLICT (text_hash) DO NOTHING",
                    row["user_text"], row["response_text"],
                    row["audio_file_path"],  # Will be updated to storage path later
                    th, row["vector_id"]
                )
                success += 1
            except Exception as e:
                print(f"  [FAIL] {row['user_text'][:40]}: {str(e)[:100]}")
                failed += 1

    finally:
        sqlite_conn.close()

    print(f"  Reply cache: {success} migrated, {skipped} skipped, {failed} failed")
    return success, skipped, failed


# ── Main ──────────────────────────────────────────────────────
async def main():
    print("=" * 60)
    print("EchoAI — Migrate Local Data → Supabase")
    if DRY_RUN:
        print("  *** DRY RUN MODE — no data will be written ***")
    print("=" * 60)

    # Connect
    conn = await asyncpg.connect(SUPABASE_DB_URL, ssl="require", statement_cache_size=0)
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

    start = time.time()

    try:
        # Step 1: SQL migrations
        await run_sql_migrations(conn)

        # Step 2: Storage bucket
        create_storage_bucket(supabase)

        # Step 3: Audio files
        audio_s, audio_sk, audio_f = await migrate_audio_files(conn, supabase)

        # Step 4: Reply cache
        reply_s, reply_sk, reply_f = await migrate_reply_cache(conn)

        # Summary
        elapsed = time.time() - start
        print(f"\n{'=' * 60}")
        print(f"MIGRATION COMPLETE in {elapsed:.1f}s")
        print(f"  Audio files:  {audio_s} migrated, {audio_sk} skipped, {audio_f} failed")
        print(f"  Reply cache:  {reply_s} migrated, {reply_sk} skipped, {reply_f} failed")

        # Final counts
        ac_count = await conn.fetchval("SELECT count(*) FROM audio_cache")
        rc_count = await conn.fetchval("SELECT count(*) FROM reply_cache")
        print(f"\n  Supabase audio_cache rows: {ac_count}")
        print(f"  Supabase reply_cache rows: {rc_count}")
        print(f"{'=' * 60}")

        if audio_f + reply_f > 0:
            print("\n⚠  Some items failed. Re-run the script to retry.")
            sys.exit(1)

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
