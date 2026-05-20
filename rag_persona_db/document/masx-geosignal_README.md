# MASX-GEOSIGNAL v2 — Dynamic Hotspot Discovery & ETL for MASX-AI

> **CORE ETL PROJECT for the MASX-AI forecasting platform.** Feeds the geopolitical pipeline at https://forecast.masxai.com/.
>
> **GitHub:** https://github.com/AteetVatan/masx-geosignal
> **Local path:** `S:\SYNC\programming\MASX-GEOSIGNAL`

---

## What MASX-GEOSIGNAL Is

MASX-GEOSIGNAL v2 is the **Dynamic Hotspot Discovery Pipeline** that powers global security and geopolitical intelligence for the wider MASX-AI ecosystem. It is the **ETL upstream** of the forecasting platform at https://forecast.masxai.com/ — it produces the hotspots that MASX-AI's Council of 35 Doctrines reasons about.

It runs **once daily at 04:00 UTC** via Railway cron job. Each run executes two coupled pipelines:

- **Hotspot Discovery (s01–s14)** — 14-stage pipeline that ingests, deduplicates, embeds, clusters, scores, and persists hotspots.
- **News Article Generation (n01–n05)** — 5-stage CFR-style article writer that triggers after the hotspot pipeline completes.

---

## Key Decisions (frozen architecture)

| Decision | Choice |
|---|---|
| **ML Runtime** | ONNX-only (no PyTorch at runtime) |
| **Embedding Model** | Multilingual MiniLM-L12-v2 INT8 — 113 MB, 427 MB peak RAM |
| **NER Model** | distilbert-NER via optimum ONNX — 514 MB |
| **RAM Budget** | 32 GB (Railway), INT8 peak 427 MB = ~31.5 GB headroom |
| **Database** | Supabase Postgres + pgvector (384-dim vectors) |
| **Image Storage** | Supabase Storage (WebP, 1200px max, public bucket) |
| **LLM** | DeepSeek V3 primary + Gemini Flash fallback |
| **News Articles** | Gemini 2.5 Flash, CFR-style, 5-stage pipeline, ~$2.85/month |
| **Schedule** | Once daily at 04:00 UTC via Railway cron (`0 4 * * *`) |
| **Deployment** | Railway (cron + web service) + Supabase (DB + Storage) |

---

## Pipeline Stages (s01–s14)

The 14-stage hotspot discovery pipeline progressively:

1. **Ingests** raw HTML via async HTTP (httpx HTTP/2) with domain-level circuit breakers.
2. **Extracts** article text using a 4-method extraction ensemble — **Trafilatura → readability-lxml → jusText → BoilerPy3**. On all-fail, detects reasons: `js_required` triggers Playwright, `paywall` triggers mark-and-skip, `consent` triggers Playwright.
3. **Detects language** using the fastText LID model.
4. **Translates** titles to English via argostranslate.
5. **Extracts named entities (NER)** using `distilbert-base-multilingual-cased-ner-hrl`.
6. **Resolves geo-entities** — LOC/GPE entities → ISO country codes via pycountry.
7. **Deduplicates** content via SHA-256 exact hash + MinHash LSH near-duplicate detection.
8. **Embeds** articles using sentence-transformers (multilingual MiniLM-L12-v2 INT8 ONNX) → pgvector.
9. **Topic prescreen** — IPTC ONNX classifier; excludes sport/lifestyle and positively tags pillar.
10. **Clusters per flashpoint** using kNN graph (cosine similarity ≥ 0.65 default) + Union-Find connected components; dense-rank cluster IDs.
11. **Summarizes** clusters via two-stage pipeline — local DistilBART pre-summary → LLM cluster synthesis (Together AI).
12. **Scores** hotspot intensity using a 4-component weighted formula.
13. **Alerts** via webhook/Slack dispatch.
14. **Writes** final output to `news_clusters`.

---

## News Article Pipeline (n01–n05)

After s01–s14 completes, the news article pipeline generates CFR-style geopolitical articles via Gemini 2.5 Flash in a 5-stage flow that drafts, fact-checks, refines, and stores articles for distribution.

Enabled by env: `NEWS_ARTICLE_ENABLED=true`, `NEWS_ARTICLE_WRITER_API_KEY=<gemini-key>`.

---

## Project Structure

```
src/geosignal/
├── config/         Settings, constants, logging
├── db/             SQLAlchemy Core tables, Pydantic models, repositories
├── pipeline/       14-stage hotspot pipeline (stages/, ml/, nlp/, geo/, scoring/)
├── news_article/   News Article Pipeline (5-stage, triggers after Pipeline 1)
├── ingest/         RSS + API adapters
├── api/            FastAPI application
└── cli/            Click commands

scripts/
├── dev_models.py         Dev: export ONNX + quantize + download fasttext
├── prod_models.py        Prod: download pre-built models from cloud storage
├── seed_domain_tree.py   Seed domain taxonomy
├── seed_regions.py       Seed geographic regions
└── seed_sources.py       Seed RSS/API source registry

models/             ONNX models (gitignored, ~1.2 GB)
research/           Design documents (gitignored)
```

---

## Tech Stack (detail)

- **Language:** Python 3.12+
- **Async HTTP:** httpx (HTTP/2) + aiohttp
- **Database:** SQLAlchemy 2.0 + asyncpg, Alembic migrations
- **Vector DB:** pgvector (HNSW index, 384-dim)
- **Config:** Pydantic Settings
- **Embedding:** sentence-transformers, multilingual MiniLM-L12-v2 INT8 ONNX
- **Language ID:** fastText LID (lid.176.bin)
- **NER:** distilbert-base-multilingual-cased-ner-hrl (ONNX)
- **Geo Resolution:** pycountry
- **Topics:** ONNX IPTC classifier
- **Local Summarization:** DistilBART CNN (PyTorch + ONNX via optimum)
- **Dedupe:** datasketch MinHash LSH + simhash
- **LLM:** DeepSeek V3 (primary) + Gemini 2.5 Flash (fallback / article writer); Together AI for cluster summaries
- **Compression:** zstandard
- **JSON:** orjson + json-repair + rapidjson + pyjson5
- **Logging:** structlog (JSON) + rich (console)
- **CLI:** Click
- **API:** FastAPI + Uvicorn
- **Testing:** pytest + pytest-asyncio + pytest-cov + factory-boy + faker
- **Linting:** Ruff
- **Type Checking:** MyPy (strict)
- **Containerization:** Docker + Docker Compose
- **Deploy:** Railway (cron + web service) + Supabase (DB + Storage)

---

## How It Fits Into MASX-AI

```
[ MASX-GEOSIGNAL v2 ]  →  Supabase hotspots table  →  [ MASX-AI Geo Pipeline ]
   daily 04:00 UTC cron                                  35 Doctrine Council
   14-stage + 5-stage                                    Forecast + Advisor
                                                         forecast.masxai.com
```

MASX-GEOSIGNAL is the **data spine**: it does the heavy lifting on the open web — ingestion, multilingual NLP, deduplication, clustering, scoring, and persistence — so that MASX-AI can spend its compute budget on doctrine-grounded reasoning and probabilistic forecasting.

---

## Why MASX-GEOSIGNAL Matters

- **Production ETL** behind https://forecast.masxai.com/ — every hotspot the doctrine council reasons about flows through this pipeline first.
- **ONNX-only runtime** — no PyTorch at production, INT8 quantized models, 31.5 GB RAM headroom on Railway.
- **Daily 04:00 UTC** Railway cron with reproducible idempotent stages (s01–s14 + n01–n05).
- **Multilingual** — fastText language ID + argostranslate translation + multilingual MiniLM embeddings.
- **Cost-efficient** — DeepSeek V3 primary, local DistilBART pre-summary, Gemini Flash only for the article-writer stage (~$2.85/month).
