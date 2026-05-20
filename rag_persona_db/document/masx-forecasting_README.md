# MASX-AI — Autonomous Multi-Domain Strategic Forecasting Engine

> **PRIMARY / FLAGSHIP PROJECT** — One of Ateet Bahamani's three most important live AI platforms.
>
> **Geopolitical pipeline live at:** https://forecast.masxai.com/
> **Bittensor pipeline live at:** https://bt.masxai.com/
> **GitHub:** https://github.com/AteetVatan/masx-forecasting
> **Local path:** `S:\SYNC\programming\MASX-AI`

---

## What MASX-AI Is

MASX-AI is an autonomous, multi-domain strategic forecasting engine. It runs **two independent prediction pipelines** in production, each producing calibrated, research-grade probabilistic forecasts with a full resolution and calibration lifecycle:

1. **Geopolitical Forecasting** — through a Council of 35 Doctrine Agents (live at https://forecast.masxai.com/)
2. **Bittensor Network Health Forecasting** — through real-time subnet anomaly detection across 50+ Bittensor subnets (live at https://bt.masxai.com/)

It is built on a **Clean / Hexagonal Architecture** with strict separation of concerns: `core/domain/` (pure logic, zero I/O), `core/infra/` (adapters), and `pipeline/` (orchestration).

---

## Geopolitical Pipeline (forecast.masxai.com)

### Per-hotspot reasoning loop

1. **Hotspot Scoring** — Composite ranking using Volume (25%), Recency (20%), Diversity (20%), Topic (15%), and lifecycle-aware Velocity ratio (10%).
2. **Doctrine Router** — Selects the 5 most relevant doctrines from 35, using matrix lookup (domain × region) + LLM router agent.
3. **Pre-fetch RAG** — Parallel doctrine retrieval via LlamaIndex VectorStoreIndex with all-MiniLM-L6-v2 embeddings + ms-marco-MiniLM-L-6-v2 cross-encoder reranking.
4. **Council of Doctrines** — Each selected doctrine agent analyzes the hotspot through its unique strategic lens, producing `DoctrineAnalysis` (confidence, direction, key concepts).
5. **Question Generator** — Produces 3 falsifiable forecasting questions per hotspot, aligned to 14/30/90-day resolution bands, with strict interrogative validation + retry.
6. **Forecaster + Advisor** — Pydantic-AI agent with 7 mathematical tools produces grounded `LLMForecast`; Advisor produces entity-level recommendations.
7. **Grounding Validator** — Checks LLM probability against Bayesian tool outputs (±15pp tolerance), validates CI, auto-heals, assigns grounding score.
8. **Persist** — Maps `LLMForecast` → domain `Forecast`, upserts to Supabase.

### 35 Doctrine Agents

Each doctrine has a dedicated LlamaIndex VectorStoreIndex built from its source PDF with enriched metadata (theme, domain, region, use_case).

- **Classical Statecraft:** Art of War (Sun Tzu), Chanakya (Arthasastra), Mahabharata, Panchatantra, Shivaji (Ganimi Kava)
- **Geopolitics & Grand Strategy:** Heartland Theory (Mackinder), Rimland (Spykman), Sea Power (Mahan), Containment, Kennan, Diplomacy (Kissinger), Mearsheimer, RAND, Smart Power, NSS, Clash of Civilizations, Iroquois Great Law of Peace
- **Hybrid & Cognitive Warfare:** Fifth Generation Warfare, Unrestricted Warfare, MindWar, LikeWar, Wag the Dog, Deep State, Cyber War
- **Economics & Systems:** Wealth of Nations, Currency Wars, Confessions of an Economic Hitman, Shock Doctrine, Innovator's Dilemma
- **Civilizational & Environmental:** Collapse (Diamond), Limits to Growth, Silent Spring, Superintelligence, Networks of Power

### 7 Mathematical Forecaster Tools

`calc_bayesian_update`, `calc_laplace_base_rate`, `calc_temporal_projection`, `calc_time_horizon_decay`, `calc_confidence_interval`, `calc_evidence_weight`, `calc_fermi_decompose`.

### 3 Advisor Tools (pre-computed)

`intervention_window`, `cost_of_inaction`, `doctrine_consensus`.

### Cross-Provider Model Routing

LLM workloads split across 2 model groups (Gemini-primary and OpenAI-primary), round-robin per hotspot, with cross-provider fallback on failure. Each provider has its own `AsyncTokenBucketLimiter` at 200 RPM. Hotspots run concurrently with `PIPELINE_HOTSPOT_CONCURRENCY = 6`.

### Distribution Channels

- **Newsletter** — HTML briefing emailed via Resend
- **LinkedIn** — Post draft emailed for manual review
- **Podcast** — AI-generated script → Gemini TTS → MP3 → Supabase Storage
- **Database** — All forecasts persisted to Supabase `forecasts` table

---

## Bittensor Pipeline (bt.masxai.com)

Independent, feature-flagged forecasting domain that monitors **50+ Bittensor subnets** in real-time. Emphasizes subnet flow, emission, and pool-state dynamics, not token price prediction.

### 9 Signal Detectors

| Signal | Trigger | Severity |
|---|---|---|
| `emission_drop` | Emission share declined ≥ 20% | Warning |
| `miner_exodus` | Active miners dropped ≥ 30% | Critical |
| `staking_flight` | Net outflow > 5,000 TAO (7d) | Warning |
| `governance_proposal` | Tempo or immunity period changed | Warning |
| `team_abandonment` | Low emission + declining miners | Critical |
| `competitive_displacement` | Emission rank fell ≥ 5 positions | Warning |
| `dtao_liquidity_drop` | dTAO pool drained ≥ 30% | Critical |
| `network_overview` | Always emitted — daily network summary | Info |
| `rotation` / `sentiment_divergence` | Reserved | — |

### Probability Calibration Stack

1. **Pattern anchoring** — empirical base rates from `bt_patterns`
2. **Multi-shot aggregation** — Shot 1 at temperature=0.0 (deterministic) + N probes at temperature=0.3, aggregated by median
3. **Isotonic recalibration** — `fit_recalibrator()` from resolved history
4. **Polymarket anchoring** — real-time market probability context
5. **Brier feedback loop** — decomposition (reliability + resolution + uncertainty) per calibration run

### Post-Pipeline Lifecycle

- **Resolution Sweep** (`bt_resolver.py`) — resolves matured predictions against historical subnet snapshots
- **Calibration Run** (`bt_calibration_runner.py`) — Brier score decomposition, updates pattern empirical rates, stores to `bt_calibration_runs`

### Data Sources

| Source | Adapter | Data |
|---|---|---|
| **Taostats** | `TaostatsAdapter` | Subnet snapshots, emission history, dTAO pool metrics |
| **CoinGecko** | `CoinGeckoAdapter` | TAO price, volume, market cap, 24h change |
| **Santiment** | `SentimentAdapter` | Social volume, Fear & Greed, sentiment ratio |
| **Polymarket** | `PolymarketAdapter` | Live prediction market probabilities for calibration anchoring |

---

## Tech Stack

| Component | Technology |
|---|---|
| **LLM Framework** | pydantic-ai (agent orchestration, structured output, tool calling) |
| **Primary LLM** | Gemini 2.0 Flash |
| **Secondary LLM** | GPT-4o-mini (cross-provider fallback) |
| **RAG** | LlamaIndex (VectorStoreIndex per doctrine) |
| **Embeddings** | all-MiniLM-L6-v2 (local HuggingFace, 384-dim) |
| **Reranking** | ms-marco-MiniLM-L-6-v2 (local cross-encoder) |
| **Database** | Supabase (Postgres) — hotspots, forecasts, podcasts, newsletters, BT snapshots/signals/predictions |
| **Email** | Resend |
| **TTS** | Gemini TTS + edge-tts |
| **Audio** | pydub + ffmpeg |
| **Validation** | Pydantic v2 |
| **Settings** | pydantic-settings |
| **HTTP** | httpx (async) |
| **Testing** | pytest (31+ test files, AAA pattern) |
| **Linting** | ruff |
| **Deployment** | Docker + Railway |

---

## Domain Models (Geopolitical)

`LLMForecast`, `Forecast`, `DoctrineAnalysis`, `AdvisorOutput`, `HotspotContext`. Key enums: `ForecastStatus` (open / resolved_true / resolved_false / expired / rejected), `EntityType`, `TimeHorizon` (1mo / 3mo / 6mo), `HazardModel` (exponential / weibull), `SignalType`.

## Domain Models (Bittensor)

`SubnetSnapshot`, `SubnetEmissionData`, `BtSignal`, `BtPrediction`, `BtForecastOutput`, `BtPattern`, `BtAdvisorOutput`, `TaoPriceData`, `TaoSentimentData`, `NetworkAnalytics`. Key enums: `BtSignalType`, `BtSignalSeverity` (critical / warning / info), shared `ForecastStatus` with geo.

---

## Why MASX-AI Matters

- **Two live production pipelines** (https://forecast.masxai.com and https://bt.masxai.com) with full resolution + calibration lifecycle.
- **35 doctrine agents** spanning classical statecraft to modern hybrid warfare and decentralized AI economics.
- **Mathematical grounding** — every probability is anchored by Bayesian + temporal + base-rate tools, then validated against ±15pp tolerance.
- **Cross-provider resilience** — round-robin Gemini ↔ OpenAI with independent rate limiters and graceful degradation.
- **End-to-end distribution** — forecast → newsletter, LinkedIn draft, podcast (Gemini TTS), and Supabase persistence.
