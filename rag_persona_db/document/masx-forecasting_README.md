# MASX — Autonomous Strategic Forecasting & Doctrine Synthesis Engine

[![GitHub](https://img.shields.io/badge/GitHub-MASX--Forecasting-181717?logo=github)](https://github.com/AteetVatan/masx-forecasting)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![LlamaIndex](https://img.shields.io/badge/LlamaIndex-RAG-blueviolet)](https://www.llamaindex.ai/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**MASX** is the world's most advanced strategic forecasting system. It synthesizes high-velocity "world as events" data through a multi-agent **Council of Doctrines** — generating probabilistic, research-grade geopolitical forecasts grounded in thousands of years of strategic wisdom and modern hybrid warfare principles.

> **GitHub Repository:** [https://github.com/AteetVatan/masx-forecasting](https://github.com/AteetVatan/masx-forecasting)

---

## Table of Contents

- [Core Architecture](#core-architecture)
- [The Forecasting Workflow](#the-forecasting-workflow)
- [23 Doctrine Agents](#23-doctrine-agents)
- [Domain Models](#domain-models)
- [Probabilistic Forecasting & Evaluation](#probabilistic-forecasting--evaluation)
- [Scenario Cockpit & Shell Methodology](#scenario-cockpit--shell-methodology)
- [GDELT Integration](#gdelt-integration)
- [GeoData Agent (LangChain Pipeline)](#geodata-agent-langchain-pipeline)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Configuration](#configuration)
- [Implementation Roadmap](#implementation-roadmap)
- [Testing](#testing)
- [Architecture Diagrams](#architecture-diagrams)

---

## Core Architecture

MASX is built on a **Clean / Hexagonal Architecture** with strict separation of concerns:

- **`core/`** — Pure domain logic with zero I/O dependencies. Contains domain models, agents, scoring, calibration, prompts, and configuration.
- **`integrations/`** — Infrastructure adapters (LlamaIndex, GDELT, LLMs, ChromaDB, storage). Implements ports defined in core.
- **Ports & Adapters** — Core defines `Protocol`-based ports; integrations provide concrete adapters that are injected at runtime.

The system is implemented as a stateful, directed acyclic graph (DAG) using **LangGraph** for orchestration, with **LlamaIndex** serving as the foundational data framework for Retrieval-Augmented Generation (RAG). This ensures that 23 unique doctrine agents have precise, high-fidelity access to their specific strategic corpora.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MASX Engine                                 │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                     core/ (Pure Domain)                      │   │
│  │  ┌──────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐ │   │
│  │  │ Agents   │  │ Forecast  │  │ Scoring & │  │ Doctrine  │ │   │
│  │  │          │  │ Models    │  │Calibration│  │  Packs    │ │   │
│  │  │•Forecster│  │•Forecast  │  │•Brier     │  │•23 JSON   │ │   │
│  │  │•Council  │  │•Scenario  │  │ Score     │  │ templates │ │   │
│  │  │•Scenario │  │•Signpost  │  │•Decomp    │  │•Loader    │ │   │
│  │  │ Gen/Mon  │  │•Evidence  │  │•Calibrate │  │           │ │   │
│  │  │•Question │  │•Outcome   │  │           │  │           │ │   │
│  │  │ Gen      │  │•DoctPack  │  │           │  │           │ │   │
│  │  └──────────┘  └───────────┘  └───────────┘  └───────────┘ │   │
│  │  ┌──────────┐  ┌───────────┐  ┌───────────┐                │   │
│  │  │  Ports   │  │ Constants │  │  Prompts  │                │   │
│  │  │(Protocol)│  │& Enums   │  │           │                │   │
│  │  └──────────┘  └───────────┘  └───────────┘                │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │ Ports                                │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                integrations/ (Adapters)                      │   │
│  │  ┌──────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐ │   │
│  │  │LlamaIndex│  │   GDELT   │  │   LLMs    │  │  Storage  │ │   │
│  │  │•IndexBld │  │•Adapter   │  │•OpenAI    │  │•Forecast  │ │   │
│  │  │•DocReader│  │•Themes    │  │•Claude    │  │ Store     │ │   │
│  │  │•Evidence │  │•Theme Map │  │•Groq      │  │           │ │   │
│  │  │ Retriever│  │           │  │•Gemini    │  │           │ │   │
│  │  │•QueryTool│  │           │  │•Cohere    │  │           │ │   │
│  │  │•LLMAdapt │  │           │  │•Factory   │  │           │ │   │
│  │  └──────────┘  └───────────┘  └───────────┘  └───────────┘ │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌─────────────┐   │
│  │  workers/  │  │processors/ │  │   gedlt/   │  │geo_intel_   │   │
│  │File Watcher│  │Raw Process │  │GDELT V2    │  │agent/       │   │
│  │(watchdog)  │  │            │  │Theme Map   │  │GeoDataAgent │   │
│  └────────────┘  └────────────┘  └────────────┘  └─────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## The Forecasting Workflow

The **Reasoning Loop** is MASX's core forecasting pipeline:

```
  ┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
  │  1. Intake   │────▶│  2. Forecaster    │────▶│  3. LlamaIndex   │
  │  GDELT +     │     │  Decomposes into  │     │  SearchAgent     │
  │  News RSS    │     │  Strategic        │     │  RouterQueryEng  │
  │  (15 min)    │     │  Questions        │     │  Semantic/Summary│
  └─────────────┘     └──────────────────┘     └────────┬─────────┘
                                                         │
  ┌─────────────┐     ┌──────────────────┐     ┌────────▼─────────┐
  │  6. Output   │◀────│  5. Synthesis     │◀────│  4. Doctrine     │
  │  Structured  │     │  Master LLM      │     │  Council         │
  │  Forecast    │     │  Resolves         │     │  3-5 Agents      │
  │  (Pydantic)  │     │  Contradictions   │     │  (Parallel RAG)  │
  └─────────────┘     └──────────────────┘     └──────────────────┘
```

### Step-by-step

1. **Intake Node** — Continuously monitors the GDELT Event Database (georeferenced CAMEO events every 15 minutes) and Multilingual News RSS feeds.
2. **ForecasterAgent** — Decomposes the primary inquiry into "Decisive Strategic Questions." Enforces an **Outside View** (identifying reference class base rates) before proceeding.
3. **LlamaIndex SearchAgent** — Performs agentic retrieval across the Global Knowledge Graph (GKG) and news vectors. Uses LlamaIndex's `RouterQueryEngine` for semantic search or summarized trend overviews.
4. **Doctrine Router & Council** — Analyzes query + evidence to select the top 3–5 most relevant doctrine agents, which then operate in **parallel** as LlamaIndex Document Agents with `QueryEngineTools` mapped to their unique RAG indexes.
5. **Synthesis Node (Master LLM)** — Resolves contradictions between doctrines and outputs a structured probabilistic forecast.
6. **Structured Output** — Every forecast is validated against a Pydantic schema ensuring scientific rigor.

---

## 23 Doctrine Agents

The heart of MASX is **23 distinct AI agents**, each acting as a specialized Query Tool powered by its own LlamaIndex RAG pipeline over a unique strategic doctrine corpus:

### Classical Statecraft
| Agent | Focus |
|---|---|
| **Chanakya (Arthasastra)** | Saptanga (7-limb state) indicators, Upayas (diplomatic methods) |
| **Sun Tzu (Art of War)** | Strategic deception, terrain advantage, intelligence warfare |
| **Mahabharata** | Dharma-yuddha, alliance dynamics, civilizational conflict |
| **Panchatantra** | Political fables, statecraft through narrative wisdom |

### Global Geopolitics
| Agent | Focus |
|---|---|
| **Heartland Theory (Mackinder)** | Pivot area control, land-power dominance |
| **Rimland Theory (Spykman)** | Coastal periphery control, buffer zones |
| **Sea Power (Mahan)** | Maritime choke points, naval superiority |
| **Containment Strategy** | Perimeter defense, alliance encirclement |
| **Kennan Containment** | Cold War containment doctrine, long telegram |

### Power Realism
| Agent | Focus |
|---|---|
| **Diplomacy (Kissinger)** | Triangular diplomacy, balance of power |
| **Great Power Politics (Mearsheimer)** | Power-maximizing revisionism, offensive realism |
| **RAND Corporation** | Systems analysis, nuclear strategy, game theory |
| **Smart Power** | Hybrid hard/soft power integration |

### Hybrid & Cognitive Warfare
| Agent | Focus |
|---|---|
| **Fifth Generation Warfare (5GW)** | Non-state actors, information superiority |
| **Unrestricted Warfare** | Beyond-limits combination strategy |
| **MindWar** | Psychological warfare, perception management |
| **LikeWar** | Social media as battleground, narrative warfare |
| **Wag the Dog** | Media manipulation, manufactured consent |
| **Deep State** | Institutional power structures, bureaucratic warfare |

### Governance & Ethics
| Agent | Focus |
|---|---|
| **Iroquois Great Law of Peace** | Consensus models, "7th Generation" principles |
| **Shivaji (Ganimi Kava)** | Asymmetric guerrilla warfare, fort-centric defense |
| **National Security Strategy** | Presidential doctrine, national interest frameworks |
| **Clash of Civilizations** | Huntington's civilizational fault lines |

Each doctrine has a dedicated JSON template in `masx_ai/data_templates/doctrines/` defining its principles, heuristics, failure modes, recommended tools, and domain fit.

---

## Domain Models

All domain models are Pydantic-validated with strict type hints:

| Model | Description |
|---|---|
| `Forecast` | Core prediction with probability (0–1), confidence interval, key drivers, disconfirming evidence, update triggers, evidence, domain, and doctrine agents used |
| `Evidence` | Source + snippet + relevance score from RAG retrieval |
| `Outcome` | Resolution of a forecast (true/false + date + notes) |
| `Scenario` | Shell methodology future scenario with probability weight, signposts, key assumptions, and early warnings |
| `Signpost` | Observable indicator for scenario monitoring (`not_seen` → `emerging` → `confirmed`) |
| `DoctrinePack` | Agent configuration: principles, heuristics, failure modes, recommended tools, domain fit |
| `BrierDecomposition` | Reliability, resolution, uncertainty, overall Brier score |
| `CalibrationReport` | Bins + per-domain + per-agent Brier scores |

### Domain Enums

| Enum | Values |
|---|---|
| `DoctrineDomain` | geopolitics, economic, military, cyber, civilizational, diplomatic |
| `ForecastStatus` | open, resolved_true, resolved_false, expired |
| `ScenarioStatus` | active, retired, realized |
| `DoctrineStatus` | raw_collected, cleaned, chunked, tagged |
| `EventCategory` | 20 CAMEO codes (01–20): from Verbal Cooperation to Mass Violence |

---

## Probabilistic Forecasting & Evaluation

### Forecast Schema

Every forecast is validated against the `Forecast` Pydantic model:

```python
class Forecast(BaseModel):
    event: str
    horizon: date
    probability: float = Field(ge=0.0, le=1.0)
    confidence_interval: tuple[float, float]
    key_drivers: list[str]
    disconfirming_evidence: list[str]
    update_triggers: list[str]     # Signposts for probability updates
    evidence: list[Evidence]
    domain: DoctrineDomain
    doctrine_agents_used: list[str]
    base_rate: float | None
    status: ForecastStatus
```

### Brier Score Decomposition

The evaluation harness decomposes each forecast's Brier Score into:
- **Reliability** — Calibration accuracy (are 70% predictions correct 70% of the time?)
- **Resolution** — Sharpness (does the model distinguish events well?)
- **Uncertainty** — Climatological base rate contribution

### Calibration Reports

Per-domain and per-agent Brier scores enable continuous learning. The `CalibrationReport` tracks:
- Binned calibration curves
- Domain-level accuracy (`geopolitics`, `military`, etc.)
- Agent-level accuracy (which doctrines contribute most)

---

## Scenario Cockpit & Shell Methodology

MASX uses **Shell International's scenario planning methodology** to construct 3–5 plausible futures:

1. **Scenario Generation** — Doctrine agents generate narratives based on "Critical Uncertainties" (e.g., *Archipelagos* vs. *Surge*).
2. **Signpost Monitoring** — The Scenario Cockpit uses LlamaIndex `SummaryIndex` and `VectorStoreIndex` to track world events as indicators drifting toward specific futures.
3. **Dynamic Weight Updates** — As signposts are confirmed or emerging, scenario probability weights are automatically adjusted and normalized.
4. **Alerts** — Dominant scenarios (P > 50%) and confirmed signposts trigger alerts.

---

## GDELT Integration

MASX integrates with the **GDELT Project** for real-time global event data:

- **GDELT Document API** — Fetches articles via `httpx` with structured queries, returning evidence for forecast generation.
- **GDELT V2 Themes** — Downloads and classifies 50,000+ GDELT theme codes into MASX categories using an LLM-powered classification pipeline.
- **CAMEO Event Taxonomy** — 20-category conflict/cooperation taxonomy (01=Verbal Cooperation through 20=Mass Violence) for event classification.
- **Theme Mapping** — `masx_gdelt_v2_theme_mapping.json` maps GDELT themes to MASX's strategic categories.

---

## GeoData Agent (LangChain Pipeline)

The `GeoDataAgent` in `geo_intelligenge_agent/` provides a secondary data classification pipeline:

- Uses **LangChain** + **Ollama (Llama 3)** for local LLM inference
- Downloads GDELT V2 theme lists and classifies each theme into MASX categories
- Loads known theme descriptions from GDELT's Global Knowledge Graph Category List
- Maps classified themes into a nested MASX category structure
- Outputs `masx_theme_map.json` for use by the forecasting engine

---

## Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| **Reasoning** | Gemini 2.0 Flash / GPT-4o | High-speed, high-context reasoning |
| **Orchestration** | LangGraph | Stateful multi-agent graph with checkpointing |
| **Data Framework** | LlamaIndex | RAG orchestration, document parsing, query tool abstraction |
| **PDF Parsing** | LlamaParse / PyMuPDF | High-accuracy layout parsing of raw doctrine PDFs |
| **Embeddings** | OpenAI `text-embedding-3-small` | Vector embeddings for semantic search |
| **Vector Store** | ChromaDB | Persistent vector storage for doctrine indexes |
| **Ingestion** | GDELT API / BigQuery | Real-time "World as Events" stream |
| **LLM Clients** | OpenAI, Claude, Groq, Gemini, Cohere | Multi-provider LLM support with factory pattern |
| **Local LLM** | Ollama (Llama 3) via LangChain | Local inference for theme classification |
| **Multi-Agent** | AutoGen (pyautogen) | Multi-agent council orchestration |
| **Evaluation** | Pydantic Evals / Brier Score | Forecast calibration and scoring |
| **Validation** | Pydantic v2 | Strict schema validation for all domain objects |
| **Settings** | pydantic-settings | Environment-based configuration (`.env`) |
| **File Watching** | watchdog | Real-time doctrine file ingestion |
| **Web Framework** | FastAPI / Flask | API serving (planned) |
| **HTTP Client** | httpx | Async-first HTTP requests |
| **Observability** | OpenTelemetry | Distributed tracing and metrics |
| **Testing** | pytest | Unit and integration tests |

---

## Project Structure

```
masx-forecasting/
├── app.py                          # Entry point — starts workers
├── app_init.py                     # Application initialization
├── requirements.txt                # Python dependencies
├── Pipfile / Pipfile.lock          # Pipenv lock files
│
├── core/                           # Pure domain logic (no I/O)
│   ├── config/
│   │   ├── settings.py             # AppSettings (pydantic-settings)
│   │   ├── paths.py                # Path constants
│   │   └── log.py                  # Logging configuration
│   ├── domain/
│   │   ├── agents/
│   │   │   ├── forecaster.py       # Main forecast generation pipeline
│   │   │   ├── doctrine_council.py # Multi-agent council orchestration
│   │   │   ├── question_generator.py # Strategic question decomposition
│   │   │   ├── scenario_generator.py # Shell methodology scenarios
│   │   │   ├── scenario_monitor.py # Signpost tracking & weight updates
│   │   │   └── ports.py           # DoctrineAgentPort, EvidenceRetrievalPort
│   │   ├── forecast_models.py      # Forecast, Scenario, Signpost, Evidence, etc.
│   │   ├── scoring.py              # Brier score computation & decomposition
│   │   ├── calibration.py          # Calibration reports (per-domain/agent)
│   │   ├── constants.py            # Enums: DoctrineDomain, EventCategory, etc.
│   │   ├── doctrine_pack.py        # Doctrine JSON template loading
│   │   ├── event_taxonomy.py       # CAMEO event classification
│   │   ├── models.py               # Base models
│   │   ├── exceptions.py           # Domain exception hierarchy
│   │   └── risk/                   # Risk assessment module
│   ├── llm/
│   │   └── ports.py                # LLMClientPort protocol
│   ├── prompts/
│   │   └── prompts.py              # Prompt templates
│   └── doctrine/                   # Doctrine parsing & processing
│       ├── parser.py               # PDF/text doctrine parser
│       ├── text_splitter.py        # Chunking logic
│       ├── metadata/               # Metadata extraction
│       └── processor/              # Doctrine processing pipeline
│
├── integrations/                   # Infrastructure adapters
│   ├── llamaindex/
│   │   ├── index_builder.py        # ChromaDB vector index management
│   │   ├── doctrine_reader.py      # PyMuPDFReader for doctrine PDFs
│   │   ├── evidence_retriever.py   # LlamaIndex RAG evidence retrieval
│   │   ├── doctrine_query_tools.py # QueryEngineTools for agents
│   │   ├── llm_adapter.py          # LlamaIndex LLM adapter
│   │   └── ingest_cli.py           # CLI for doctrine ingestion
│   ├── llms/
│   │   ├── factory.py              # LLM client factory
│   │   ├── base.py                 # Base LLM client
│   │   ├── openai_client.py        # OpenAI GPT adapter
│   │   ├── claude_client.py        # Anthropic Claude adapter
│   │   ├── groq_client.py          # Groq adapter
│   │   ├── gemini_client.py        # Google Gemini adapter
│   │   ├── cohere_client.py        # Cohere adapter
│   │   └── doctrine_agent_adapter.py # Doctrine agent LLM bridge
│   ├── gdelt/
│   │   ├── gdelt_adapter.py        # GDELT Document API integration
│   │   ├── gdelt_themes.py         # GDELT theme management
│   │   └── masx_gdelt_v2_theme_mapping.json
│   ├── storage/
│   │   └── forecast_store.py       # Forecast persistence
│   ├── vectorstore/                # Vector store abstractions
│   ├── analytics/                  # Analytics module (planned)
│   ├── autogen/                    # AutoGen multi-agent (planned)
│   ├── memory/                     # Agent memory (planned)
│   └── scraper/                    # Web scraping (planned)
│
├── workers/
│   ├── base_worker.py              # Base worker class
│   ├── raw_doctrine_handler.py     # Watchdog file event handler
│   └── raw_doctrine_watcher_worker.py # File watcher for new doctrines
│
├── processors/
│   └── raw_process.py              # Raw doctrine text processing
│
├── gedlt/                          # GDELT V2 Theme Classification
│   ├── geldt_v2_themes.py          # Theme downloader & parser
│   ├── masx_gdelt_v2_theme_mapping.json
│   └── constants/
│       ├── masx_keywords.json      # MASX category taxonomy
│       └── GDELT-Global_Knowledge_Graph_CategoryList.csv
│
├── geo_intelligenge_agent/
│   ├── geo_data_agent.py           # LangChain + Ollama classifier
│   └── docs/                       # Agent documentation
│
├── masx_ai/
│   └── data_templates/
│       └── doctrines/              # 23 doctrine JSON templates
│           ├── artofwar.json
│           ├── chanakya_kautilya_arthasastra.json
│           ├── heartland_theory_mackinder.json
│           └── ... (23 total)
│
├── data/
│   ├── doctrines/                  # Processed doctrine data
│   │   ├── raw/                    # Raw PDF doctrine files
│   │   ├── cleaned/                # Cleaned text
│   │   ├── chunks/                 # Chunked for indexing
│   │   └── metadata/               # Extracted metadata
│   └── evolved_doctrines/          # Post-evolution doctrine data
│
├── common/                         # Shared configurations
│   ├── config/
│   └── prompts/
│
├── helpers/
│   └── json_file_helper.py         # JSON read/write utilities
│
├── templates/
│   ├── doctrines/                  # Doctrine display templates
│   └── doctring_metadata/          # Metadata display templates
│
├── tests/
│   ├── test_forecast_models.py     # Domain model tests
│   ├── test_scoring.py             # Brier score tests
│   ├── test_agents/                # Agent unit tests
│   ├── test_api/                   # API tests
│   ├── test_autogen/               # AutoGen integration tests
│   └── test_services/              # Service integration tests
│
├── docs/
│   └── MASX_ The Architectural Blueprint.md
│
├── alerts/                         # Alert system (planned)
├── notifications/                  # Notification system (planned)
├── api/                            # REST API (planned)
├── routes/                         # API routes (planned)
└── deploy/                         # Deployment configurations (planned)
```

---

## Setup & Installation

### Prerequisites

- Python 3.11+
- [Pipenv](https://pipenv.pypa.io/) or pip

### Install

```bash
# Clone the repository
git clone https://github.com/AteetVatan/masx-forecasting.git
cd masx-forecasting

# Using Pipenv (recommended)
pipenv install

# Or using pip
pip install -r requirements.txt
```

### Run

```bash
# Start the forecasting engine
python app.py

# Ingest doctrine PDFs (CLI)
python -m integrations.llamaindex.ingest_cli
```

---

## Configuration

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-...
CLAUDE_API_KEY=sk-ant-...
CLAUDE_URL=https://api.anthropic.com/v1/messages
GROQ_API_KEY=gsk_...
GROQ_URL=https://api.groq.com/openai/v1/chat/completions
GEMINI_API_KEY=...
COHERE_API_KEY=...

# LlamaIndex settings
LLAMAINDEX_EMBED_MODEL=text-embedding-3-small
LLAMAINDEX_CHUNK_SIZE=512
LLAMAINDEX_CHUNK_OVERLAP=64
```

All settings are managed via `pydantic-settings` (`core/config/settings.py`).

---

## Implementation Roadmap

### Engine v1 (Foundational MVP) ✅
- Deploy LlamaIndex with `SimpleDirectoryReader` for initial raw PDF ingestion
- Create 23 individual Vector Indexes, one for each doctrine part
- Expose these as `QueryEngineTools` to a `FunctionAgent` workflow
- Brier Score scoring and calibration harness
- GDELT evidence retrieval adapter
- File-watching worker for automatic doctrine ingestion

### Engine v2 (Research-Grade) 🚧
- **Agentic Retrieval** — Transition to `LlamaCloudIndex` for enterprise-grade managed retrieval
- **Reflection Loops** — LlamaIndex Workflows for structured output validation
- **Cognitive Circuit Breakers** — Retry budgets and loop detection to prevent hallucination loops
- **Full Scenario Cockpit** — Real-time signpost monitoring dashboard
- **Alert System** — Notifications for dominant scenarios and confirmed signposts
- **REST API** — FastAPI endpoints for forecast queries
- **Deployment** — Containerized deployment configuration

---

## Testing

```bash
# Run all tests
pytest

# Run specific test modules
pytest tests/test_scoring.py
pytest tests/test_forecast_models.py
```

Tests follow the **AAA** (Arrange-Act-Assert) pattern using pytest fixtures.

---

## Architecture Diagrams

### High-Level System Architecture

```
                        ┌─────────────────────┐
                        │    MASX Engine       │
                        │    (app.py)          │
                        └─────────┬───────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼              ▼
             ┌───────────┐ ┌──────────┐  ┌────────────┐
             │   Core     │ │ Workers  │  │Integrations│
             │  Domain    │ │          │  │            │
             └─────┬─────┘ └────┬─────┘  └─────┬──────┘
                   │             │               │
          ┌────────┼────────┐    │      ┌────────┼────────┐
          ▼        ▼        ▼    ▼      ▼        ▼        ▼
     ┌────────┐┌───────┐┌──────┐│ ┌──────────┐┌──────┐┌──────┐
     │Forecast││Scoring││Agents│├─│LlamaIndex││ GDELT││ LLMs │
     │ Models ││& Calib││      ││ │ RAG      ││      ││5 APIs│
     └────────┘└───────┘└──────┘│ └──────────┘└──────┘└──────┘
                                │
                         ┌──────┴──────┐
                         │  watchdog   │
                         │ File Watcher│
                         └─────────────┘
```

### Doctrine Council Parallel Processing

```
                    ┌─────────────────┐
                    │  Event Query    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │Question Generator│
                    │ (Strategic Qs)   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Doctrine Router  │
                    │ (Select Top 3-5) │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
   ┌────────────────┐┌───────────────┐┌───────────────┐
   │ Sun Tzu Agent  ││Kissinger Agent││ 5GW Agent     │
   │ ┌────────────┐ ││┌────────────┐ ││┌────────────┐ │
   │ │Art of War  │ │││Diplomacy   │ │││5GW Corpus  │ │
   │ │RAG Index   │ │││RAG Index   │ │││RAG Index   │ │
   │ └────────────┘ ││└────────────┘ ││└────────────┘ │
   └───────┬────────┘└──────┬────────┘└──────┬────────┘
           │                │                │
           └────────────────┼────────────────┘
                            ▼
                   ┌────────────────┐
                   │  Synthesis LLM │
                   │(Master Council)│
                   └────────┬───────┘
                            ▼
                   ┌────────────────┐
                   │  Forecast      │
                   │  (Probabilistic│
                   │   0.00 - 1.00) │
                   └────────────────┘
```

### Data Ingestion Pipeline

```
  Raw PDFs (23 doctrines)          GDELT Real-Time Events
        │                                  │
        ▼                                  ▼
  ┌───────────────┐                ┌───────────────┐
  │  PyMuPDFReader │               │ GDELT Doc API  │
  │  (doctrine_    │               │ (httpx)        │
  │   reader.py)   │               └───────┬───────┘
  └───────┬───────┘                        │
          │                                │
          ▼                                ▼
  ┌───────────────┐                ┌───────────────┐
  │ SentenceSplitter│              │ CAMEO Event    │
  │ (chunk_size=512)│              │ Taxonomy       │
  │ (overlap=64)    │              │ (20 categories)│
  └───────┬─────────┘              └───────┬───────┘
          │                                │
          ▼                                ▼
  ┌───────────────┐                ┌───────────────┐
  │ OpenAI Embed   │               │ Evidence       │
  │ text-embed-3   │               │ Objects        │
  │ -small         │               │ (Pydantic)     │
  └───────┬───────┘                └───────────────┘
          │
          ▼
  ┌───────────────┐
  │ ChromaDB       │
  │ VectorStore    │
  │ (persistent)   │
  └───────────────┘
```

---

## Works Cited

- [The GDELT Project](https://www.gdeltproject.org/)
- [Superforecasting LLM: Advanced Forecasting — Emergent Mind](https://www.emergentmind.com/)
- [Good Judgment Project — AI Impacts](https://aiimpacts.org/)
- [Brier Score — Wikipedia](https://en.wikipedia.org/wiki/Brier_score)
- [Shell's Scenarios: An Explorer's Guide](https://www.shell.com/energy-and-innovation/the-energy-future/scenarios.html)

---

## License

This project is part of the MASX AI ecosystem.

---

<p align="center">
  <b>MASX — Where Ancient Strategy Meets Artificial Intelligence</b>
</p>
