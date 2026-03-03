# EchoAI - Project Explanation for Clients

> A plain-English walkthrough of what EchoAI is, how it works, and what every technical term means.

---

## What Is EchoAI?

EchoAI is a **voice-powered AI assistant** that you can talk to — just like calling someone on the phone. You speak, it listens, thinks, and talks back. But unlike basic voice assistants (Siri, Alexa), EchoAI has a **memory** and a **knowledge base**. It knows who it represents, remembers what you asked before, and gives answers grounded in real facts rather than making things up.

Think of it as building a **digital clone** of a person — one that can hold natural voice conversations, answer questions about that person's career, skills, and projects, all in real time through a web browser.

---

## How Does a Conversation Work? (The Flow)

Here is the step-by-step journey of a single conversation, from the moment a user speaks to the moment they hear a reply:

```
User speaks into microphone
        ↓
1. SPEECH-TO-TEXT (STT) — Voice is converted to written text
        ↓
2. CACHE CHECK — Have we answered this exact question before?
   ├── YES → Skip to step 5 (instant reply)
   └── NO  → Continue to step 3
        ↓
3. KNOWLEDGE SEARCH (RAG) — Search the knowledge base for relevant info
        ↓
4. AI THINKING (LLM) — The AI reads the retrieved info and writes a reply
        ↓
5. TEXT-TO-SPEECH (TTS) — The written reply is converted back to a human voice
        ↓
User hears the AI speak the answer
```

**Total time from speaking to hearing a reply: under 2-3 seconds.**

### How the Cache Check Works (Step 2 — Deep Dive)

The cache check is the most important performance optimization in EchoAI. Before doing any expensive AI work, we check **4 levels of cache** in order. If any level has the answer, we skip everything below it.

```
User's question arrives
        ↓
Level 1: IN-MEMORY CACHE
  What: A fast short-term memory that lives directly in the server's
        RAM. It holds up to 1,000 question-answer pairs. When it fills
        up, the 100 oldest entries (the ones that were added first)
        are removed in bulk to make room for new ones.
        Think of it like a whiteboard with limited space: when you
        run out of room, you erase the oldest 100 notes in one go.
  Tech: Python dictionary (max 1,000 entries, bulk-evicts 100 at a time)
  Check: Is this exact question already in RAM?
  Speed: ~0ms (instant — no database, no disk, just memory)
  ├── HIT → return answer immediately
  └── MISS ↓
        ↓
Level 2: HASH-BASED EXACT MATCH
  What: We take the user's question and run it through a formula
        called MD5 that turns any text into a unique 32-character
        code (called a "hash"). "What is your email?" always produces
        the exact same hash. We look up that hash in a small local
        database. If found, we already know the answer.
        Think of it like a fingerprint scanner: instead of comparing
        entire sentences word-by-word, we compare short fingerprints.
  Tech: SQLite database + MD5 hashing algorithm
  Check: Compute MD5 hash of the question text, look it up in SQLite
  Speed: ~1ms
  ├── HIT → return cached answer + cached audio file
  └── MISS ↓
        ↓
Level 3: SEMANTIC SIMILARITY SEARCH
  What: This is the smart cache. Even if the user phrases the question
        differently, we can still find the cached answer. We convert
        the question into a list of numbers (a "vector") that captures
        its meaning. Then we compare it to every previously cached
        question's vector using cosine similarity. If the similarity
        score is 95% or higher, we treat it as the same question.
        Example: "What is your email?" and "How do I email you?" are
        different words but ~96% similar in meaning — cache hit.
  Tech: ChromaDB vector database + SentenceTransformers embeddings
  Check: Convert question to a vector, find the closest match
         in the cache. If similarity >= 95% → treat as same question
  Speed: ~50ms
  ├── HIT → return cached answer + cached audio file
  └── MISS ↓
        ↓
Level 4: TTS AUDIO CACHE
  What: Even when we do need to generate a fresh text answer, the
        AI might produce the exact same response text as before
        (e.g., "My email is ab@masxai.com"). In that case, we already
        have a spoken audio file (.mp3) on disk from the last time
        that text was synthesized. We reuse it instead of calling
        the TTS engine again.
        Think of it like a voicemail library: if the message has
        already been recorded, just replay the recording.
  Tech: Disk-based .mp3 file cache
  Check: Even if we need to generate a new text answer, has the
         exact same response text been spoken before?
  Speed: ~5ms (file read from disk)
  ├── HIT → skip TTS synthesis, reuse saved audio
  └── MISS → generate new audio via Edge-TTS, save to disk
```

**Key technologies explained:**

| Technology | What it is | Why we use it |
|-----------|-----------|---------------|
| **LRU Cache** | "Least Recently Used" cache. A fast in-memory store that automatically removes the oldest entries when it fills up (max 1,000). | Fastest possible lookup. If the same question was asked in the last few minutes, it is still in RAM. |
| **MD5 Hash** | A one-way function that turns any text into a fixed 32-character "fingerprint". "What is your email?" always produces the same hash. | Allows instant exact-match lookup in SQLite without comparing full text strings. |
| **SQLite** | A lightweight, file-based database that requires zero setup. It stores the hash-to-answer mappings and audio file paths. | Always available, no external database server needed, zero configuration. |
| **Semantic Similarity** | Instead of matching exact words, we compare the *meaning* of two questions. "What is your email?" and "How can I contact you by email?" score ~96% similar. | Catches rephrased questions that a simple text match would miss. |
| **Cosine Similarity** | The mathematical method used to compare two vectors (numerical fingerprints). A score of 1.0 = identical meaning, 0.0 = completely unrelated. We set the threshold at **0.95** (95%). | Industry-standard way to measure how close two pieces of text are in meaning. |
| **ChromaDB** | An open-source vector database that stores text as numerical vectors and finds the closest matches using cosine similarity. | Purpose-built for this kind of semantic search. Fast, persistent, runs locally. |

**Why 4 levels instead of 1?** Each level trades speed for coverage. Level 1 is the fastest but only catches recent exact matches. Level 3 is slower but catches rephrased questions. By checking in order (fast to slow), most requests get answered at the fastest possible level.

---

## The Voice Pipeline — What Happens When You Speak

This is the core engine of EchoAI. The **Voice Pipeline** (`VoicePipeline`) is the orchestrator that chains every stage together and makes sure the user gets a reply in under 2-3 seconds. Here is exactly what happens, step by step, from the moment a user clicks the microphone to the moment they hear the AI reply.

### Step-by-Step Breakdown (with typical timings)

```
┌─────────────────────────────────────────────────────────────────┐
│  USER CLICKS "TALK TO ME" → microphone activates               │
│  System listens using Voice Activity Detection (VAD).           │
│  When the user speaks, recording starts automatically.          │
│  When 1.5s of silence is detected → audio is sent.             │
│  No stop button needed.                                         │
│  Audio is base64-encoded and sent over WebSocket.               │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 1: Audio Processing + Speech-to-Text (STT)  ~500ms     │
│                                                                 │
│  1. Raw bytes are decoded from base64                           │
│  2. FFmpeg converts WebM/Opus → WAV (PCM 16-bit, mono, 16kHz) │
│  3. Audio is normalized (volume leveled via RMS gain control)   │
│  4. 10ms of silence padded at the end (clean chunk boundary)   │
│  5. Processed WAV is sent to Faster-Whisper (local model)      │
│     └── If Faster-Whisper fails → fallback to OpenAI API      │
│  6. Result: clean text transcription of what the user said     │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 2: RAG + Cache Check + LLM Thinking  ~800-1500ms       │
│                                                                 │
│  SHORTCUT CHECK (before doing any heavy work):                 │
│  ├── In-memory cache (instant, ~0ms)                           │
│  ├── MD5 hash exact match in SQLite (instant, ~1ms)            │
│  └── Semantic similarity in ChromaDB (fast, ~50ms)             │
│      If similarity >= 95% → cached answer + cached audio found │
│      ══════════════════════════════════════════════             │
│      SKIP STAGES 3-4 ENTIRELY → jump to response              │
│      (this is how repeat questions get instant replies)         │
│                                                                 │
│  If no cache hit:                                              │
│  1. Query Router classifies the question (instant, no LLM)     │
│  2. Hybrid search runs (vector + BM25 keyword) on ChromaDB     │
│  3. Retrieved documents + conversation history assembled       │
│  4. LangChain RetrievalQA chain sends everything to the LLM   │
│     Primary: DeepSeek AI                                       │
│     └── If DeepSeek fails → fallback to Mistral AI            │
│  5. LLM generates a grounded answer (temp=0, facts only)      │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 3: Text-to-Speech (TTS)  ~500-800ms                    │
│                                                                 │
│  1. Check if audio for this exact text exists on disk          │
│     └── If YES → load cached .mp3 file (instant)              │
│  2. If no cached audio: Edge-TTS (Microsoft Neural Voices)     │
│     synthesizes the response into natural speech               │
│  3. Generated audio saved to disk for future reuse             │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 4: Store + Respond                                      │
│                                                                 │
│  1. New Q&A pair stored in reply cache (SQLite + ChromaDB)     │
│     so future similar questions are instant                    │
│  2. Audio is base64-encoded and sent back over WebSocket       │
│  3. Browser receives and auto-plays the audio response         │
│  4. Latency stats for every stage are recorded for monitoring  │
└─────────────────────────────────────────────────────────────────┘
```

**How silence detection works (VAD — Voice Activity Detection):**

The browser's **Web Audio API** continuously monitors the microphone input ~60 times per second. Here is what happens on each check:

1. The microphone's raw audio waveform is captured via an `AnalyserNode` (2048 samples per frame)
2. We compute the **RMS** (Root Mean Square) of those samples — a single number representing "how loud is it right now?" (0.0 = dead silent, 1.0 = maximum volume)
3. That RMS value is compared against a **threshold**:
   - `0.01` when idle (very sensitive — picks up any speech)
   - `0.04` when already speaking (slightly higher — ignores minor background noise)
4. **If RMS > threshold** → the user is speaking. Recording starts automatically.
5. **If RMS < threshold** → silence. A timer starts counting.
6. **If silence lasts 1.5 seconds continuously** → the user is done talking. Recording stops and the audio is sent to the server.

The system also supports **interruption**: if the AI is speaking and the user starts talking for more than 500ms, the AI's audio is stopped immediately and a new recording begins. This makes the conversation feel natural — you can interrupt the AI mid-sentence, just like a real phone call.

**Audio format journey — from your microphone to the AI and back:**

| Stage | Format | Why |
|-------|--------|-----|
| **Browser records** | WebM/Opus (or MP4 on Safari) | Efficient, compressed, supported by all modern browsers |
| **Sent over WebSocket** | Base64-encoded binary | WebSocket text frames require text encoding |
| **Server receives** | Raw bytes (WebM/Opus) | Decoded from base64 |
| **FFmpeg converts to** | **WAV, PCM 16-bit, mono, 16kHz** | Standard format that Whisper (STT) expects — uncompressed, single channel, 16,000 samples per second |
| **STT processes** | WAV PCM 16-bit mono 16kHz | Faster-Whisper reads the clean WAV and outputs text |
| **AI reply generated** | Plain text | LLM produces a text response |
| **TTS produces** | **MP3** (via Edge-TTS) | Compressed audio that plays in any browser, small file size for fast delivery |
| **Sent back to browser** | Base64-encoded MP3 | Sent over the same WebSocket connection |
| **Browser plays** | MP3 via `<audio>` element | User hears the AI's spoken reply |

### Three Audio Input Modes

The pipeline supports three ways to receive audio, each suited for different scenarios:

| Mode | How it works | Best for |
|------|-------------|----------|
| **Complete Audio** | User records a full message, then sends it as one blob | Standard conversation (record → stop → send) |
| **Streaming Chunks** | Browser sends audio in small chunks while recording. Server buffers them, then processes all at once when the user stops. | Longer messages where you want progressive upload |
| **Real-Time Buffer** | Audio is processed immediately as it arrives, without waiting for the user to finish | Ultra-low-latency, push-to-talk scenarios |

### How We Keep Latency Low

Getting a voice reply in 2-3 seconds requires optimization at every level. Here is how we achieve it:

**1. Async Everything**
The entire backend is built on Python's `asyncio`. No stage blocks the server. While one user's audio is being transcribed, another user's LLM response can be generated at the same time. This keeps the server responsive even under load.

**2. Cache Shortcuts**
The 4-level cache hierarchy is the single biggest latency saver. If a question (or a semantically similar one) was asked before, we skip the LLM and TTS stages entirely and return the cached audio. Response time drops from ~2-3 seconds to under 100ms.

**3. Startup Warm-Up**
When the server starts, it pre-loads models and caches in the background so the first user does not experience a cold start:
- STT model (Faster-Whisper) is loaded into memory
- LLM connections are initialized
- TTS cache is pre-warmed with common phrases
- RAG knowledge base indexes are loaded

The server accepts connections immediately while warm-up runs in the background. If a request arrives before warm-up finishes, only that specific request waits.

**4. Auto-Failover at Every Stage**
If any component fails, a backup kicks in automatically — no user-visible error, just a slightly different path:

| Stage | Primary | Automatic Backup |
|-------|---------|-------------------|
| STT | Faster-Whisper (local) | OpenAI Whisper API (cloud) |
| LLM | DeepSeek AI | Mistral AI |
| RAG | ChromaDB vector store | MockVectorStore (graceful degradation) |

**5. Per-Component Latency Tracking**
Every single stage is timed independently (STT latency, RAG latency, LLM latency, TTS latency, total pipeline latency). These stats are exposed via a `/stats` API endpoint, allowing us to monitor performance in real time and identify bottlenecks immediately.

**6. Configurable Timeouts**
Each stage has a maximum allowed time: STT (5 seconds), LLM (10 seconds), TTS (8 seconds). If a stage exceeds its timeout, it fails fast and the fallback provider takes over rather than making the user wait.

**7. Connection Management**
Each user gets a unique session ID. WebSocket connections are managed by a `ConnectionManager` that handles per-IP connection limits, per-session rate limiting, and graceful cleanup when users disconnect. Audio buffers are cleared after processing to prevent memory leaks.

### The Result

| Scenario | Typical Response Time |
|----------|----------------------|
| Cache hit (exact or semantic match) | **Under 100ms** |
| RAG hit (knowledge found, LLM answers) | **1.5 - 2.5 seconds** |
| Full pipeline (no cache, no direct knowledge) | **2 - 3 seconds** |
| Repeat question | **Nearly instant** |

---

## Key Technical Terms — Explained Simply

### RAG (Retrieval-Augmented Generation)

**Simple definition:** Instead of the AI making up answers from scratch, we first *search a database* for relevant facts and then *give those facts to the AI* so it can write an informed answer.

**Analogy:** Imagine asking someone a question. Instead of guessing, they first open a filing cabinet, pull out the relevant folder, read it, and *then* answer you. That filing cabinet lookup is the "Retrieval" part. The AI writing the answer after reading it is the "Generation" part.

**Why it matters:** Without RAG, AI models hallucinate (make up facts). With RAG, answers are grounded in real, verified data.

#### How RAG Works in EchoAI (Full Details)

Our RAG system is not a single step. It is a multi-stage pipeline built on **LangChain** (a popular AI orchestration framework). Here is every stage:

**Stage 1 — Query Classification (No AI needed)**
Before searching, a **Query Router** classifies the question using keyword patterns (no LLM call required, so this is instant and free):

| Question type | Where it searches | Example |
|---------------|-------------------|----------|
| Factual | Facts index | "What is your email?" |
| Evidence | Evidence index | "Tell me about the ApplyBots project" |
| Timeline | Both indices | "Walk me through your career" |
| General | Facts index (default) | Any other question |

**Stage 2 — Dual-Index Knowledge Base**
We store knowledge in **two separate ChromaDB collections** (think: two different filing cabinets optimized for different types of questions):

| Index | What it holds | Source data | How it is structured |
|-------|--------------|-------------|---------------------|
| **Facts Index** | Structured Q&A pairs (name, email, skills, bio) | `self_info.json` (curated JSON file) | One document per Q&A pair |
| **Evidence Index** | Full documents, chunked into searchable pieces | Project READMEs (.md), CV (.docx), LinkedIn exports (.csv), PDFs | Header-aware chunking for Markdown (1000 chars, 150 overlap), paragraph chunking for DOCX (800/100), row-based for CSV |

**Stage 3 — Hybrid Search**
For each question, we run **two search strategies in parallel** and merge the results:

1. **Vector similarity search (runs inside ChromaDB)**
   - Every document in the knowledge base has been converted into a list of numbers (a "vector" or "embedding") that captures its *meaning*.
   - When a question arrives, it is also converted into a vector using the same model (`all-MiniLM-L6-v2`).
   - ChromaDB then compares the question's vector against every document's vector using **cosine similarity** (a math formula that scores how close two vectors are, from 0% = unrelated to 100% = identical meaning).
   - The top 4 closest matches are returned.
   - **Why it works:** "What is your job?" and "Tell me about your career" use different words but produce nearly identical vectors, so both find the same documents. This is what makes it *semantic* search — it understands meaning, not just spelling.

2. **BM25 keyword search (runs in Python, outside ChromaDB)**
   - BM25 stands for "Best Matching 25" and is a classic text-ranking algorithm used by search engines since the 1990s.
   - It works by scanning every document for the **exact words** in the question and scoring each document based on:
     - **How often** the search words appear in the document (more = better match)
     - **How rare** those words are across all documents (rare words matter more than common ones like "the" or "is")
     - **How long** the document is (shorter documents with the same keyword count score higher)
   - **Why it works:** If the user asks "Tell me about the ApplyBots project", BM25 will find every document that literally contains the word "ApplyBots". Vector search might miss this if the word is unusual or a proper noun that the embedding model has not seen before.

**Why combine both?** Each method has a blind spot the other covers. Vector search understands meaning but can miss rare proper nouns. BM25 catches exact keywords but misses rephrased questions. Running both together and merging the results (vector results first, then BM25 additions) gives the most complete set of relevant documents.

Results are deduplicated and filtered by metadata tags before being passed to the LLM.

**Stage 4 — Grounded Answer Generation**
The retrieved documents are passed to the LLM via a **LangChain RetrievalQA chain** with strict rules:
- Temperature is **hard-locked to 0** (no creativity, only factual answers)
- The AI uses **ONLY** the retrieved context. It never invents facts.
- If the context does not contain the answer → the AI explicitly says "I don't have that information" instead of guessing
- Output includes: the answer, key facts used, source documents, and the search route taken

**Stage 5 — Reply Caching**
After generating an answer, it is cached at two levels so we never recompute it:
- **MD5 hash** of the exact question text → stored in SQLite for O(1) instant lookup
- **Semantic embedding** of the question → stored in ChromaDB so that *similar* questions (95% match or above) also return the cached answer

**What data feeds the knowledge base:**
- `self_info.json` — Curated personal/professional facts (~90KB)
- GitHub project READMEs (ApplyBots, Galileo, ShotGraph, MASX projects, MedAI)
- CV / resume documents (.docx)
- LinkedIn data exports (skills, projects, endorsements, languages)
- Additional PDFs

All documents get deterministic IDs (SHA-256 for facts, MD5 for evidence) so re-importing the same data never creates duplicates.

#### How We Build the RAG Knowledge Base (The Full Methodology)

Building the knowledge base is a one-time setup step (with optional rebuilds). Here is exactly what happens, from raw files on disk to a searchable vector database ready to answer questions.

```
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: COLLECT RAW DATA                                       │
│                                                                 │
│  We gather all source material into two folders:                │
│                                                                 │
│  Layer A — Facts (self_info.json)                               │
│    A curated JSON file containing structured Q&A pairs.         │
│    Each entry has: doc_type, tags, question, and answer.        │
│    Example: { "doc_type": "about_me",                           │
│               "tags": ["contact", "email"],                     │
│               "question": "What is your email?",                │
│               "answer": "ab@masxai.com" }                       │
│                                                                 │
│  Layer B — Evidence (rag_persona_db/document/)                  │
│    Full documents that provide rich, detailed context:          │
│    • GitHub project READMEs (.md)                               │
│    • CV / resume (.docx)                                        │
│    • LinkedIn data exports (.csv)                               │
│    • Additional PDFs and text files                             │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: VALIDATE & CLEAN (Facts only)                          │
│                                                                 │
│  Each JSON entry is validated against a strict schema           │
│  (using Pydantic). This ensures:                                │
│  • Every record has a non-empty question and answer             │
│  • doc_type is normalized to lowercase                          │
│  • Tags are deduplicated and lowercased                         │
│  • Invalid entries are logged and skipped (not crash-worthy)    │
│                                                                 │
│  Result: a clean, typed list of Q&A records                     │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: CHUNK THE DOCUMENTS (Evidence only)                    │
│                                                                 │
│  Large documents are split into smaller, searchable pieces      │
│  ("chunks"). Each file type gets a different chunking strategy  │
│  optimized for its structure:                                   │
│                                                                 │
│  File Type    │ Chunking Method             │ Chunk Size        │
│  ─────────────┼─────────────────────────────┼───────────────────│
│  Markdown     │ Split by headers (H1-H3),   │ 1,000 chars,     │
│  (.md)        │ then sub-split large         │ 150 char overlap │
│               │ sections                     │                  │
│  Word Doc     │ Extract paragraphs, then     │ 800 chars,       │
│  (.docx)      │ recursive character split    │ 100 char overlap │
│  CSV          │ One text row per record,     │ 800 chars,       │
│  (.csv)       │ combined and split           │ 100 char overlap │
│  PDF          │ Page-by-page extraction,     │ 800 chars,       │
│  (.pdf)       │ then recursive split         │ 100 char overlap │
│  Plain text   │ Recursive character split    │ 800 chars,       │
│  (.txt)       │                              │ 100 char overlap │
│                                                                 │
│  "Overlap" means each chunk shares some text with the next      │
│  chunk. This prevents losing context at chunk boundaries.       │
│  Think of it like overlapping puzzle pieces: the overlap        │
│  ensures that if a sentence is split across two chunks,         │
│  at least one chunk has the complete sentence.                  │
│                                                                 │
│  "Recursive character split" means the system tries to cut      │
│  text at the most natural boundary possible, in this order:     │
│    1. Paragraph breaks (double newline)                         │
│    2. Line breaks (single newline)                              │
│    3. Word boundaries (spaces)                                  │
│    4. Individual characters (last resort)                       │
│  It keeps trying the next separator down the list until every   │
│  chunk fits within the size limit. This way, sentences and      │
│  paragraphs stay intact whenever possible.                  │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: CONVERT TO LANGCHAIN DOCUMENTS                         │
│                                                                 │
│  A "LangChain Document" is a standardized container (like a     │
│  labeled envelope) that LangChain uses to pass text between     │
│  different AI tools. Every tool in the pipeline — ChromaDB,     │
│  BM25, the LLM — expects data in this exact format. By          │
│  converting all our raw text into this common format, every     │
│  component can work together without custom adapters.           │
│                                                                 │
│  Each chunk (or Q&A pair) is wrapped in a LangChain Document    │
│  object with two parts:                                         │
│                                                                 │
│  • page_content: the actual text                                │
│    Facts:    "Q: What is your email?\nA: ab@masxai.com"          │
│    Evidence: "## ApplyBots\nAn AI-powered job application..."   │
│                                                                 │
│  • metadata: labels for filtering and deduplication             │
│    - doc_type (e.g., "about_me", "career")                      │
│    - tags (e.g., ["contact", "email"])                           │
│    - source (original filename)                                 │
│    - stable_id (a unique fingerprint, explained below)          │
│    - layer ("facts" or "evidence")                              │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 5: GENERATE DETERMINISTIC IDs                             │
│                                                                 │
│  Each document gets a unique "stable_id" that never changes     │
│  as long as the content stays the same:                         │
│                                                                 │
│  • Facts: SHA-256 hash of (doc_type + question)                 │
│    "about_me:What is your email?" → always "a3f8d1b6..."        │
│                                                                 │
│  • Evidence: SHA-256 hash of (source filename + chunk number)   │
│    "ApplyBots_readme.md:chunk:3" → always "b4c9e2c7..."        │
│                                                                 │
│  Why this matters: if you re-import the same data, the IDs      │
│  match the existing ones in the database, so the system         │
│  updates them in place instead of creating duplicates.          │
│  This is what "upsert" means — update if exists, insert if new. │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 6: EMBED (Convert Text → Vectors)                         │
│                                                                 │
│  This is the core transformation that makes semantic search     │
│  possible. Each document's text is fed through an AI model      │
│  called SentenceTransformers (model: all-MiniLM-L6-v2) which   │
│  converts it into a list of 384 numbers (a "vector").           │
│                                                                 │
│  "What is your email?" → [0.032, -0.198, 0.445, ..., 0.071]    │
│                           (384 numbers that capture meaning)    │
│                                                                 │
│  These vectors are the numerical fingerprints that allow the    │
│  system to search by meaning rather than exact words.           │
│  The embedding model runs locally on the server, so no text     │
│  is sent to any external API during this process.               │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 7: STORE IN CHROMADB (Dual-Index Architecture)            │
│                                                                 │
│  The embedded documents are stored in two separate ChromaDB     │
│  collections (like two filing cabinets):                        │
│                                                                 │
│  Collection 1: "self_info_facts"                                │
│    Contains: all Q&A pairs from self_info.json                  │
│    Best for: direct factual questions                            │
│                                                                 │
│  Collection 2: "self_info_evidence"                             │
│    Contains: all chunked evidence documents                     │
│    Best for: detailed project/career questions                   │
│                                                                 │
│  Both collections use HNSW (Hierarchical Navigable Small        │
│  World) indexing with cosine similarity. HNSW is a fast         │
│  nearest-neighbor search algorithm that organizes vectors       │
│  into a graph structure so that finding the closest matches     │
│  takes milliseconds, even with thousands of documents.          │
│                                                                 │
│  The database is persisted to disk so it survives server        │
│  restarts. On startup, it is loaded once, then shared           │
│  across all incoming requests (singleton pattern).              │
└─────────────────────────────────────────────────────────────────┘
```

**Two modes of building:**

| Mode | When it runs | What happens |
|------|-------------|--------------|
| **Upsert (default)** | Every server startup | Only adds new or changed documents. Existing documents with the same stable_id are updated in place. Fast and non-destructive. |
| **Full rebuild** | When `SELF_INFO_REBUILD=1` is set | Deletes the entire ChromaDB directory and re-embeds everything from scratch. Used when the data structure changes significantly. |

---

### LLM (Large Language Model)

**Simple definition:** The "brain" of the AI. It reads text and writes human-like responses. Examples include ChatGPT, Claude, and DeepSeek.

**In EchoAI:** We use **DeepSeek AI** as the primary brain, with **Mistral AI** as an automatic backup if DeepSeek goes down.

**Analogy:** If RAG is the filing cabinet, the LLM is the person reading the files and composing a thoughtful reply.

---

### STT (Speech-to-Text)

**Simple definition:** Technology that listens to audio and converts spoken words into written text.

**What we use:**

| Priority | Technology | How it works | Why we chose it |
|----------|-----------|-------------|----------------|
| **Primary** | **Faster-Whisper** (local, `small` model) | Runs directly on our server using CTranslate2 (an optimized inference engine). No audio leaves our infrastructure. | Ultra-low latency (~200-500ms), free, private, no API keys needed |
| **Backup** | **OpenAI Whisper API** (cloud) | If the local model fails or is unavailable, we automatically fall back to OpenAI's cloud-based Whisper service. | High accuracy, always available as a safety net |

**How the audio is processed before STT:**
- Audio arrives as raw bytes via WebSocket (base64-encoded)
- It is decoded, normalized (volume leveled using RMS-based gain control), and tail-padded (10ms silence added at the end for clean boundaries)
- Supports three input modes: full recording, streaming chunks, and real-time buffered streams

**Analogy:** Like a human transcriptionist, but instant and automated. The primary transcriptionist sits in our office (fast, private). If they call in sick, a remote transcriptionist (OpenAI) takes over automatically.

---

### TTS (Text-to-Speech)

**Simple definition:** The opposite of STT. Takes written text and produces a natural-sounding human voice.

**In EchoAI:** We use **Edge-TTS** (Microsoft's neural voices), which produces natural-sounding speech for free.

**Analogy:** The AI writes its answer as text, then this technology "reads it aloud" in a realistic voice.

---

### Vector Database / Embeddings

**Simple definition:** A special database that understands *meaning*, not just exact words. When you ask "What is your job?", it can also find documents about "career", "role", and "position" because it understands they mean the same thing.

**What we use:**
- **ChromaDB** as the vector database (open-source, persisted to disk)
- **SentenceTransformers** with the `all-MiniLM-L6-v2` model to generate embeddings (the numerical fingerprints)
- **HNSW (Hierarchical Navigable Small World)** algorithm with cosine similarity for fast nearest-neighbor search
- Search latency: **under 50ms**

**Analogy:** Normal databases search like a dictionary (exact word match). Vector databases search like a librarian who understands your question and brings you the right book, even if you did not use the exact title.

---

### WebSocket

**Simple definition:** A persistent two-way connection between the user's browser and the server. Unlike regular web requests (ask-and-wait), WebSockets keep the line open so data flows in real time in both directions.

**In EchoAI:** Audio streams from the user's microphone to the server, and audio responses stream back, all over a single open WebSocket connection. This is what makes the conversation feel live and instant, like a phone call rather than a web form.

---

### Agentic AI / Agentic Architecture

**Simple definition:** The AI does not just answer one question in isolation. It acts more like a team of specialized workers who hand tasks to each other automatically. One agent handles listening, another searches for knowledge, another thinks, another speaks.

**In EchoAI:** The system coordinates multiple agents in a pipeline:
- **STT Agent** — Converts voice to text
- **RAG Agent** — Searches knowledge and manages caching
- **LLM Agent** — Generates the answer
- **TTS Agent** — Converts the answer to speech

Each agent works independently and can be swapped out without breaking the others.

---

### Caching (Multi-Level)

**Simple definition:** Storing answers we have already computed so we do not have to redo the work. If someone asks the same question twice, the second time is instant.

**In EchoAI:** We have **4 levels** of caching:
1. **In-Memory** — Answers stored in RAM (fastest, instant recall)
2. **Hash Lookup** — Exact question match in a local database
3. **Semantic Search** — "Close enough" question match using meaning (95% similarity threshold)
4. **Audio Cache** — Pre-generated voice files stored on disk

---

### LangChain

**Simple definition:** A popular framework (toolkit) for building AI applications that combine LLMs with external data sources. It handles the plumbing of connecting the knowledge search to the AI brain.

**In EchoAI:** LangChain orchestrates the RAG pipeline. It takes the user's question, searches the knowledge base, assembles the context, and passes everything to the LLM in the right format.

---

### Knowledge Base / Self-Info

**Simple definition:** The structured data that the AI draws its answers from. In EchoAI, this includes career history, skills, projects, education, and personal info, loaded from a curated JSON file and supporting documents (CVs, project READMEs, LinkedIn data).

**Two types of knowledge are stored:**

| Type | What it contains | Example |
|------|-----------------|---------|
| **Facts** | Structured Q&A pairs | "What is your email?" → "ab@masxai.com" |
| **Evidence** | Full documents, chunked for search | Project READMEs, CV, LinkedIn exports |

---

### Hybrid Search (Vector + BM25)

**Simple definition:** We use two search methods together for better results:
- **Vector search** converts text into numerical fingerprints (vectors) and finds documents with similar meaning, even if they use completely different words. This runs inside **ChromaDB**.
- **BM25 search** is a traditional keyword-scoring algorithm (used by Google in its early days). It ranks documents by how well their words match the question, with bonus points for rare and specific terms. This runs in **Python** alongside ChromaDB.

**Analogy:** Vector search is like asking a librarian "I need something about career history" — they understand your intent and bring relevant books. BM25 search is like using a book's index to look up exact words. Using both together means you never miss a result.

---

### FastAPI

**Simple definition:** The web framework (written in Python) that powers the backend server. It handles incoming requests, manages WebSocket connections, and routes everything to the right processing pipeline.

**Why FastAPI:** It is one of the fastest Python web frameworks and has built-in support for WebSockets and asynchronous operations, both critical for real-time voice chat.

---

### Next.js (Frontend)

**Simple definition:** The framework used to build the web interface (what you see in the browser). It is built on React and provides a fast, modern, interactive user experience.

**In EchoAI:** The frontend provides a chat interface where users can type or speak, see AI responses appear in real time, and toggle between text and voice modes.

---

## Architecture at a Glance

```
┌──────────────────────────────────────────────────────────────┐
│                    USER'S BROWSER                            │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  Next.js Frontend (Chat UI, Voice Input, Playback)  │     │
│  └────────────────────────┬────────────────────────────┘     │
└───────────────────────────┼──────────────────────────────────┘
                            │ WebSocket (real-time audio)
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                    BACKEND SERVER                             │
│                                                              │
│  ┌──────────┐   ┌──────────────┐   ┌──────────┐             │
│  │   STT    │──▶│  RAG Engine   │──▶│   TTS    │             │
│  │ (Voice → │   │ (Search +     │   │ (Text →  │             │
│  │  Text)   │   │  AI Thinking) │   │  Voice)  │             │
│  └──────────┘   └──────┬───────┘   └──────────┘             │
│                        │                                     │
│              ┌─────────▼─────────┐                           │
│              │  Knowledge Base   │                           │
│              │  (ChromaDB +      │                           │
│              │   Self-Info JSON) │                           │
│              └───────────────────┘                           │
└──────────────────────────────────────────────────────────────┘
```

---

## What Makes EchoAI Special?

| Feature | What it means for the end user |
|---------|-------------------------------|
| **Real-time voice** | Talk and get spoken replies in 2-3 seconds |
| **Remembers context** | Ask follow-up questions and the AI keeps track |
| **Fact-grounded answers** | No hallucinations. Every answer comes from verified data |
| **Multi-level caching** | Repeated questions get instant replies |
| **Auto-failover** | If one AI provider goes down, a backup kicks in automatically |
| **Web-based** | No app install needed. Works in any modern browser |
| **Deployable anywhere** | Runs on Docker, deployable to Railway, Vercel, or any cloud |

---

## Tech Stack Summary

| Layer | Technology | Role |
|-------|-----------|------|
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS | Web chat interface |
| **Backend** | Python, FastAPI | Server, API, WebSocket handler |
| **Voice In** | Faster-Whisper (local) + OpenAI Whisper (backup) | Speech-to-Text |
| **Voice Out** | Edge-TTS (Microsoft Neural Voices) | Text-to-Speech |
| **AI Brain** | DeepSeek AI (primary) + Mistral AI (backup) | Response generation |
| **Knowledge Search** | LangChain + ChromaDB + BM25 | RAG pipeline |
| **Databases** | SQLite (local cache) + Supabase PostgreSQL (cloud) + ChromaDB (vectors) | Data storage |
| **Deployment** | Docker + Railway | Hosting and scaling |

---

## Glossary Quick Reference

| Term | One-Line Definition |
|------|-------------------|
| **RAG** | Search a knowledge base first, then let AI answer using those facts |
| **LLM** | The AI brain that reads and writes human-like text |
| **STT** | Converts spoken words into written text |
| **TTS** | Converts written text into spoken words |
| **Vector Database** | A database that searches by meaning, not just keywords |
| **Embeddings** | Numerical fingerprints that capture the meaning of text |
| **WebSocket** | A live two-way connection for real-time data exchange |
| **Agentic AI** | Multiple AI agents working together as a coordinated team |
| **Caching** | Storing past answers so repeat questions are instant  |
| **LangChain** | A toolkit for connecting AI models to external data sources |
| **FastAPI** | A fast Python web framework for building APIs |
| **Next.js** | A React-based framework for building modern web interfaces |
| **ChromaDB** | An open-source vector database for semantic search |
| **Hybrid Search** | Combining meaning-based and keyword-based search for best results |
| **Knowledge Base** | The curated data the AI uses to answer questions accurately |

---

*Document prepared for client briefing. For the full technical README, see [readme.md](readme.md).*
