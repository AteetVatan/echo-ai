# 🛠️ EchoAI — Setup & Run Guide

Step-by-step instructions to get EchoAI running on your local machine.

---

## 📋 Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| **Python** | 3.9+ (3.11 recommended) | Backend runtime |
| **Node.js** | 18+ | Frontend build tooling |
| **npm** | 9+ | Comes with Node.js |
| **Git** | Any | To clone the repo |
| **Supabase account** | — | Database + Storage ([supabase.com](https://supabase.com)) |
| **Docker** *(optional)* | 20+ | For containerised deployment |

### API Keys Required

You will need at least one of the following LLM API keys:

| Key | Required | Purpose |
|-----|----------|---------|
| `DEEPSEEK_API_KEY` | **Yes** | Primary LLM |
| `OPENAI_API_KEY` | Recommended | STT fallback (Whisper API) |
| `MISTRAL_API_KEY` | Recommended | Fallback LLM |
| `SUPABASE_URL` | **Yes** | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | **Yes** | Supabase service role key (Settings → API) |
| `SUPABASE_DB_URL` | **Yes** | Supabase Postgres connection string |

---

## 🚀 Quick Start (Manual)

### 1. Clone the Repository

```bash
git clone https://github.com/AteetVatan/echo-ai.git
cd echo-ai
```

### 2. Create & Activate a Virtual Environment

```bash
# Create
python -m venv .venv

# Activate (pick your OS)
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (CMD)
.venv\Scripts\activate.bat

# macOS / Linux
source .venv/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> ⏳ This installs PyTorch, Transformers, Supabase, LangChain, etc. — the first install may take several minutes.

### 4. Configure Environment Variables

```bash
# Copy the template
cp env.example .env        # Linux / macOS / Git Bash
copy env.example .env      # Windows CMD
```

Open `.env` in your editor and fill in **at minimum**:

```dotenv
DEEPSEEK_API_KEY=sk-your-deepseek-key
OPENAI_API_KEY=sk-your-openai-key
MISTRAL_API_KEY=your-mistral-key
```

See the full [Environment Variables Reference](#-environment-variables-reference) below for all options.

### 5. Start the Backend Server

```bash
python run_dev.py
```

This starts both development servers:
- **FastAPI hot reload** on port 8000
- **Next.js hot reload** on port 3000
- **CORS** configured for development

The development app will be available at:

| URL | Description |
|-----|-------------|
| `http://localhost:8000` | Backend API root |
| `http://localhost:8000/docs` | Interactive Swagger docs |
| `http://localhost:8000/health` | Health-check endpoint |
| `http://localhost:3000` | Next.js web client |
| `http://localhost:8000/frontend` | Legacy dev redirect to the web client |
| `http://localhost:8000/api/chat` | REST chat endpoint (POST) |
| `http://localhost:8000/api/persona` | Persona info endpoint (GET) |

### 6. Set Up & Start the Frontend Manually

The Next.js frontend (React 19 + Tailwind CSS v4) can also be run manually.

Open a **second terminal** (keep the backend running):

```bash
cd frontend
npm install
npm run dev
```

The Next.js dev server will start on `http://localhost:3000`.

### 7. Set Up Supabase Database

EchoAI uses Supabase for audio caching, reply caching, and vector search (pgvector).

#### a) Get your Supabase credentials

1. Go to [supabase.com](https://supabase.com) → create a project (or use existing)
2. **Settings → API** → copy `URL` and `service_role` secret key
3. **Connect button** (top of dashboard) → copy the `URI` connection string
4. Add all three to `.env`:
   ```dotenv
   SUPABASE_URL=https://YOUR_PROJECT.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=sb_secret_...
   SUPABASE_DB_URL=postgresql://postgres.YOUR_PROJECT:PASSWORD@aws-0-REGION.pooler.supabase.com:6543/postgres
   ```

#### b) Create database tables

Run the SQL migration in the **Supabase SQL Editor** (Dashboard → SQL Editor → New query):

```sql
-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Audio cache (TTS audio metadata)
CREATE TABLE IF NOT EXISTS audio_cache (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    voice_id TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    file_size_bytes INTEGER,
    text_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(text_hash, voice_id)
);
CREATE INDEX IF NOT EXISTS idx_audio_cache_lookup ON audio_cache(text_hash, voice_id);

-- Reply cache (Q&A pairs)
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

-- Vector search tables (pgvector, 384-dim for all-MiniLM-L6-v2)
CREATE TABLE IF NOT EXISTS documents_reply_cache (
    id TEXT PRIMARY KEY, content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}', embedding vector(384)
);
CREATE TABLE IF NOT EXISTS documents_self_info_facts (
    id TEXT PRIMARY KEY, content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}', embedding vector(384)
);
CREATE TABLE IF NOT EXISTS documents_self_info_evidence (
    id TEXT PRIMARY KEY, content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}', embedding vector(384)
);
```

#### c) Create the Storage bucket

1. Dashboard → **Storage** → **New bucket**
2. Name: `audio-cache`, Public: No, File size limit: 10MB

#### d) Run data migration (if upgrading from local storage)

```bash
# Migrate local audio_cache/ directory + SQLite data → Supabase
python migrate_audio_to_supabase.py
```

---

## 🐳 Quick Start (Docker)

```bash
# 1. Clone
git clone https://github.com/AteetVatan/echo-ai.git
cd echo-ai

# 2. Configure environment
cp env.example .env
# Edit .env with your API keys

# 3. Build the image
docker build -t echoai .

# 4. Run the container
docker run -p 8000:8000 --env-file .env echoai
```

The backend is now accessible at `http://localhost:8000`.

> **Note:** For local development, `python run_dev.py` starts the backend and Next.js frontend together. If you run the backend manually, start the frontend separately as described in step 6 above.

---

## 🧪 Running Tests

```bash
# Make sure your virtual environment is active

# Run all tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_self_info_loader.py -v
python -m pytest tests/test_self_info_rag_smoke.py -v
python -m pytest tests/test_self_info_retriever.py -v
```

---

## 🔧 Optional: Build the RAG Knowledge Index

EchoAI ships with a CLI tool to build and query the self-info vector index:

```bash
# Build the vector index from self_info.json + evidence documents
python -m src.tools.self_info_cli build

# Ask a question against the index
python -m src.tools.self_info_cli ask "What is your email?"
```

---

## 📝 Environment Variables Reference

All variables are configured in the `.env` file. Below is the full list:

### API Keys & Models

| Variable | Default | Description |
|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | — | DeepSeek API key (primary LLM) |
| `OPENAI_API_KEY` | — | OpenAI API key (STT fallback) |
| `MISTRAL_API_KEY` | — | Mistral AI API key (fallback LLM) |
| `DEEPSEEK_MODEL` | `deepseek-chat` | DeepSeek model name |
| `DEEPSEEK_API_BASE` | `https://api.deepseek.com` | DeepSeek API base URL |
| `MISTRAL_MODEL` | `mistral-large-latest` | Mistral model name |
| `MISTRAL_API_BASE` | `https://api.mistral.ai` | Mistral API base URL |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model name |
| `FALLBACK_STT_MODEL` | `openai/whisper-1` | Fallback STT model for transcription |

### TTS Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `EDGE_TTS_VOICE` | `en-IN-PrabhatNeural` | Microsoft Edge neural TTS voice |

### Latency Tuning

| Variable | Default | Description |
|----------|---------|-------------|
| `STT_CHUNK_DURATION` | `2.0` | STT chunk duration in seconds |
| `LLM_TEMPERATURE` | `0.0` | LLM temperature (0 = deterministic) |
| `TTS_STREAMING` | `True` | Enable TTS streaming |
| `TTS_CACHE_ENABLED` | `True` | Enable TTS audio caching |

### Self-Info RAG Knowledge Base

| Variable | Default | Description |
|----------|---------|-------------|
| `SELF_INFO_JSON_PATH` | `src/documents/self_info.json` | Path to the persona JSON knowledge file |
| `SELF_INFO_REBUILD` | `0` | Set to `1` to force-rebuild the vector index on startup |
| `EVIDENCE_DOCS_DIR` | `rag_persona_db/document` | Directory containing evidence documents for RAG |

### Database (Supabase — Required)

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPABASE_URL` | — | Supabase project URL (required) |
| `SUPABASE_ANON_KEY` | — | Supabase anon/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | — | Supabase service role key (required) |
| `SUPABASE_DB_URL` | — | Full Supabase PostgreSQL connection URL (required) |

### Server & Audio

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server bind host |
| `PORT` | `8000` | Server bind port |
| `LOG_LEVEL` | `INFO` | Logging level |
| `DEBUG` | `False` | Enable debug mode |
| `SAMPLE_RATE` | `16000` | Audio sample rate (Hz) |
| `CHANNELS` | `1` | Audio channels |
| `AUDIO_FORMAT` | `wav` | Audio format |
| `STT_TIMEOUT` | `5.0` | STT timeout (seconds) |
| `LLM_TIMEOUT` | `10.0` | LLM timeout (seconds) |
| `TTS_TIMEOUT` | `8.0` | TTS timeout (seconds) |

---

## ❓ Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError` | Make sure the virtual environment is activated and `pip install -r requirements.txt` completed successfully. |
| PyTorch install fails | Try installing PyTorch separately first: `pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu` |
| `.env` not found error | Copy `env.example` to `.env` and fill in your API keys. |
| Port 8000 already in use | Change `PORT` in `.env`, or stop the other process. |
| Supabase connection error | Verify `SUPABASE_DB_URL` format is `postgresql://postgres.PROJECT:PASSWORD@...pooler.supabase.com:6543/postgres` |
| Frontend `npm install` fails | Delete `node_modules` and `package-lock.json` in `frontend/`, then retry. |
| pgvector extension error | Enable pgvector via Supabase SQL Editor: `CREATE EXTENSION IF NOT EXISTS vector;` |
