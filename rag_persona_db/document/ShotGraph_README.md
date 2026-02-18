# ShotGraph

[![GitHub](https://img.shields.io/badge/GitHub-AteetVatan%2FShotGraph-blue?logo=github)](https://github.com/AteetVatan/ShotGraph)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**AI Cinematic Video Generation Pipeline** — Convert long-form stories into cinematic videos using open-source AI models.

> **Repository**: [https://github.com/AteetVatan/ShotGraph](https://github.com/AteetVatan/ShotGraph)

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Architecture](#system-architecture)
  - [High-Level Architecture](#high-level-architecture)
  - [Pipeline Architecture](#pipeline-architecture)
  - [Agent Pipeline Design](#agent-pipeline-design)
  - [Data Flow](#data-flow)
- [Data Models](#data-models)
- [Cost-Optimized LLM Routing](#cost-optimized-llm-routing)
- [TOON Format](#toon-format)
- [Execution Profiles](#execution-profiles)
- [Mock Asset Generation & Caching](#mock-asset-generation--caching)
- [Automatic GPU Detection](#automatic-gpu-detection)
- [Visual Continuity & Video Stitching](#visual-continuity--video-stitching)
- [Security](#security)
- [Quick Start](#quick-start)
  - [Installation](#installation)
  - [Debugging Installation](#debugging-installation)
  - [Running the API](#running-the-api)
  - [Generate a Video](#generate-a-video)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Development](#development)
  - [Running Tests](#running-tests)
  - [Code Quality](#code-quality)
  - [Debugging Guide](#debugging-guide)
- [Production Deployment](#production-deployment)
  - [Docker](#docker)
  - [Docker Compose (Production)](#docker-compose-production)
  - [RunPod / Cloud GPU](#runpod--cloud-gpu)
  - [Self-Hosted Server](#self-hosted-server)
- [API Endpoints](#api-endpoints)
- [Implementation Phases](#implementation-phases)
- [Acknowledgments](#acknowledgments)
- [License](#license)

---

## Overview

ShotGraph is a modular, multi-agent AI pipeline that transforms text stories into cinematic videos. The system is built on SOLID principles with a clean hexagonal architecture, using:

- **LLMs** (Together.ai with cost-optimized per-stage routing) for scene breakdown and shot planning
- **Diffusion Models** (Stable Video Diffusion) for video generation
- **TTS Models** (Edge TTS) for narration in English and Hindi
- **MusicGen** (Meta AI) for background music generation
- **MoviePy/FFmpeg** for video composition with transitions, subtitles, and audio mixing
- **NLP Preprocessing** for entity extraction, summarization, and story chunking

The system supports dual execution profiles: a lightweight `DEBUG_CPU` mode for fast testing on 16GB RAM laptops, and a full `PROD_GPU` mode for production-quality output on GPU-enabled machines (RunPod, A100, RTX 3090+).

---

## Features

### Core Pipeline
- **Multi-Agent Architecture**: Each pipeline stage (scene splitting, shot planning, video generation, TTS, music, composition) is a separate, testable agent following the single-responsibility principle
- **Pipeline Orchestrator**: Central `VideoGenerationPipeline` coordinates all stages, manages job state, handles errors/retries, and reports progress
- **Pydantic Data Models**: Every agent's input/output is type-validated with Pydantic models (`StoryInput`, `Scene`, `Shot`, `SceneList`, `VideoJob`)
- **Background Job Processing**: Async job queue with status tracking (pending → processing → completed → failed)

### LLM Intelligence
- **Cost-Optimized LLM Routing**: Per-stage model selection reduces costs by 30–40% compared to a single model
- **TOON Format Support**: Token-Oriented Object Notation saves ~40% tokens on output-heavy stages
- **Structured Outputs**: JSON schema validation with automatic repair using Together.ai structured outputs
- **JSON Repair Agent**: Dedicated agent (`JSONRepairAgent`) uses cheap models to fix malformed LLM responses instead of expensive retries
- **Safety Moderation**: Content safety checks before video generation using Llama Guard 4 (VirtueGuard)

### NLP & Preprocessing
- **Story Compression**: Smart summarization that skips processing for short stories (configurable threshold)
- **Entity Extraction**: Automatic extraction of characters, locations, themes, and organizations via NER
- **Token-Aware Chunking**: Splits long stories into LLM-friendly chunks respecting context limits
- **Context Reduction**: Summarization pipeline to condense lengthy narratives while preserving key plot points

### Video & Audio Generation
- **Visual Continuity**: Last-frame initialization for smooth shot transitions
- **Style Context Manager**: Maintains consistent visual style (characters, settings, lighting) across shots
- **Video Effects**: Built-in effects engine for transitions, Ken Burns effects, and frame interpolation
- **Edge TTS Integration**: Cloud-based text-to-speech with multi-language support (English, Hindi)
- **MusicGen Integration**: AI-generated background music with mood-aware prompts

### Video Composition
- **Intelligent Stitching**: Concatenates clips with cross-fade transitions between scenes
- **Audio Mixing**: Automatic ducking (music volume reduced during narration)
- **Subtitle Embedding**: SRT-format subtitle generation and overlay
- **Frame Trimming**: Configurable trimming of corrupt last frames from AI-generated videos
- **Ken Burns Effects**: Simulated camera motion (pan/zoom) on still images for dynamic feel

### Infrastructure
- **Dual Execution Profiles**: `DEBUG_CPU` for local development, `PROD_GPU` for production
- **Automatic GPU Detection**: Falls back gracefully to CPU mode when no GPU is detected
- **Parallel LLM Processing**: Optional parallel shot planning for faster processing
- **Mock Asset Generation**: Fast end-to-end testing without AI models (storyboard images, dummy clips)
- **Cost Tracking**: Automatic logging and reporting of token usage and estimated costs per stage
- **Dependency Injection**: Service interfaces (protocols) with swappable implementations
- **External Prompt Templates**: LLM prompts stored as text files for easy tweaking without code changes

### Security & API
- **API Key Authentication**: Header-based authentication (`X-API-Key`) with configurable enable/disable
- **Rate Limiting**: Configurable per-minute rate limits using `slowapi`
- **CORS Protection**: Configurable allowed origins
- **Non-Root Docker**: Container runs as unprivileged `appuser` (UID 1000)
- **Input Validation**: Min/max story length, word count validation, and size limits (500KB)

---

## System Architecture

### High-Level Architecture

```
┌─────────────────┐
│  FastAPI Server  │  (Orchestrator)
│  /generate      │
│  /status/{id}   │
│  /video/{id}    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Agent Pipeline (Sequential/Parallel)│
│                                      │
│  ┌──────────────────┐               │
│  │ NLP Preprocessing │ ← Entity extraction, summarization, chunking
│  └────────┬─────────┘               │
│           ▼                          │
│  ┌──────────┐  ┌──────────┐         │
│  │ Scene    │→ │ Shot     │         │
│  │ Breakdown│  │ Planning │         │
│  └──────────┘  └────┬─────┘         │
│                     │                │
│         ┌───────────┴───────────┐   │
│         ▼                       ▼   │
│  ┌──────────────┐      ┌──────────────┐
│  │ Visual Asset │      │ Audio        │
│  │ Generation   │      │ Generation   │
│  │ (Diffusion)  │      │ (TTS+Music)  │
│  └──────┬───────┘      └──────┬───────┘
│         │                     │
│         └───────────┬─────────┘
│                     ▼
│            ┌─────────────────┐
│            │ Video Composition│ ← Stitching, transitions, subtitles
│            └─────────────────┘
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  Storage        │  (Local disk or cloud)
│  - Video clips  │
│  - Audio files  │
│  - Final video  │
└─────────────────┘
```

### Pipeline Architecture

```
Story Input
    │
    ▼
┌───────────────────────┐
│ NLP Preprocessing     │ ← Entity extraction, summarization (Step A: Gemma 3N)
│ - Token counting      │
│ - Story chunking      │
│ - Entity extraction   │
│ - Smart summarization │
└───────────────────────┘
    │
    ▼
┌───────────────────────┐
│ Scene Breakdown       │ ← LLM splits story into scenes (Step B: Llama 3.1-8B or Scout)
│ - JSON/TOON output    │
│ - Pydantic validation │
└───────────────────────┘
    │
    ▼
┌───────────────────────┐
│ Shot Planning         │ ← LLM creates shots per scene (Step C: Maverick, can run parallel)
│ - Visual descriptions │
│ - Duration, shot type │
│ - Dialogue extraction │
└───────────────────────┘
    │
    ▼
┌───────────────────────┐
│ JSON Repair (if needed)│ ← Fix malformed JSON (Step D: Llama 3.2-3B)
│ - Structured outputs  │
│ - Schema validation   │
└───────────────────────┘
    │
    ▼
┌───────────────────────┐
│ Safety Check          │ ← Content moderation (Llama Guard 4 / VirtueGuard)
└───────────────────────┘
    │
    ▼
┌───────────────────────┐
│ Video Generation      │ ← Diffusion model generates clips
│ - Text-to-image       │
│ - Image-to-video      │
│ - Last-frame init     │
│ - Style consistency   │
└───────────────────────┘
    │
    ▼
┌───────────────────────┐
│ Audio Generation      │ ← TTS narration + Background music
│ - Edge TTS (EN/HI)   │
│ - MusicGen (moods)    │
│ - Duration matching   │
└───────────────────────┘
    │
    ▼
┌───────────────────────┐
│ Video Composition     │ ← Stitch clips, add audio, subtitles
│ - Cross-fade          │
│ - Audio ducking       │
│ - Subtitle overlay    │
│ - Ken Burns effects   │
│ - Frame trimming      │
└───────────────────────┘
    │
    ▼
Final Video (MP4)
```

### Agent Pipeline Design

The pipeline is composed of specialized agents, each with a clear `run(input) → output` interface:

| # | Agent | Module | Responsibility |
|---|-------|--------|----------------|
| 0 | **NLP Preprocessor** | `core/services/nlp.py` | Token counting, entity extraction (NER), story summarization, LLM-friendly chunking |
| 1 | **Scene Splitter** | `core/agents/scene_splitter.py` | Splits story into logical scenes with summaries using LLM (JSON/TOON) |
| 2 | **Shot Planner** | `core/agents/shot_planner.py` | Breaks each scene into 5–10s cinematic shots with visual descriptions |
| 3 | **JSON Repair** | `core/agents/json_repair.py` | Fixes malformed JSON responses from LLMs using structured outputs |
| 4 | **Video Generator** | `core/agents/video_generator.py` | Generates video clips per shot using diffusion models |
| 5 | **TTS Agent** | `core/agents/audio_tts.py` | Converts dialogue/narration to speech audio (English/Hindi) |
| 6 | **Music Generator** | `core/agents/music_generator.py` | Generates background music matching scene mood |
| 7 | **Video Compositor** | `core/agents/video_compositor.py` | Stitches clips, adds audio, subtitles, transitions |

All agents inherit from `BaseAgent` (`core/agents/base.py`) and follow the dependency injection pattern via protocol interfaces.

### Service Layer

Low-level integrations that agents depend on:

| Service | Module | Purpose |
|---------|--------|---------|
| **LLM Client** | `core/services/llm_client.py` | HTTP client for Together.ai/Groq LLM APIs |
| **Model Router** | `core/services/model_router.py` | Cost-optimized per-stage model selection with fallbacks |
| **NLP Processor** | `core/services/nlp.py` | Story preprocessing, entity extraction, summarization |
| **TOON Parser** | `core/services/toon.py` | Token-Oriented Object Notation encoder/decoder |
| **Vision** | `core/services/vision.py` | Diffusion model video/image generation |
| **TTS** | `core/services/tts.py` | Edge TTS wrapper for text-to-speech |
| **Music** | `core/services/music.py` | MusicGen wrapper for music generation |
| **Video Editing** | `core/services/video_editing.py` | MoviePy/FFmpeg-based video composition |
| **Video Effects** | `core/services/video_effects.py` | Transitions, Ken Burns, frame interpolation |
| **Style Context** | `core/services/style_context.py` | Maintains visual consistency across shots |
| **Device Utils** | `core/services/device_utils.py` | GPU detection, VRAM monitoring, fallback logic |

### Protocol Interfaces

All services implement abstract protocol interfaces for dependency injection:

| Protocol | Module | Interface |
|----------|--------|-----------|
| `ILLMClient` | `core/protocols/llm_client.py` | LLM API calls |
| `INLPProcessor` | `core/protocols/nlp_processor.py` | NLP preprocessing |
| `IVideoGenerator` | `core/protocols/video_generator.py` | Video clip generation |
| `ITTSGenerator` | `core/protocols/tts_generator.py` | Text-to-speech |
| `IMusicGenerator` | `core/protocols/music_generator.py` | Music generation |

### Data Flow

```
1. User submits story → FastAPI receives it → Creates VideoJob → Returns job_id
2. Orchestrator starts pipeline (background task):
   a. Story Ingestion → StoryInput (validated)
   b. NLP Preprocessing → ProcessedStory (entities, chunks, summary, token count)
   c. Scene Breakdown Agent → SceneList (LLM)
   d. For each Scene:
      - Shot Planning Agent → List[Shot] (LLM, optionally parallel)
   e. JSON Repair (if needed) → Fixed JSON → Pydantic re-validation
   f. Safety Check → Pass/Fail
   g. For each Shot:
      - Visual Asset Generation → video_file_path
      - TTS Generation → audio_file_path
   h. Music Generation per Scene → music_file_path
   i. Subtitle Generation → subtitle_file_path
   j. Video Composition → final_video_path
3. Job status updated to "completed", final video available via API
```

---

## Data Models

All data structures are defined as Pydantic models in `core/models.py`:

```python
class Language(str, Enum):
    ENGLISH = "en"
    HINDI = "hi"

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ShotType(str, Enum):
    WIDE = "wide"
    MEDIUM = "medium"
    CLOSE_UP = "close_up"
    ESTABLISHING = "establishing"

class StoryEntities(BaseModel):
    characters: list[str]    # Main characters identified
    locations: list[str]     # Locations/settings
    themes: list[str]        # Key themes/concepts
    organizations: list[str] # Organizations/groups

class ProcessedStory(BaseModel):
    original_text: str       # Original unprocessed text
    chunks: list[str]        # LLM-friendly chunks
    summary: str | None      # Condensed summary
    entities: StoryEntities  # Extracted entities
    token_count: int         # Estimated token count
    was_chunked: bool        # Whether chunking occurred

class StoryInput(BaseModel):
    text: str                # Story text (min 10 chars)
    title: str | None        # Optional title
    language: Language       # Primary language (en/hi)

class Shot(BaseModel):
    id: int                  # Shot ID within scene
    scene_id: int            # Parent scene ID
    description: str         # Visual description for generation
    duration_seconds: float  # Duration (1–30s, default 5s)
    shot_type: ShotType | None
    dialogue: str | None     # Dialogue text for TTS
    subtitle_text: str | None
    video_file_path: str | None
    audio_file_path: str | None

class Scene(BaseModel):
    id: int                  # Scene ID
    text: str                # Original story text
    summary: str             # Brief summary
    shots: list[Shot]        # Shots in this scene
    music_file_path: str | None

class SceneList(BaseModel):
    scenes: list[Scene]

class VideoJob(BaseModel):
    job_id: str              # Unique identifier
    status: JobStatus        # Current status
    story_input: StoryInput  # Original input
    processed_story: ProcessedStory | None
    scenes: SceneList | None
    final_video_path: str | None
    error_message: str | None
    progress: str | None     # e.g. "Generating scene 3 of 10"
    current_stage: str | None
```

---

## Cost-Optimized LLM Routing

ShotGraph uses intelligent model routing via `ModelRouter` to minimize costs while maintaining quality:

| Stage | Model | Cost (per 1M tokens) | Purpose |
|-------|-------|---------------------|---------|
| **Step A** — Story Compression | `google/gemma-3n-E4B-it` | $0.02 / $0.04 | Ultra-cheap summarization |
| **Step A** — Fallback | `meta-llama/Llama-3.2-3B-Instruct-Turbo` | $0.06 / $0.06 | Backup for Step A |
| **Step B** — Scene Breakdown | `meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo` | $0.18 / $0.18 | Standard context |
| **Step B** — Large Context | `meta-llama/Llama-4-Scout-17B-16E-Instruct` | — | Long stories (>8K tokens) |
| **Step C** — Shot Planning | `meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8` | $0.27 / $0.85 | Quality shot descriptions |
| **Step C** — Fallback | `meta-llama/Llama-3.3-70B-Instruct-Turbo` | — | Hard cases |
| **Step D** — JSON Repair | `meta-llama/Llama-3.2-3B-Instruct-Turbo` | $0.06 / $0.06 | Fix malformed responses |
| **Safety** — Moderation | `meta-llama/Llama-Guard-4-12B` | $0.18 / $0.18 | Content safety checks |

**Expected Savings**: 30–40% reduction in LLM costs compared to using a single model throughout.

**Smart Thresholds**:
- Stories < 2,000 tokens skip summarization (configurable via `LLM_SKIP_SUMMARIZATION_THRESHOLD`)
- Stories > 8,000 tokens use large-context model (configurable via `LLM_USE_LARGE_CONTEXT_THRESHOLD`)

---

## TOON Format

ShotGraph supports [TOON (Token-Oriented Object Notation)](https://toonformat.dev/) — a compact, human-readable encoding of JSON designed for LLM prompts. TOON uses indentation and minimal quoting, resulting in ~40% fewer tokens and higher structural accuracy.

**Example** — TOON output for scenes:
```
scenes [3]:
1:
  summary: Hero meets mentor in village...
  text: "...original text..."
2:
  summary: Villain attacks the village...
  text: "...original text..."
3:
  ...
```

Enable/disable via `USE_TOON_FORMAT=true|false` in `.env`. Dedicated scene breakdown and shot planning prompts exist for both JSON and TOON formats in `config/prompts/`.

---

## Execution Profiles

| Profile | Environment | Use Case |
|---------|-------------|----------|
| `DEBUG_CPU` | Local (16GB RAM, no GPU) | Fast pipeline testing with mock services |
| `PROD_GPU` | Cloud/GPU (24GB+ VRAM) | Full-quality video generation |

**Service Injection by Profile**:

| Component | DEBUG_CPU | PROD_GPU |
|-----------|-----------|----------|
| Video Generation | `MockVideoGenerator` (text-on-image storyboards) | `DiffuseVideoGenerator` (Stable Video Diffusion) |
| TTS | `MockTTSGenerator` (silent audio) | Edge TTS (cloud-based) |
| Music | `LoopedMusicGenerator` (looped sample) | `MusicGenGenerator` (Meta MusicGen) |

Set via `EXECUTION_PROFILE=debug_cpu` or `EXECUTION_PROFILE=prod_gpu` in `.env`.

---

## Mock Asset Generation & Caching

In `DEBUG_CPU` mode, the system generates and caches placeholder assets for fast end-to-end testing:

- **Storyboard Images**: PIL-rendered images with shot description text overlaid on colored backgrounds, saved to `assets/mock/`
- **Dummy Video Clips**: 1-second MP4 clips created from storyboard images using MoviePy
- **Audio Stubs**: Silent WAV files of correct duration based on estimated reading speed
- **Music Stubs**: Short looped music clip from `assets/mock/`

Assets are generated on first use and cached for subsequent runs. This enables full pipeline validation on a CPU-only machine in minutes.

---

## Automatic GPU Detection

On startup, `device_utils.py` checks for GPU availability:

1. Attempts `torch.cuda.is_available()` to detect CUDA devices
2. If GPU found → defaults to `PROD_GPU` profile
3. If no GPU → logs warning and falls back to `DEBUG_CPU` mode
4. Manual override available via `EXECUTION_PROFILE` or `GPU_ENABLED` env vars

This ensures the app "just works" on both local laptops and cloud GPU instances.

---

## Visual Continuity & Video Stitching

Multiple strategies ensure cohesive video output:

- **Last-Frame Initialization**: The last frame of shot N is used as the initial frame for shot N+1, carrying over characters, scenery, and lighting
- **Style Context Manager**: Maintains persistent descriptors (character appearance, scene settings, lighting) across shots via `style_context.py`
- **Smooth Transitions**: Cross-fade, fade-to-black, and dissolve effects between shots/scenes via `video_effects.py`
- **Background Music Continuity**: Single music track or thematically consistent loop; cross-fade during scene transitions
- **Audio Ducking**: Music volume automatically reduced when narration is playing
- **Ken Burns Effects**: Simulated pan/zoom on still images for dynamic feel when animation is limited
- **Frame Interpolation**: Optional intermediate frame generation for smooth blending between clips

---

## Security

- **API Key Authentication**: Enabled via `API_KEY_ENABLED=true` with key in `X-API-Key` header
- **Rate Limiting**: Configurable per-minute limits using `slowapi` library
- **CORS Protection**: Configurable allowed origins via `CORS_ORIGINS`
- **Input Validation**: Story size limits (50 chars min, 100K chars max, 500KB max), word count validation (10 words min)
- **Non-Root Docker**: Production container runs as `appuser` (UID 1000)
- **Content Moderation**: Llama Guard 4 safety checks before video generation
- **Resource Limits**: Configurable CPU/memory constraints in Docker Compose

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/AteetVatan/ShotGraph.git
cd ShotGraph

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install development dependencies (see "Debugging Installation" section below)
pip install -r requirements-dev.txt

# Copy environment template
cp env.example .env
# Edit .env with your API keys
```

### Debugging Installation

ShotGraph provides three requirements files for different use cases:

1. **`requirements-dev.txt`** — Minimal dependencies for debugging
   - Lightweight installation (~100MB)
   - No ML libraries (torch, diffusers, etc.)
   - Perfect for testing pipeline flow on CPU-only systems
   - Use with `EXECUTION_PROFILE=debug_cpu` in `.env`

2. **`requirements-dev-full.txt`** — Full dependencies with CPU-only PyTorch
   - All dependencies including ML libraries
   - CPU-only PyTorch (smaller, no CUDA)
   - Suitable for debugging on 16GB RAM systems
   - Installation steps:
     ```bash
     # Install CPU-only PyTorch first (MUST be done before other deps)
     pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

     # Then install remaining dependencies
     pip install -r requirements-dev-full.txt
     ```
   - Use with `EXECUTION_PROFILE=debug_cpu` and `GPU_ENABLED=false` in `.env`

3. **`requirements.txt`** — Full production dependencies with GPU PyTorch
   - Complete production dependencies (CUDA-enabled PyTorch, diffusers, transformers, etc.)
   - Requires GPU and CUDA 12.1+
   - Use with `EXECUTION_PROFILE=prod_gpu` and `GPU_ENABLED=true` in `.env`

> **Recommendation**: Start with `requirements-dev.txt` for quick debugging. Use `requirements-dev-full.txt` if you need all dependencies on a CPU-only system.

### Running the API

```bash
# Start the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Open API docs
# http://localhost:8000/docs
# http://localhost:8000/redoc
```

### Generate a Video

```bash
# Using curl
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{"story": "Once upon a time in a magical kingdom...", "title": "The Quest"}'

# Check status
curl -H "X-API-Key: your_api_key" "http://localhost:8000/status/{job_id}"

# List all jobs
curl -H "X-API-Key: your_api_key" "http://localhost:8000/jobs"

# Download video when complete
curl -O -H "X-API-Key: your_api_key" "http://localhost:8000/video/{job_id}"
```

---

## Configuration

All configuration is via environment variables or `.env` file. See `env.example` for the full template.

```bash
# ─── Execution Profile ───
EXECUTION_PROFILE=debug_cpu          # or prod_gpu
GPU_ENABLED=false

# ─── LLM Configuration ───
LLM_PROVIDER=together               # together, groq
LLM_API_KEY=your_key
LLM_MODEL=mistralai/Mistral-7B-Instruct-v0.3  # Fallback model
LLM_PARALLEL=false                   # Enable parallel shot planning

# ─── Per-Stage Model Configuration (Cost-Optimized Routing) ───
# Step A - Story compression ($0.02/$0.04 per 1M tokens)
LLM_MODEL_STORY_COMPRESS=google/gemma-3n-E4B-it
LLM_MODEL_STORY_COMPRESS_FALLBACK=meta-llama/Llama-3.2-3B-Instruct-Turbo

# Step B - Scene breakdown ($0.18/$0.18 per 1M tokens)
LLM_MODEL_SCENE_DRAFT=meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo
LLM_MODEL_SCENE_DRAFT_LARGE=meta-llama/Llama-4-Scout-17B-16E-Instruct

# Step C - Shot planning ($0.27/$0.85 per 1M tokens)
LLM_MODEL_SHOT_FINAL=meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8
LLM_MODEL_SHOT_FINAL_FALLBACK=meta-llama/Llama-3.3-70B-Instruct-Turbo

# Step D - JSON repair ($0.06/$0.06 per 1M tokens)
LLM_MODEL_JSON_REPAIR=meta-llama/Llama-3.2-3B-Instruct-Turbo

# Safety/moderation
LLM_SAFETY_MODEL=meta-llama/Llama-Guard-4-12B

# ─── Cost Control Thresholds ───
LLM_SKIP_SUMMARIZATION_THRESHOLD=2000    # Skip summarization if story < N tokens
LLM_USE_LARGE_CONTEXT_THRESHOLD=8000     # Use large context model if input > N tokens

# ─── TOON Format ───
USE_TOON_FORMAT=true                     # Saves ~40% tokens on output stages

# ─── Video Generation ───
VIDEO_MODEL=stable-video-diffusion
VIDEO_RESOLUTION=1024x576
VIDEO_FPS=24

# ─── TTS Configuration ───
TTS_VOICE_EN=en-US-AriaNeural
TTS_VOICE_HI=hi-IN-SwaraNeural

# ─── Storage ───
STORAGE_PATH=./output
ASSETS_PATH=./assets

# ─── Security ───
API_KEY_ENABLED=false
API_KEY=your_secret_key
RATE_LIMIT_PER_MINUTE=10
CORS_ORIGINS=[]

# ─── Docker/Production ───
WORKERS=1
HOST=0.0.0.0
PORT=8000
```

---

## Project Structure

```
ShotGraph/
├── app/                        # FastAPI application layer
│   ├── main.py                # API endpoints (/generate, /status, /video, /health, /jobs)
│   ├── main_debug.py          # Debug script for direct pipeline testing
│   ├── schemas.py             # Request/response Pydantic models (GenerateRequest, etc.)
│   ├── dependencies.py        # FastAPI dependency injection (get_pipeline, get_settings)
│   └── security.py            # API key auth, rate limiting, CORS, SecurityDependency
│
├── core/                       # Core domain logic (hexagonal architecture)
│   ├── models.py              # Domain models (StoryInput, Scene, Shot, VideoJob, etc.)
│   ├── constants.py           # Centralized constants and enums
│   ├── exceptions.py          # Custom exception classes
│   ├── orchestrator.py        # VideoGenerationPipeline - coordinates all stages
│   │
│   ├── agents/                # Pipeline agents (each with run() interface)
│   │   ├── base.py            # BaseAgent abstract class
│   │   ├── scene_splitter.py  # SceneSplitterAgent - LLM scene breakdown
│   │   ├── shot_planner.py    # ShotPlannerAgent - LLM shot planning
│   │   ├── json_repair.py     # JSONRepairAgent - fix malformed LLM output
│   │   ├── video_generator.py # VideoGenerationAgent - diffusion model
│   │   ├── audio_tts.py       # TTSAgent - text-to-speech
│   │   ├── music_generator.py # MusicAgent - background music
│   │   └── video_compositor.py# VideoEditingAgent - final composition
│   │
│   ├── protocols/             # Abstract interfaces (dependency inversion)
│   │   ├── llm_client.py      # ILLMClient protocol
│   │   ├── nlp_processor.py   # INLPProcessor protocol
│   │   ├── video_generator.py # IVideoGenerator protocol
│   │   ├── tts_generator.py   # ITTSGenerator protocol
│   │   └── music_generator.py # IMusicGenerator protocol
│   │
│   ├── services/              # Service implementations
│   │   ├── llm_client.py      # Together.ai/Groq HTTP client
│   │   ├── model_router.py    # Cost-optimized per-stage model routing
│   │   ├── nlp.py             # StoryPreprocessor (NER, chunking, summarization)
│   │   ├── toon.py            # TOON format encoder/decoder
│   │   ├── vision.py          # DiffuseVideoGenerator / MockVideoGenerator
│   │   ├── tts.py             # Edge TTS wrapper
│   │   ├── music.py           # MusicGen wrapper
│   │   ├── video_editing.py   # MoviePy/FFmpeg composition engine
│   │   ├── video_effects.py   # Transitions, Ken Burns, frame interpolation
│   │   ├── style_context.py   # Cross-shot visual consistency manager
│   │   └── device_utils.py    # GPU detection, VRAM monitoring
│   │
│   └── schemas/               # JSON schemas for structured LLM outputs
│       └── json_schemas.py    # Scene/Shot JSON schema definitions
│
├── config/                     # Configuration
│   ├── settings.py            # Pydantic Settings (ExecutionProfile, all env vars)
│   ├── prompt_loader.py       # Dynamic prompt template loader
│   ├── logging.conf           # Python logging configuration
│   └── prompts/               # LLM prompt templates (text files)
│       ├── scene_breakdown.txt         # Scene splitting (JSON mode)
│       ├── scene_breakdown_toon.txt    # Scene splitting (TOON mode)
│       ├── shot_planning.txt           # Shot planning (JSON mode)
│       ├── shot_planning_toon.txt      # Shot planning (TOON mode)
│       ├── story_summarization_system.txt
│       ├── story_summarization_user.txt
│       ├── json_repair_system.txt
│       ├── json_repair_user.txt
│       ├── content_moderation_system.txt
│       ├── content_moderation_user.txt
│       └── style_guide.txt
│
├── workers/                    # Background worker setup
│   └── tasks.py               # Async task definitions
│
├── tests/                      # Test suite
│   ├── conftest.py            # Shared fixtures
│   ├── unit/                  # Unit tests
│   └── integration/           # Integration tests
│
├── assets/                     # Static assets
│   └── mock/                  # Mock/placeholder assets for debug mode
│
├── output/                     # Generated videos (gitignored)
├── docs/                       # Documentation
│   ├── code_implementation.md # Full architecture blueprint
│   ├── research.md            # System design & research notes
│   ├── deployment.md          # Production deployment guide
│   └── how_to_debug.md        # Debugging step-by-step guide
│
├── Dockerfile                  # Multi-stage production build (CUDA 12.1)
├── docker-compose.yml          # Development compose
├── docker-compose.prod.yml     # Production compose with resource limits
├── pyproject.toml              # Project metadata, dependencies, tool config
├── requirements.txt            # Production deps (GPU PyTorch)
├── requirements-dev.txt        # Minimal dev deps (no ML libs)
├── requirements-dev-full.txt   # Full dev deps (CPU PyTorch)
├── env.example                 # Development env template
├── env.prod.example            # Production env template
├── scripts/
│   └── start.sh               # Container startup script
└── README.md                   # This file
```

---

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=core --cov=app

# Run specific test file
pytest tests/unit/test_models.py -v

# Run integration tests only
pytest tests/integration/ -v
```

### Code Quality

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Fix lint issues
ruff check --fix .
```

Configuration in `pyproject.toml`:
- Line length: 100
- Target: Python 3.11
- Rules: E, F, I, W, UP, B, SIM

### Debugging Guide

Use the built-in debug script for step-by-step pipeline testing:

```bash
# Recommended method
python -m app.main_debug
```

The debug script will:
1. Start the FastAPI server in a background thread
2. Create a test request with sample story data
3. Call `generate_video` directly (bypassing HTTP)
4. Execute background tasks and display results

**Verify environment configuration:**
```bash
python -c "from config.settings import Settings; s = Settings(); print(f'Profile: {s.execution_profile.value}')"
```

**Test scenarios:**

| Scenario | `.env` Setting | Description |
|----------|----------------|-------------|
| Mock Services (Fast) | `EXECUTION_PROFILE=debug_cpu` | Tests pipeline flow without AI models |
| Real AI Models | `EXECUTION_PROFILE=prod_gpu` | Full end-to-end with GPU |
| API Key Auth | `API_KEY_ENABLED=true` | Test authentication flow |
| Parallel Processing | `LLM_PARALLEL=true` | Test concurrent shot planning |

See [`docs/how_to_debug.md`](docs/how_to_debug.md) for the complete debugging guide.

---

## Production Deployment

### Docker

```bash
# Build image
docker build -t shotgraph:latest .

# Run container
docker run -d \
  --gpus all \
  -p 8000:8000 \
  -e LLM_API_KEY=your_key \
  -e API_KEY=your_secret \
  -v $(pwd)/output:/app/output \
  shotgraph:latest
```

**Dockerfile features:**
- Multi-stage build for smaller image size
- Base: `nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04`
- Non-root user (`appuser`, UID 1000)
- FFmpeg pre-installed
- Health check with 30s interval
- Python 3.11

### Docker Compose (Production)

```bash
# Copy production env template
cp env.prod.example .env.prod

# Edit .env.prod with your values (LLM_API_KEY, API_KEY, etc.)

# Build and start
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Check logs
docker-compose -f docker-compose.prod.yml logs -f

# Verify health
curl http://localhost:8000/health
```

**Production features:**
- Named volumes: `shotgraph_output`, `shotgraph_assets`, `shotgraph_models`
- Configurable resource limits (`CPU_LIMIT`, `MEMORY_LIMIT`)
- Automatic log rotation (10MB max, 3 files)
- Health checks with Docker monitoring

### RunPod / Cloud GPU

1. Build and push image:
   ```bash
   docker build -t your-registry/shotgraph:latest .
   docker push your-registry/shotgraph:latest
   ```
2. Deploy on RunPod with the pushed image
3. Set environment variables via RunPod UI
4. Mount volumes for persistent storage
5. Recommended GPUs: **RTX 3090** or **A100**

### Self-Hosted Server

**Prerequisites:**
- Docker 20.10+
- Docker Compose 2.0+
- NVIDIA Docker runtime (for GPU support)
- CUDA 12.1+ compatible GPU

```bash
git clone https://github.com/AteetVatan/ShotGraph.git
cd ShotGraph
cp env.prod.example .env.prod
# Edit .env.prod
docker-compose -f docker-compose.prod.yml up -d
```

### Security Checklist

- [ ] API key authentication enabled (`API_KEY_ENABLED=true`)
- [ ] Strong API key set (`API_KEY`)
- [ ] CORS origins restricted to your domain
- [ ] Rate limiting configured appropriately
- [ ] Secrets stored securely (not in git)
- [ ] Container runs as non-root user
- [ ] Resource limits set to prevent DoS
- [ ] Health checks enabled
- [ ] Log rotation configured

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/` | No | Redirect to `/docs` |
| `GET` | `/health` | No | Health check (status, version, profile) |
| `POST` | `/generate` | Yes | Start video generation job |
| `GET` | `/status/{job_id}` | Yes | Get job status and progress |
| `GET` | `/jobs` | Yes | List all jobs |
| `GET` | `/video/{job_id}` | Yes | Download completed video |

**Interactive API Docs**: Available at `/docs` (Swagger UI) and `/redoc` (ReDoc).

---

## Implementation Phases

### Phase 1: MVP ✅
- FastAPI skeleton with job tracking
- Story ingestion and validation
- Scene Breakdown Agent (Together.ai LLM)
- Shot Planning Agent with JSON/TOON output
- Mock video/audio generation (debug mode)
- Basic video composition with MoviePy
- End-to-end pipeline test

### Phase 2: Production Readiness
- Error handling & retries with JSON repair
- Cost-optimized model routing (4-stage)
- NLP preprocessing (NER, summarization, chunking)
- Edge TTS integration
- MusicGen integration
- Content safety moderation
- Docker containerization with multi-stage build
- API key authentication & rate limiting

### Phase 3: Scaling & Polish
- Multi-GPU support and parallel processing
- Advanced transitions and video effects
- Frame interpolation for smooth blending
- Style context for visual consistency
- Structured logging and monitoring
- Comprehensive test suite
- Production deployment automation (RunPod)

---

## Acknowledgments

- [Together.ai](https://together.ai) — LLM API with cost-optimized routing
- [Stability AI](https://stability.ai) — Stable Video Diffusion
- [Edge TTS](https://github.com/rany2/edge-tts) — Cloud-based text-to-speech
- [Meta AI](https://ai.meta.com) — MusicGen / AudioCraft
- [TOON Format](https://toonformat.dev/) — Token-Oriented Object Notation for LLM prompts
- [MoviePy](https://zulko.github.io/moviepy/) — Video editing in Python
- [FFmpeg](https://ffmpeg.org/) — Multimedia framework
- [Pydantic](https://docs.pydantic.dev/) — Data validation with Python type hints
- [FastAPI](https://fastapi.tiangolo.com/) — Modern web framework for APIs
- [AI4Bharat](https://ai4bharat.iitm.ac.in/) — Indic language NLP and TTS research

---

## License

MIT License — See [LICENSE](LICENSE) for details.
