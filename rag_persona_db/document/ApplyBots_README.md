# ApplyBots — AI-Powered Job Application Platform

[![GitHub](https://img.shields.io/badge/GitHub-AteetVatan%2FApplyBots-181717?logo=github)](https://github.com/AteetVatan/ApplyBots)

> **An agentic AI-powered automated job application platform** that helps job seekers discover opportunities, generate tailored applications, and submit them efficiently — all while maintaining **100% truthfulness** via Truth-Lock Technology.
>

---

## 📖 Table of Contents

1. [Features](#-features)
2. [Key Principle — Truth-Lock Technology](#-key-principle--truth-lock-technology)
3. [High-Level Architecture](#-high-level-architecture)
4. [AutoGen Multi-Agent System](#-autogen-multi-agent-system)
5. [Technology Stack](#-technology-stack)
6. [Backend Deep Dive](#-backend-deep-dive)
7. [Frontend Deep Dive](#-frontend-deep-dive)
8. [Infrastructure Services](#-infrastructure-services)
9. [Data Flow Diagrams](#-data-flow-diagrams)
10. [Resume Builder & Reactive Resume Integration](#-resume-builder--reactive-resume-integration)
11. [API Endpoints Reference](#-api-endpoints-reference)
12. [Deployment Architecture](#-deployment-architecture)
13. [Security & Compliance](#-security--compliance)
14. [Subscription Plans & Billing](#-subscription-plans--billing)
15. [Quick Start](#-quick-start)
16. [Project Structure](#-project-structure)
17. [Make Commands](#-make-commands)
18. [Environment Variables](#-environment-variables)
19. [Testing](#-testing)
20. [Glossary](#-glossary)
21. [Further Reading](#-further-reading)
22. [License](#-license)

---

## 🌟 Features

### Core Application Features

- **Smart Job Discovery** — Automatically finds and matches jobs from multiple sources (Adzuna, Jooble, TheMuse, StackOverflow, Wellfound) with semantic embedding-based search
- **AI-Powered Match Scoring** — Multi-factor compatibility scoring (Skills 40%, Experience 25%, Location 15%, Salary 10%, Culture 10%) with detailed explanations
- **Automated Applications** — Playwright-based browser automation for Greenhouse and Lever ATS systems with full audit trail and screenshots
- **Human-in-the-Loop** — Review, edit, and approve every AI-generated cover letter, answer, and application before submission
- **Truth-Lock Technology** — All AI-generated content is cross-verified against your actual resume to prevent hallucinations
- **Multi-Agent AI System** — AutoGen-powered specialized agents (Orchestrator, Resume, Match, Apply, QC, Critic) collaborating via GroupChat

### Campaign System (Copilot)

- **Role-Cluster Campaigns** — Create targeted campaigns for similar positions across multiple companies
- **Recommendation Modes** — Choose between keyword-based or learned matching (adapts from your feedback)
- **Negative Keyword Filtering** — Exclude jobs containing specific unwanted terms
- **Daily Limits & Auto-Apply** — Configure daily application caps and toggle auto-apply vs. manual review
- **Campaign Analytics** — Track jobs applied, interviews secured, and offers received per campaign

### Application Tracking (Kanban)

- **Drag-and-Drop Kanban Board** — Visual pipeline with stages: Saved → Applied → Interviewing → Offer → Rejected
- **Application Notes** — Add timestamped notes to any application for tracking
- **Detail Drawer** — Side panel showing full application details, timeline, and action buttons
- **Pipeline Statistics** — Real-time stats bar showing application counts per stage
- **Search & Filter** — Filter applications by stage, company, score, and more

### Resume Builder

- **Visual Resume Editor** — Form-based editor with sections for Contact, Summary, Experience, Education, Skills, and Projects
- **Live Preview** — Real-time preview with 5 professional templates (Professional Modern, Classic Traditional, Tech Minimalist, Two Column, ATS Optimized)
- **AI Assistant Drawer** — AI-powered summary generation, skills suggestions, and ATS scoring
- **ATS Compatibility Scoring** — Score based on keyword optimization, formatting, section completeness, and bullet point structure
- **PDF Export** — Generate PDF resumes using WeasyPrint with template rendering
- **Auto-Save** — 2-second debounced auto-save of drafts to backend
- **Reactive Resume Integration** — Planned migration to Reactive Resume fork with JSON Resume format bidirectional conversion

### Career Tools

- **Mock Interview Roleplay** — AI-conducted mock interviews with configurable role, company, type (behavioral/technical/mixed), experience level, and focus areas. Get per-answer feedback with scoring and improvement suggestions, plus an end-of-session summary with recommendations
- **Offer Negotiation Analyzer** — Analyze job offers against market data with total compensation calculation, market comparison, strengths/concerns assessment, and negotiation room estimation. Get scripted negotiation strategies with configurable risk tolerance
- **Career Path Advisor** — Career assessment based on current role, experience, and skills. Get recommended career paths with learning roadmaps and timeline projections

### Company Intelligence

- **Company Research** — Aggregated company data from multiple sources:
  - **Wikipedia** — Company description, history, and overview
  - **SEC EDGAR** — Financial data from 10-K filings (revenue, employees)
  - **NewsAPI** — Recent news articles with sentiment analysis
  - **Clearbit** — Logo, industry, company size, headquarters, founding year
- **Hiring Signals** — Indicators of active hiring and growth
- **Confidence Scoring** — 0-100 score based on data quality and completeness

### AI Chat Assistant

- **Natural Language Interface** — Ask the AI system anything about jobs, resumes, career advice
- **Streaming Responses** — Real-time streaming of agent responses with agent identification
- **Context-Aware** — Enriched with user context (resume, preferences, history)
- **Multi-Agent Collaboration** — Orchestrator delegates to specialized agents based on query type

### Gamification & Wellness

- **Achievement System** — Unlock achievements (First Apply, Streak 7, Perfect Match, etc.) with point rewards
- **Activity Streaks** — Track daily application streaks with longest streak records
- **Leaderboard** — Compare progress with other users
- **Burnout Detection** — Monitor activity patterns for burnout signals (high activity, rejection streaks, days since positive outcome)
- **Wellness Insights** — Personalized tips and encouragement based on wellness status
- **Burnout Risk Assessment** — Low/Medium/High risk classification with recommended actions

### Alerts & Notifications

- **Dream Job Alerts** — Notifications when match score exceeds configurable threshold (default 90)
- **Application Status Changes** — Updates when application status changes
- **Interview Reminders** — Upcoming interview notifications
- **Achievement Unlocks** — Notifications for new achievements
- **Alert Preferences** — Configurable per-type enable/disable settings
- **Email Notifications** — SendGrid-powered transactional emails

### Analytics

- **Application Funnel** — Visual funnel from applications to interviews to offers
- **Conversion Rates** — Track application-to-interview and interview-to-offer rates
- **Timing Intelligence** — Best day-of-week and hour to apply, days-after-posting analysis
- **Resume A/B Testing** — Compare performance of different resume versions
- **Answer Learning** — Few-shot learning from user edits to AI-generated answers

### Additional Intelligence

- **Skill Gap Analysis** — Identify missing skills for target roles with upskilling recommendations
- **Remote Work Compatibility** — Remote score (0-100), remote type classification (Remote/Hybrid/Onsite), timezone requirement analysis
- **Recruiter Outreach** — AI-generated personalized outreach messages
- **Job Validation** — Negative keyword filtering and scam detection
- **Timing Intelligence** — Analysis of best times to apply based on historical success data

---

## 🔐 Key Principle — Truth-Lock Technology

The platform **NEVER fabricates information**. The Truth-Lock Verifier cross-checks all AI-generated content against source documents:

- **Experience years** — Must match resume
- **Company names** — Must appear in work history
- **Education claims** — Degrees must exist in resume
- **Skill claims** — Skills must be listed in resume
- **Job description references** — Must include phrases from the actual job ad

Any violation is flagged and blocked before submission.

---

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE                                     │
│                    (Browser - Next.js 16 Frontend)                          │
│   ┌─────────┐ ┌───────────┐ ┌────────┐ ┌──────────┐ ┌─────────────────────┐│
│   │  Auth   │ │ Dashboard │ │  Jobs  │ │ Resumes  │ │    Career Tools     ││
│   │ (OAuth) │ │  (Kanban) │ │  List  │ │ Builder  │ │Interview|Nego|Paths ││
│   └─────────┘ └───────────┘ └────────┘ └──────────┘ └─────────────────────┘│
│   ┌─────────┐ ┌───────────┐ ┌────────┐ ┌──────────┐ ┌─────────────────────┐│
│   │Campaigns│ │ AI Chat   │ │ Alerts │ │Gamificat.│ │ Company Intel       ││
│   └─────────┘ └───────────┘ └────────┘ └──────────┘ └─────────────────────┘│
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │ HTTP/REST API
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         API GATEWAY                                          │
│                  (FastAPI Backend + Rate Limiting)                          │
│ ┌────────┐ ┌─────────┐ ┌──────┐ ┌─────────────┐ ┌─────────┐ ┌────────────┐│
│ │ /auth  │ │/resumes │ │/jobs │ │/applications│ │/agents  │ │  /tools    ││
│ └────────┘ └─────────┘ └──────┘ └─────────────┘ └─────────┘ └────────────┘│
│ ┌──────────┐ ┌──────────────┐ ┌────────────┐ ┌───────────┐ ┌────────────┐│
│ │/campaigns│ │/resume-build │ │/gamificat. │ │/wellness  │ │/company    ││
│ └──────────┘ └──────────────┘ └────────────┘ └───────────┘ └────────────┘│
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   AI AGENTS     │   │  BACKGROUND     │   │  DATA LAYER     │
│ (AutoGen Group  │   │  WORKERS        │   │                 │
│     Chat)       │   │  (Celery)       │   │  PostgreSQL     │
│  ┌───────────┐  │   │                 │   │  Redis          │
│  │Orchestrate│  │   │  Job Ingestion  │   │  MinIO (S3)     │
│  │ Resume    │  │   │  App Submitter  │   │  ChromaDB       │
│  │ Match     │  │   │  Alert Generate │   │                 │
│  │ Apply     │  │   │  Status Monitor │   │                 │
│  │ QC/Critic │  │   └─────────────────┘   └─────────────────┘
│  └───────────┘  │           │
└─────────────────┘           ▼
         │            ┌─────────────────┐
         │            │  EXTERNAL APIs  │
         └───────────>│  Together AI    │
                      │  SendGrid       │
                      │  Google/GitHub  │
                      │  Adzuna/Jooble  │
                      │  NewsAPI        │
                      │  SEC EDGAR      │
                      │  Stripe         │
                      └─────────────────┘
```

---

## 🤖 AutoGen Multi-Agent System

### Agent Roles & Models

| Agent | Together AI Model | Cost (In/Out per 1M) | Role |
|-------|-------------------|----------------------|------|
| **Orchestrator** | DeepSeek-R1-0528 | $3.00 / $7.00 | Coordinates all agents, task routing, workflow management |
| **Resume Agent** | Qwen3-235B-A22B | $0.65 / $3.00 | Resume parsing, optimization, ATS tailoring |
| **Job Scraper Agent** | Llama-4-Scout-17B | $0.18 / $0.59 | Job discovery, filtering, extraction |
| **Match Agent** | Llama-4-Maverick-17B | $0.27 / $0.85 | Job-candidate scoring, gap analysis |
| **Apply Agent** | Llama-3.3-70B | $0.88 / $0.88 | Cover letters, screening answers, form filling |
| **Quality Control** | DeepSeek-V3.1 | $0.60 / $1.25 | Review, validation, error prevention |
| **Critic Agent** | Qwen-QwQ-32B | $1.20 / $1.20 | Constructive feedback, improvement suggestions |
| **Coder Agent** | Qwen3-Coder-480B | $2.00 / $2.00 | Code generation for form automation scripts |
| **Embeddings** | BAAI/bge-large-en-v1.5 | $0.02 / — | 1024-dimension text embeddings |

### Agent Communication Flow

```
User Request
     │
     ▼
┌─────────────────┐
│  Orchestrator   │ ◄── Manages conversation and delegates tasks
└────────┬────────┘
         │
    ┌────┴────┬─────────────┬─────────────┐
    ▼         ▼             ▼             ▼
┌───────┐ ┌───────┐   ┌──────────┐  ┌──────────┐
│Resume │ │ Job   │   │  Match   │  │  Apply   │
│ Agent │ │Scraper│   │  Agent   │  │  Agent   │
└───┬───┘ └───┬───┘   └────┬─────┘  └────┬─────┘
    │         │            │             │
    └─────────┴─────┬──────┴─────────────┘
                    ▼
            ┌──────────────┐
            │ Critic Agent │ ◄── Reviews all outputs
            └──────┬───────┘
                   ▼
            ┌──────────────┐
            │   Quality    │
            │   Control    │ ◄── Final validation
            └──────────────┘
                   │
                   ▼
            Final Output
```

### GroupChat Orchestration

Agents collaborate via AutoGen's `GroupChat` with automatic speaker selection (DeepSeek-R1 decides who speaks next). Max 20-25 rounds per conversation. Specialized groups exist for focused tasks (e.g., Resume Optimization group with Resume + Critic + QC agents).

### Agent Tools (Function Calling)

Agents can invoke registered tool functions:
- `parse_resume` — Parse PDF/DOCX/TXT resumes into structured data
- `search_jobs` — Search across multiple job platforms with filters
- `calculate_match_score` — Score resume-job compatibility
- `generate_cover_letter` — Create tailored cover letters (formal/conversational/enthusiastic)
- `submit_application` — Submit via Playwright browser automation
- `browse_webpage` — Navigate and extract data from webpages

---

## 📊 Technology Stack

### Backend Technologies

| Technology | Purpose | Version |
|------------|---------|---------|
| **Python** | Main language | 3.11+ |
| **FastAPI** | Web framework with auto docs | 0.109.0 |
| **SQLAlchemy** | Async ORM with type hints | 2.0.25 |
| **Alembic** | Database migrations | 1.13.1 |
| **PostgreSQL** | Primary relational database | 16 |
| **Redis** | Cache, rate limiting, Celery broker | 7 |
| **Celery** | Distributed background task queue | 5.3.6 |
| **AutoGen** | Multi-agent AI orchestration | 0.2.10 |
| **Playwright** | Browser automation for ATS | 1.41.0 |
| **pdfplumber/pypdfium2** | PDF text extraction | Latest |
| **Tesseract OCR** | OCR for scanned PDFs | Latest |
| **WeasyPrint** | HTML to PDF resume generation | 60.0+ |
| **MinIO** | S3-compatible object storage | Latest |
| **ChromaDB** | Vector database for embeddings | 0.4.22 |
| **Pydantic** | Data validation & settings | 2.6.3 |
| **Together AI** | LLM provider (OpenAI-compatible) | — |
| **SendGrid** | Transactional email | — |
| **Stripe** | Subscription billing | 7.10.0 |
| **structlog** | JSON structured logging | 24.1.0 |
| **tenacity** | Retry logic for external calls | 8.2.3 |

### Frontend Technologies

| Technology | Purpose | Version |
|------------|---------|---------|
| **Next.js** | React framework with App Router | 16.1.6 |
| **React** | Component-based UI library | 18.2 |
| **TypeScript** | Type-safe JavaScript | 5.3.3 |
| **TanStack Query** | Server state & data fetching | 5.17.9 |
| **Tailwind CSS** | Utility-first styling | 3.4.1 |
| **Zod** | Runtime type validation | 3.22.4 |
| **Zustand** | Lightweight state management | 4.5.0 |
| **Immer** | Immutable state updates | 11.1.3 |
| **Radix UI** | Accessible component primitives | Various |
| **Framer Motion** | Smooth UI animations | 10.18.0 |
| **dnd-kit** | Drag-and-drop (Kanban board) | 6.3.1 |
| **react-resizable-panels** | Split pane layouts | 4.5.6 |
| **Vitest** | Fast unit testing | 4.0.18 |
| **Playwright** | E2E browser automation tests | 1.41.0 |

### Internationalization

- Configuration in `i18n/config.ts`
- Locales: English (`en.ts`), German (`de.ts`)
- Translation utilities with interpolation support

---

## 🔧 Backend Deep Dive

### Hexagonal Architecture (Ports & Adapters)

The backend follows a clean hexagonal architecture with three layers:

**Core Layer** (`app/core/`) — Pure business logic, no external dependencies:
- `domain/` — Dataclass entities: User, Job, Resume, Application, Campaign, Alert, Gamification, Wellness, CompanyIntelligence
- `ports/` — Protocol interfaces: UserRepository, LLMClient, FileStorage, VectorStore, ATSAdapter
- `services/` — Business logic: MatchService, TruthLockVerifier, PlanGating, AIContentService, ATSScoringService, CareerTools (Interview/Negotiation/Career), GamificationService, WellnessService, SkillGapAnalysis, CoverLetterGenerator, QuestionAnswerer, RecruiterOutreach, Analytics, ABTesting, AnswerLearning, JobFeedback, JobPreference, JobValidator, RecommendationMode, TimingIntel, RemoteIntel
- `exceptions.py` — Domain exceptions hierarchy (DomainError → AuthenticationError, AuthorizationError, ResourceError, ApplicationError, AutomationError, ExternalServiceError)

**Infrastructure Layer** (`app/infra/`) — All IO operations:
- `db/` — SQLAlchemy models, session management, repository implementations
- `auth/` — JWT management, bcrypt password hashing, Google/GitHub OAuth
- `storage/` — S3/MinIO file storage
- `llm/` — Together AI client (OpenAI-compatible API)
- `vector/` — ChromaDB client
- `ats_adapters/` — Greenhouse and Lever automation adapters
- `scrapers/` — Adzuna, Jooble, TheMuse, StackOverflow, Wellfound adapters
- `company_intel/` — Wikipedia, SEC EDGAR, NewsAPI, Clearbit clients
- `notifications/` — SendGrid email service
- `services/` — Resume upload/parsing, application management, Stripe billing, PDF generation

**API Layer** (`app/api/`) — REST endpoints with FastAPI:
- Versioned under `/api/v1/`
- Dependency injection via `deps.py`
- Middleware: Redis-based rate limiting, Prometheus metrics

### Domain Exception Hierarchy

```
DomainError
├── AuthenticationError
│   ├── InvalidCredentialsError
│   ├── TokenExpiredError
│   ├── TokenInvalidError
│   └── SessionRevokedError
├── AuthorizationError
│   ├── PlanLimitExceededError
│   └── InsufficientPermissionsError
├── ResourceNotFoundError
├── ResourceAlreadyExistsError
├── ValidationError
├── ApplicationError
│   ├── TruthLockViolationError
│   ├── QCRejectionError
│   └── LowMatchScoreError
├── AutomationError
│   ├── CaptchaDetectedError
│   ├── MFARequiredError
│   └── FormFieldNotFoundError
└── ExternalServiceError
```

### Background Workers (Celery)

| Worker | Schedule | Description |
|--------|----------|-------------|
| **Job Ingestion** | Every 4 hours | Scrape jobs from APIs, deduplicate, extract requirements with AI, generate embeddings, store in ChromaDB + PostgreSQL |
| **Application Submitter** | On-demand | Launch Playwright browser, detect ATS type, fill form, capture screenshots, handle errors (CAPTCHA → manual), store audit trail |
| **Alert Generator** | On-demand | Check for dream job matches, status changes, interview reminders, achievement unlocks |
| **Status Monitor** | Periodic | Track application status changes |
| **Daily Usage Reset** | Every 24 hours | Reset daily application counters |

Windows compatibility: Celery auto-detects Windows and uses `solo` pool.

---

## 🎨 Frontend Deep Dive

### Page Structure (Next.js App Router)

| Route | Page |
|-------|------|
| `/` | Landing page |
| `/login` | Login with email/password + Google/GitHub OAuth |
| `/signup` | Registration with OAuth |
| `/dashboard` | Main dashboard overview |
| `/dashboard/jobs` | Job listings with match scores |
| `/dashboard/jobs/[id]/expert-apply` | Expert apply for specific job |
| `/dashboard/applications` | Kanban board (drag-and-drop) |
| `/dashboard/resumes` | Resume list |
| `/dashboard/resumes/builder` | Visual resume builder |
| `/dashboard/chat` | AI chat assistant |
| `/dashboard/tools` | Career tools hub |
| `/dashboard/tools/interview` | Mock interview roleplay |
| `/dashboard/tools/negotiation` | Offer analysis & negotiation |
| `/dashboard/tools/career` | Career path advisor |
| `/dashboard/profile` | User profile & preferences |
| `/dashboard/billing` | Subscription management |

### Key Components

- **KanbanBoard** — dnd-kit powered drag-and-drop with StageColumn, ApplicationCard, DetailDrawer, DrawerNotes, DrawerTimeline, DrawerFooter
- **Resume Builder** — EditorPanel, PreviewPanel, TemplateSelector, AIAssistantDrawer (SummaryMode, SkillsMode, ATSMode), section editors (Contact, Summary, Experience, Education, Skills, Projects)
- **5 Resume Templates** — ProfessionalModern, ClassicTraditional, TechMinimalist, TwoColumn, ATSOptimized

### State Management

- **Zustand + Immer** — Resume builder store with immutable state updates
- **TanStack Query** — Server state management for API data fetching/caching
- **AuthProvider** — React context for authentication state
- **Typed API Client** (`lib/api.ts`) — Comprehensive Zod schema validation for all API responses

---

## 💾 Infrastructure Services

### PostgreSQL — Database Tables

| Table | Purpose |
|-------|---------|
| `users` | User accounts with roles |
| `profiles` | Preferences, contact info, negative keywords |
| `resumes` | Uploaded resumes with parsed data & embeddings |
| `resume_drafts` | Resume builder drafts with autosave (JSON) |
| `jobs` | Job listings with embeddings & remote analysis |
| `applications` | Application records with Kanban stages & notes |
| `application_notes` | Notes on applications |
| `campaigns` | Job search campaigns (copilots) |
| `campaign_jobs` | Campaign-job associations with scores |
| `subscriptions` | Plan & billing info |
| `refresh_sessions` | JWT refresh tokens |
| `agent_sessions` | AI chat history |
| `audit_logs` | Automation action logs |
| `alerts` | User notifications |
| `alert_preferences` | Alert settings per user |
| `user_streaks` | Activity streak tracking |
| `user_achievements` | Earned achievements |
| `answer_edits` | User edits for few-shot learning |

### Redis
- Session cache, rate limiting (sliding window), Celery broker & backend

### MinIO (S3-compatible)
- Resume PDFs/DOCX, automation screenshots, generated documents

### ChromaDB (Vector Database)

| Collection | Purpose |
|------------|---------|
| `resumes` | Resume embeddings for semantic matching |
| `jobs` | Job description embeddings |
| `agent_memory` | Agent conversation memory for context |

**Embedding Model:** BAAI/bge-large-en-v1.5 (1024 dimensions) via Together AI

---

## 🔄 Data Flow Diagrams

### Job Application Flow with Kanban

```
User           Frontend        Backend         Celery Worker      ATS Site
 │                │               │                  │               │
 │ Click "Apply"  │               │                  │               │
 │───────────────>│               │                  │               │
 │                │ POST /applications               │               │
 │                │──────────────>│                  │               │
 │                │               │ Calculate match  │               │
 │                │               │ Generate cover   │               │
 │                │               │ Truth-lock verify│               │
 │                │ Application   │ Stage: SAVED     │               │
 │                │<─────created──│                  │               │
 │ Review & Edit  │               │                  │               │
 │───────────────>│               │                  │               │
 │                │ PATCH /stage  │                  │               │
 │                │──────────────>│                  │               │
 │                │               │ Stage: APPLIED   │               │
 │                │ POST /approve │                  │               │
 │                │──────────────>│                  │               │
 │                │               │ Queue submission │               │
 │                │               │─────────────────>│               │
 │                │               │                  │ Launch browser│
 │                │               │                  │──────────────>│
 │                │               │                  │ Fill form     │
 │                │               │                  │ Screenshot    │
 │                │               │                  │<──────────────│
 │                │               │ Update stage     │               │
 │ (Kanban moves) │ Stage: INTERVIEW               │               │
 │<───────────────│<──────────────│                  │               │
```

### Interview Roleplay Flow

```
User           Frontend        Backend (Tools API)      LLM (Together AI)
 │                │                    │                       │
 │ Start Interview│                    │                       │
 │───────────────>│                    │                       │
 │                │ POST /tools/interview/start               │
 │                │───────────────────>│                       │
 │                │                    │ Generate questions    │
 │                │                    │──────────────────────>│
 │                │                    │<──────────────────────│
 │                │ session_id + first_question               │
 │                │<───────────────────│                       │
 │ Answer Q1      │                    │                       │
 │───────────────>│                    │                       │
 │                │ POST /tools/interview/respond             │
 │                │───────────────────>│                       │
 │                │                    │ Evaluate answer       │
 │                │                    │──────────────────────>│
 │                │                    │<──────────────────────│
 │ Feedback +     │                    │                       │
 │ next question  │<───────────────────│                       │
 │   ...repeat... │                    │                       │
 │ End Interview  │                    │                       │
 │───────────────>│                    │                       │
 │                │ POST /tools/interview/end                 │
 │                │───────────────────>│                       │
 │ Summary with   │                    │                       │
 │ recommendations│<───────────────────│                       │
```

### Resume Builder Data Flow

```
┌────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │     Reactive Resume (Forked & Integrated)            │  │
│  │  ┌──────────────┐  ┌──────────────┐                 │  │
│  │  │ Zustand Store│  │ UI Components│                 │  │
│  │  └──────┬───────┘  └──────┬───────┘                 │  │
│  └─────────┼──────────────────┼─────────────────────────┘  │
│            │                  │                              │
│  ┌─────────▼──────────────────▼─────────┐                  │
│  │     Resume Adapter Utilities          │                  │
│  │  (JSON Resume ↔ ResumeContent)       │                  │
│  └─────────┬──────────────────┬─────────┘                  │
│            │                  │                              │
│  ┌─────────▼──────────────────▼─────────┐                  │
│  │     Integration Hooks                │                  │
│  │  (Sync, ATS Scoring)                 │                  │
│  └─────────────────────────────────────┘                  │
└────────────────────────────┬───────────────────────────────┘
                             ▼
┌────────────────────────────────────────────────────────────┐
│              Backend (FastAPI - Unchanged)                  │
│  /api/v1/resume-builder/drafts (CRUD)                      │
│  /api/v1/resume-builder/ats-score                           │
│  ATSScoringService + PostgreSQL (JSON Storage)             │
└────────────────────────────────────────────────────────────┘
```

---

## 📚 Resume Builder & Reactive Resume Integration

The resume builder is being migrated to integrate a **Reactive Resume** fork:

- **Resume Adapter Utilities** (`resume-adapter.ts`) — Bidirectional conversion between JSON Resume format (Reactive Resume) and ResumeContent format (our frontend/backend)
- **Sync Hook** (`useReactiveResumeSync`) — Auto-loads drafts, converts formats, auto-saves with 2s debounce
- **ATS Hook** (`useReactiveResumeATSScore`) — Fetches data from Reactive Resume store, converts, scores
- **Wrapper Component** (`ReactiveResumeBuilder`) — Data synchronization with loading/saving status
- **Browserless** container for PDF/screenshot generation (port 4000)

---

## 📡 API Endpoints Reference

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/signup` | Create new account |
| POST | `/auth/login` | Login, get JWT tokens |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/logout` | Invalidate session |
| GET | `/auth/google-login` | Initiate Google OAuth |
| GET | `/auth/google-callback` | Handle Google OAuth callback |
| GET | `/auth/github-login` | Initiate GitHub OAuth |
| GET | `/auth/github-callback` | Handle GitHub OAuth callback |

### Profile & Resumes
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/PUT | `/profile` | Get/update user profile |
| GET/POST | `/resumes` | List / upload resumes |
| GET/DELETE | `/resumes/{id}` | Get / delete resume |
| POST | `/resumes/{id}/set-primary` | Set as primary resume |

### Resume Builder
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/resume-builder/drafts` | List / create drafts |
| GET/PUT/DELETE | `/resume-builder/drafts/{id}` | Manage draft |
| POST | `/resume-builder/drafts/{id}/export` | Export to PDF |
| POST | `/resume-builder/ai/summary` | AI summary generation |
| POST | `/resume-builder/ai/skills` | AI skills suggestions |
| POST | `/resume-builder/ai/ats-score` | Calculate ATS score |

### Jobs & Applications
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/jobs` | List matching jobs |
| GET | `/jobs/{id}` | Get job details |
| POST | `/jobs/refresh` | Trigger job ingestion |
| GET/POST | `/applications` | List / create applications |
| GET | `/applications/grouped` | Applications by Kanban stage |
| PATCH | `/applications/{id}/stage` | Update Kanban stage |
| POST | `/applications/{id}/notes` | Add note to application |
| POST | `/applications/{id}/approve` | Approve for submission |

### Campaigns
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/campaigns` | List / create campaigns |
| GET/PUT/DELETE | `/campaigns/{id}` | Manage campaign |
| GET | `/campaigns/{id}/jobs` | Campaign's matched jobs |

### AI & Tools
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/agents/chat` | Send message to AI |
| POST | `/agents/chat/stream` | Stream AI response |
| POST | `/tools/interview/start` | Start mock interview |
| POST | `/tools/interview/respond` | Submit answer, get feedback |
| POST | `/tools/interview/end` | End session, get summary |
| POST | `/tools/negotiation/analyze` | Analyze job offer |
| POST | `/tools/negotiation/strategy` | Get negotiation scripts |
| POST | `/tools/career/assess` | Assess career position |
| POST | `/tools/career/paths` | Get career path recommendations |

### Engagement & Intelligence
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/alerts` | List user alerts |
| POST | `/alerts/{id}/read` | Mark alert as read |
| GET/PUT | `/alerts/preferences` | Manage alert preferences |
| GET | `/gamification/progress` | Achievements & streak |
| GET | `/gamification/leaderboard` | Leaderboard |
| GET | `/analytics/dashboard` | Analytics data |
| GET | `/wellness/status` | Wellness status |
| GET | `/wellness/insight` | Wellness tip |
| GET | `/company/{name}/intelligence` | Company research |
| GET | `/billing/usage` | Usage stats |
| POST | `/billing/checkout` | Start Stripe checkout |

---

## ☁️ Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CLOUD INFRASTRUCTURE                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Kubernetes Cluster                                │    │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐       │    │
│  │  │ Frontend  │  │  FastAPI  │  │  Celery   │  │  Agent    │       │    │
│  │  │  (Next)   │  │  Backend  │  │  Workers  │  │  Service  │       │    │
│  │  │  3 pods   │  │  5 pods   │  │  3 pods   │  │  2 pods   │       │    │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘       │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Managed Services                                  │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │    │
│  │  │PostgreSQL│  │  Redis   │  │ ChromaDB │  │   S3     │           │    │
│  │  │  (RDS)   │  │(Upstash) │  │ (Vector) │  │ (Files)  │           │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    External APIs                                     │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │    │
│  │  │Together  │  │  Stripe  │  │ SendGrid │  │  Twilio  │           │    │
│  │  │   AI     │  │(Billing) │  │ (Email)  │  │  (SMS)   │           │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │    │
│  └────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Service Ports (Local Development)

| Service | Port | UI/Console |
|---------|------|------------|
| Frontend | 3000 | http://localhost:3000 |
| Backend API | 8080 | http://localhost:8080/docs |
| Reactive Resume | 3002 | http://localhost:3002 |
| PostgreSQL | 5432 | — |
| Redis | 6379 | — |
| MinIO API | 9000 | — |
| MinIO Console | 9001 | http://localhost:9001 |
| Browserless | 4000 | — |
| ChromaDB | 8000 | — |
| Prometheus | 9090 | http://localhost:9090 |
| Grafana | 3001 | http://localhost:3001 |

---

## 🔒 Security & Compliance

### Non-Negotiable Rules

1. **No CAPTCHA Bypass** — Automation aborts and flags for manual intervention
2. **No ToS Violations** — Only safe ATS platforms (Greenhouse, Lever)
3. **Truth-Lock Enforcement** — All AI content verified against resume
4. **Audit Everything** — Complete logs + screenshots for every automation step
5. **No Hardcoded Secrets** — All credentials via environment variables

### Authentication Security

- **Passwords** — bcrypt with cost factor
- **Access Tokens** — JWT, 30-minute expiry
- **Refresh Tokens** — 7-day expiry with session tracking and revocation
- **OAuth** — Google and GitHub via authorization code flow with PKCE
- **Sensitive Config** — Pydantic `SecretStr` (never logged or exposed)

### Rate Limiting (Redis Sliding Window)

| Plan | Requests/Minute |
|------|----------------|
| Free | 100 |
| Premium | 500 |
| Elite | 2000 |

Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

### Data Handling

- GDPR-aligned data retention with purge on account deletion/inactivity
- User data export/delete capabilities
- AES-256 encrypted storage for sensitive information
- No PII in logs
- Platform anti-ban: random delays, human-like speeds, rate limiting

### Feature Flags

```
FEATURE_COMPANY_INTEL=true
FEATURE_GAMIFICATION=true
FEATURE_WELLNESS=true
FEATURE_ADVANCED_ANALYTICS=true
```

---

## 💳 Subscription Plans & Billing

| Feature | Free | Premium | Elite |
|---------|------|---------|-------|
| Daily Applications | 5 | 20 | 50 |
| Copilots (Campaigns) | — | 1 | 3 |
| Rate Limit | 100/min | 500/min | 2000/min |

- Payments via **Stripe** (PCI-compliant, no card data stored)
- Webhook-driven status updates
- Monthly billing with Stripe Checkout integration

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose v2+
- Node.js 20+
- Python 3.11+
- pnpm v10.28+ (for Reactive Resume)

### 1. Clone and Configure

```bash
git clone https://github.com/AteetVatan/ApplyBots.git
cd ApplyBots
cp env.example .env
# Edit .env — at minimum set JWT_SECRET_KEY and TOGETHER_API_KEY
# Generate JWT secret: python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Start Development Environment

```bash
# Start all services with Docker Compose
make dev

# Or start individually:
make dev-up          # Infrastructure services (PostgreSQL, Redis, MinIO, ChromaDB)
make backend         # FastAPI server (separate terminal)
make frontend        # Next.js dev server (separate terminal)
make worker          # Celery worker (separate terminal)
```

### 3. Run Database Migrations

```bash
make migrate
# Optional: seed sample jobs
python scripts/seed_jobs.py
```

### 4. Access the Application

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8080/docs
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)

---

## 📁 Project Structure

```
applybots/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entry point
│   │   ├── config.py            # Pydantic settings
│   │   ├── core/                # 🏛️ Business Logic (Pure Python, No IO)
│   │   │   ├── domain/          # Dataclass entities (User, Job, Resume, Application, Campaign, Alert, Gamification, Wellness, CompanyIntel)
│   │   │   ├── ports/           # Protocol interfaces (Repository, LLM, Storage, Vector, ATS)
│   │   │   ├── services/        # 20+ business services (Matcher, TruthLock, CareerTools, Gamification, Wellness, Analytics, etc.)
│   │   │   └── exceptions.py    # Domain exception hierarchy
│   │   ├── infra/               # 🔌 Infrastructure (IO Operations)
│   │   │   ├── db/              # SQLAlchemy models, session, 11+ repositories
│   │   │   ├── auth/            # JWT, bcrypt, Google/GitHub OAuth
│   │   │   ├── storage/         # S3/MinIO file storage
│   │   │   ├── llm/             # Together AI client
│   │   │   ├── vector/          # ChromaDB client
│   │   │   ├── ats_adapters/    # Greenhouse, Lever automation
│   │   │   ├── scrapers/        # Adzuna, Jooble, TheMuse, StackOverflow, Wellfound
│   │   │   ├── company_intel/   # Wikipedia, SEC EDGAR, NewsAPI, Clearbit
│   │   │   ├── notifications/   # SendGrid email
│   │   │   └── services/        # Resume, Application, Billing, PDF services
│   │   ├── api/                 # 🌐 REST API Layer
│   │   │   ├── v1/              # 15+ endpoint routers
│   │   │   ├── deps.py          # Dependency injection
│   │   │   └── middleware/      # Rate limiting, Prometheus metrics
│   │   ├── agents/              # 🤖 AutoGen multi-agent system
│   │   │   ├── config.py        # LLM model configurations
│   │   │   ├── prompts.py       # System prompts per agent
│   │   │   ├── tools.py         # Agent tool functions
│   │   │   └── workflows.py     # GroupChat orchestration
│   │   ├── workers/             # ⚙️ Celery background tasks
│   │   │   ├── celery_app.py    # Configuration + beat schedule
│   │   │   ├── job_ingestion.py # Multi-source job scraping
│   │   │   ├── application_submitter.py # Playwright form automation
│   │   │   ├── status_monitor.py
│   │   │   └── alert_generator.py
│   │   └── schemas/             # 📋 Pydantic request/response models
│   ├── migrations/              # Alembic database migrations
│   └── tests/                   # unit/, integration/, e2e/
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js App Router (auth, dashboard, tools)
│   │   ├── components/          # React components (Kanban, Resume Builder)
│   │   ├── hooks/               # useJobs, useApplications
│   │   ├── i18n/                # Internationalization (en, de)
│   │   ├── lib/                 # Typed API client + utilities
│   │   ├── providers/           # Auth + combined providers
│   │   └── stores/              # Zustand (resume builder)
│   └── __tests__/               # Frontend tests
├── reactive-resume/             # Reactive Resume fork (for integration)
├── docker/                      # Docker Compose configuration
├── docs/                        # Design documents
│   ├── ARCHITECTURE_DEEP_DIVE.md
│   ├── DESIGN_DOCUMENT.md
│   ├── SETUP_GUIDE.md
│   ├── Reaserch.md
│   ├── REACTIVE_RESUME_MIGRATION.md
│   └── REACTIVE_RESUME_MIGRATION_PLAN.md
├── scripts/                     # Utility scripts (seed_jobs.py)
├── Makefile                     # Development commands
├── env.example                  # Environment variable template
└── pyrightconfig.json           # Python type checking config
```

---

## ⌨️ Make Commands

```bash
make help              # Show all available commands
make dev               # Start full development environment
make dev-up            # Start Docker infrastructure services
make dev-down          # Stop Docker services
make dev-logs          # View Docker logs
make dev-rebuild       # Rebuild and restart services
make backend           # Run backend locally
make frontend          # Run frontend locally
make worker            # Run Celery worker (auto-detects Windows)
make worker-beat       # Run Celery beat scheduler
make worker-windows    # Run Celery worker with explicit solo pool
make migrate           # Run database migrations
make migrate-new       # Create new migration (MSG="description")
make migrate-down      # Rollback last migration
make db-shell          # Open PostgreSQL shell
make test              # Run all backend tests
make test-unit         # Run unit tests only
make test-integration  # Run integration tests only
make test-cov          # Run tests with coverage report
make test-frontend     # Run frontend tests
make test-e2e          # Run E2E Playwright tests
make lint              # Run ruff + mypy + eslint
make format            # Format with ruff
make typecheck         # Run mypy + TypeScript checks
make install           # Install all dependencies
make install-backend   # Install backend dependencies only
make install-frontend  # Install frontend dependencies only
make build             # Build production Docker images
make clean             # Clean generated files
make seed-jobs         # Seed database with sample jobs
make shell             # Open Python shell with app context
```

---

## 🔑 Environment Variables

See `env.example` for all variables. Key categories:

| Category | Variables | Required |
|----------|-----------|----------|
| **App** | `APP_NAME`, `APP_ENV`, `DEBUG` | ✅ |
| **Database** | `DATABASE_URL` | ✅ |
| **Redis** | `REDIS_URL` | ✅ |
| **Auth** | `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` | ✅ |
| **Together AI** | `TOGETHER_API_KEY`, `TOGETHER_API_BASE` | ✅ |
| **Storage** | `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET` | ✅ |
| **ChromaDB** | `CHROMA_HOST`, `CHROMA_PORT` | ⚙️ |
| **Stripe** | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID_*` | 💳 |
| **OAuth** | `GOOGLE_CLIENT_ID/SECRET`, `GITHUB_CLIENT_ID/SECRET`, `*_REDIRECT_URI` | ⚙️ |
| **Email** | `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL` | ⚙️ |
| **Job APIs** | `ADZUNA_APP_ID/KEY`, `JOOBLE_API_KEY`, `THEMUSE_API_KEY` | ⚙️ |
| **Rate Limits** | `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS` | ⚙️ |
| **Plan Limits** | `DAILY_APPLY_LIMIT_FREE/PREMIUM/ELITE` | ⚙️ |
| **Features** | `FEATURE_COMPANY_INTEL/GAMIFICATION/WELLNESS/ADVANCED_ANALYTICS` | ⚙️ |
| **Alerts** | `ALERT_DREAM_JOB_DEFAULT_THRESHOLD` | ⚙️ |
| **Frontend** | `NEXT_PUBLIC_API_URL` | ✅ |

✅ = Required for basic operation, 💳 = Required for payments, ⚙️ = Optional

---

## 🧪 Testing

```bash
# Backend
make test              # All backend tests
make test-unit         # Unit tests only
make test-integration  # Integration tests
make test-cov          # Tests with coverage report

# Frontend
make test-frontend     # Vitest unit tests
make test-e2e          # Playwright E2E tests

# Code Quality
make lint              # ruff + mypy + eslint
make format            # Auto-format with ruff
make typecheck         # Type checking (mypy + tsc)
```

---

## 📖 Glossary

| Term | Definition |
|------|------------|
| **ATS** | Applicant Tracking System — software companies use to manage applications (Greenhouse, Lever) |
| **AutoGen** | Microsoft's framework for building multi-agent AI systems |
| **Celery** | Distributed task queue for Python background jobs |
| **ChromaDB** | Vector database for storing and searching embeddings |
| **dnd-kit** | React drag-and-drop library for Kanban board |
| **Embedding** | Vector representation of text for semantic similarity search |
| **GroupChat** | AutoGen feature for coordinating multiple AI agents |
| **Immer** | Library for immutable state updates in JavaScript |
| **JWT** | JSON Web Token for secure authentication |
| **Kanban** | Visual board with columns representing application stages |
| **LLM** | Large Language Model (DeepSeek, Llama, Qwen) |
| **MinIO** | S3-compatible object storage for files |
| **OAuth** | Protocol for secure delegated access (Google, GitHub) |
| **Port** | Interface defining what the core layer needs (Python Protocol) |
| **Truth-Lock** | System ensuring AI doesn't fabricate information |
| **Vector Search** | Finding similar documents using embedding similarity |
| **WeasyPrint** | Python library for HTML to PDF conversion |
| **Zod** | TypeScript library for runtime type validation |
| **Zustand** | Lightweight state management for React |

---

## 📚 Further Reading

- [Architecture Deep Dive](docs/ARCHITECTURE_DEEP_DIVE.md) — Complete module-by-module technical breakdown
- [Design Document](docs/DESIGN_DOCUMENT.md) — Original system design specifications
- [Setup Guide](docs/SETUP_GUIDE.md) — Detailed installation and debugging instructions
- [Research](docs/Reaserch.md) — Competitor analysis and product strategy
- [Reactive Resume Migration](docs/REACTIVE_RESUME_MIGRATION.md) — Resume builder integration plan
- [Reactive Resume Migration Plan](docs/REACTIVE_RESUME_MIGRATION_PLAN.md) — Detailed migration steps

---

## 📄 License

[MIT License](LICENSE)

---

Built with ❤️ for job seekers everywhere.
