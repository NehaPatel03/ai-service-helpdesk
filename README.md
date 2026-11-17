# DigiPlus AI-Powered Service Desk 🤖🎫

[![Next.js](https://img.shields.io/badge/Next.js-16.0-black?style=flat&logo=next.js)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19.0-blue?style=flat&logo=react)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18.7-336791?style=flat&logo=postgresql)](https://www.postgresql.org/)
[![pgvector](https://img.shields.io/badge/pgvector-0.8.7-336791?style=flat)](https://github.com/pgvector/pgvector)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-3.5_Flash_Lite-4285F4?style=flat&logo=google)](https://ai.google.dev/)
[![Tests](https://img.shields.io/badge/Tests-35%2F35_Passing-brightgreen?style=flat)](file:///d:/ai-service-desk/digiplus-ai-service-desk/ai-service/tests)
[![TypeScript](https://img.shields.io/badge/TypeScript-Strict_Mode-blue?style=flat&logo=typescript)](https://www.typescriptlang.org/)

**DigiPlus AI-Powered Service Desk** is a full-stack, enterprise-grade IT Service Management (ITSM) and automated incident remediation platform. Engineered for IT Support Engineers, SREs, and Helpdesk teams, DigiPlus streamlines the entire incident resolution lifecycle—from natural language ticket ingestion and automated triage to AI-powered root-cause diagnosis, contextual runbook retrieval via **Hybrid RAG**, and real-time interactive incident chat.

Powered by a modern full-stack architecture featuring **Next.js 16 (App Router, React 19)**, a high-performance **FastAPI AI Microservice**, **Neon Serverless PostgreSQL with `pgvector`**, and **Google Gemini (Generative AI & Dense Embeddings)**.

---

## 📑 Table of Contents
- [Executive Overview & Purpose](#-executive-overview--purpose)
- [Comprehensive Feature Suite](#-comprehensive-feature-suite)
  - [1. Executive Analytics & Incident Dashboard](#1-executive-analytics--incident-dashboard)
  - [2. End-to-End Ticket Lifecycle Management](#2-end-to-end-ticket-lifecycle-management)
  - [3. AI-Powered Automated Root Cause Diagnosis](#3-ai-powered-automated-root-cause-diagnosis)
  - [4. Interactive Incident Chat Assistant (AI Copilot)](#4-interactive-incident-chat-assistant-ai-copilot)
  - [5. Historical Similar Incident Detection](#5-historical-similar-incident-detection)
  - [6. Technical Knowledge Base & Runbook Repository](#6-technical-knowledge-base--runbook-repository)
  - [7. Production Hybrid Retrieval Engine (Hybrid RAG)](#7-production-hybrid-retrieval-engine-hybrid-rag)
  - [8. Synthetic Dataset Benchmarking & Bulk Ingestion](#8-synthetic-dataset-benchmarking--bulk-ingestion)
  - [9. High Availability, Fault Tolerance & DNS Resilience](#9-high-availability-fault-tolerance--dns-resilience)
- [System Architecture](#-system-architecture)
- [Project Directory Layout](#-project-directory-layout)
- [End-to-End User Workflows](#-end-to-end-user-workflows)
- [Database Schema & Data Models](#-database-schema--data-models)
- [API Endpoints Reference](#-api-endpoints-reference)
- [Environment Configuration](#-environment-configuration)
- [Step-by-Step Setup & Execution](#-step-by-step-setup--execution)
- [Automated Testing & Quality Verification](#-automated-testing--quality-verification)
- [Implementation Progress (Phases 0–2)](#-implementation-progress-phases-02)
- [Upcoming Roadmap (Phases 3 & 4)](#-upcoming-roadmap-phases-3--4)
- [Security & Best Practices](#-security--best-practices)

---

## 🎯 Executive Overview & Purpose

Modern IT operations face high ticket volumes, fragmented documentation, and prolonged Mean Time to Resolution (MTTR). Support engineers often spend critical minutes manually categorizing tickets, searching through stale documentation, or re-solving problems that were already resolved in prior incidents.

**DigiPlus AI Service Desk** solves this by uniting automated triage, dense semantic search, and generative AI:
- **Reduces MTTR:** Generates instant root-cause diagnostics and step-by-step remediation checklists within seconds of ticket submission.
- **Eliminates Hallucinations via Hybrid RAG:** Grounds LLM solutions in verified, organization-specific technical runbooks using dense vector search (`pgvector`), sparse keyword search (`tsvector`), Reciprocal Rank Fusion (RRF), and neural reranking.
- **Prevents Duplicate Effort:** Matches incoming incidents against historical resolved tickets with similarity percentages, allowing engineers to reuse proven resolutions immediately.
- **Empowers Support Engineers:** Provides an in-context conversational AI assistant on every ticket for interactive troubleshooting, command explanations, and log analysis.
- **Ensures Zero Downtime:** Features dual-database compatibility (Neon PostgreSQL primary + SQLite backup) and automatic heuristic fallback layers if external AI services or networks encounter transient outages.

---

## 🚀 Comprehensive Feature Suite

### 1. Executive Analytics & Incident Dashboard
- **Real-Time KPI Cards:** Displays critical metrics including Total Incidents, Open Incidents, In Progress Incidents, and Resolved/Closed counts with real-time percentage resolution rates.
- **Visual Distribution Breakdowns:**
  - **Priority Breakdown:** Instant visual distribution across `Urgent` (P1), `High` (P2), `Medium` (P3), and `Low` (P4) severity tiers.
  - **Category Breakdown:** Real-time distribution across all 8 technical categories (`Network`, `Software`, `Hardware`, `Access & Security`, `Email & Communication`, `Cloud & Infrastructure`, `Billing & Accounts`, `Database`).
- **Recent Incident Activity Stream:** Real-time chronological feed of newly reported issues with interactive status badges, priority tags, and direct one-click navigation to ticket inspection pages.
- **Quick Action Bar:** Instant access to Create Ticket modal, Knowledge Base explorer, and Bulk Dataset Import tool.

### 2. End-to-End Ticket Lifecycle Management
- **Structured Incident Creation:** Clean modal interface accepting natural language title and description, department, affected service, initial priority, and category.
- **Full-Text Ticket Filtering & Search (`/tickets`):**
  - Search by ticket ID, title keywords, or issue description.
  - Filter simultaneously by Status (`Open`, `In Progress`, `Resolved`, `Closed`), Priority, and Category.
  - Sort by latest activity or creation date.
- **Dedicated Incident Workspace (`/tickets/[id]`):**
  - Edit ticket status, adjust priority dynamically as severity escalates, or re-categorize based on technical findings.
  - Record official resolution notes with audit timestamps.
  - View full creation and last-modified metadata.

### 3. AI-Powered Automated Root Cause Diagnosis
- **One-Click AI Analysis:** Powered by Google Gemini (`gemini-3.5-flash-lite`) via the dedicated FastAPI microservice.
- **Structured Pydantic Diagnostics:**
  - **Executive Summary:** High-level non-technical summary of the disruption.
  - **Root Cause Hypothesis:** Technical deduction identifying the exact underlying failure mechanism (e.g., connection pool exhaustion, expired certificates, stale DNS cache).
  - **Actionable Remediation Steps:** Step-by-step terminal commands, configuration changes, or verification procedures.
  - **One-Click Copy:** Instant clipboard export for support engineers to execute commands or send instructions directly to end-users.
  - **Grounded Runbook Citations:** Displays matching organization runbooks cited by the model to validate recommendations.
  - **Confidence Rating:** Explicit confidence score (e.g., 95% High Confidence).
- **Heuristic Fallback Engine:** If external API connectivity or quotas are interrupted, the built-in heuristic rule engine immediately generates validated baseline diagnostics, ensuring 100% operational uptime.

### 4. Interactive Incident Chat Assistant (AI Copilot)
- **Contextual In-Ticket Copilot:** Embedded drawer directly inside the incident workspace that understands the current ticket's title, description, category, and priority.
- **Multi-Turn Interactive Dialogue:** Support engineers can converse with the AI copilot to:
  - Ask follow-up questions: *"What logs should I check first for this Nginx error?"*
  - Simplify complex diagnostics: *"Explain this root cause in simpler terms for the client."*
  - Request alternative remediation: *"What if restarting the container doesn't clear the lock?"*
- **Quick-Prompt Suggestions:** One-click pre-composed prompts to accelerate triage.
- **Persistent Chat History:** Chat messages are saved per ticket and restored upon subsequent visits.

### 5. Historical Similar Incident Detection
- **Semantic & TF-IDF Incident Matching:** Analyzes the incident title and description against the complete database of historical incidents using high-dimensional TF-IDF feature vectors and bigram contextual awareness.
- **Relevance Scoring:** Computes mathematical similarity percentages (e.g., `92% Match`).
- **Prior Resolution Reuse:** Displays the exact resolution text applied to previous incidents so engineers can resolve recurring issues in seconds without repeating diagnostic cycles.

### 6. Technical Knowledge Base & Runbook Repository
- **8 Canonical IT Domains:** Covers `Network`, `Software`, `Hardware`, `Access & Security`, `Email & Communication`, `Cloud & Infrastructure`, `Billing & Accounts`, and `Database`.
- **Markdown-Rendered Runbook Viewer:** Formatted code blocks, bash commands, configuration tables, and troubleshooting flowcharts.
- **Interactive Search & Tag Filtering:** Search runbooks by keywords or filter by category tags.
- **Direct Incident Grounding:** Knowledge base articles serve as the canonical grounding corpus for RAG retrieval during incident analysis.

### 7. Production Hybrid Retrieval Engine (Hybrid RAG)
- **Overlapping Markdown Chunking (`ai-service/app/rag/chunker.py`):**
  - Chunks technical articles into 300–500 token segments (~1200–2000 characters).
  - 50–100 token overlap (~200–400 characters) across Markdown section boundaries to preserve technical context.
  - Injects contextual metadata headers `[{category}] {title}` into each chunk for optimal vector embedding separation.
- **Dense Vector Search (`gemini-embedding-001`):**
  - High-dimensional vector generation using `gemini-embedding-001` with `output_dimensionality=768` (`EMBED_DIM=768`).
  - Native Neon PostgreSQL `pgvector` HNSW index with cosine distance (`<=>`).
- **Sparse Full-Text Search (`tsvector`):**
  - PostgreSQL native full-text search with automated `tsvector` generation and inverted GIN indexing.
  - Relevance ranking powered by `ts_rank_cd`.
- **Reciprocal Rank Fusion (RRF):**
  - Fuses dense vector and sparse keyword rankings mathematically:
    $$\text{RRF\_Score}(d) = \sum_{m \in \{\text{vector}, \text{text}\}} \frac{1.0}{60 + \text{rank}_m(d)}$$
  - Normalizes disparate score distributions without arbitrary threshold scaling.
- **Gemini Neural Reranking (`ai-service/app/rag/reranker.py`):**
  - Re-evaluates Top 20 RRF candidates using `gemini-3.5-flash-lite` with structured scoring (0.0 to 1.0) and technical reasoning.
  - Filters out any hallucinated IDs and automatically falls back to RRF ordering if JSON parsing fails.
- **Feature Flag Control:** Toggle between pure full-text, hybrid RRF, and hybrid + reranking via `USE_HYBRID` and `USE_RERANK` environment flags.

### 8. Synthetic Dataset Benchmarking & Bulk Ingestion
- **Automated Seed Generator (`scripts/generate_seed_data.py`):** Generates reproducible, realistic IT helpdesk datasets with deterministic random seeds.
- **40 Canonical Technical Runbooks (`data/seed/kb_articles.jsonl`):** Deep troubleshooting procedures covering VPN gateways, Kubernetes pods, database replication lag, disk full errors, OAuth SSO loops, and more.
- **300 Historical Incident Tickets (`data/seed/tickets.jsonl`):** Diverse tickets with realistic timestamps, priority distributions, and verified resolutions.
- **60 Held-Out Golden Benchmark Tickets (`eval/golden_set.jsonl`):** Strictly isolated from the searchable knowledge base to enable clean, uncontaminated offline evaluation.
- **In-App Dataset Import Modal:** Easily import or reload seed data directly through the web UI.

### 9. High Availability, Fault Tolerance & DNS Resilience
- **Dual Database Architecture:**
  - **Neon PostgreSQL (Active Production):** Serverless, scalable cloud database with `pgvector` 0.8.7.
  - **SQLite Backup (`data/support_desk.db.backup`):** Byte-for-byte preserved snapshot of the original system.
- **ISP DNS Resilience:** Restrictive local ISP routers frequently fail to resolve `*.neon.tech` subdomains. Both the Python microservice (`dnspython`) and Node.js (`dns.Resolver`) feature built-in programmatic fallback to public resolvers (`8.8.8.8`, `1.1.1.1`) with TLS Server Name Indication (`SNI`), eliminating connection dropouts.
- **Resilient AI Timeouts:** Next.js requests to the AI microservice utilize an optimized 15-second abort signal with automatic fallback to heuristic analysis if the AI service is undergoing a cold start.

---

## 🏗️ System Architecture

```
                                  +---------------------------------------+
                                  |     Next.js 16 Full-Stack Web App     |
                                  |     (React 19, TypeScript, Tailwind)  |
                                  +--------+---------------------+--------+
                                           |                     |
                               Next.js API |                     | Fast REST Calls
                                  Routes   |                     | (15s resilient timeout)
                                           v                     v
                        +--------------------+        +----------------------+
                        |  Neon PostgreSQL   |        |  FastAPI AI Service  |
                        |  - tickets         |        |  - Health: /health   |
                        |  - kb_articles     |        |  - Analyze: /analyze |
                        |  - kb_chunks       |        |  - Search: /search   |
                        |  - pgvector (768d) |        |  - Index: /index     |
                        |  - GIN tsvector    |        +----------+-----------+
                        +--------------------+                   |
                                                                 | google-genai SDK
                                                                 v
                                                      +----------------------+
                                                      |  Google Gemini API   |
                                                      |  - gemini-3.5-flash-lite
                                                      |  - gemini-embedding-001
                                                      +----------------------+
```

### Hybrid RAG Retrieval Pipeline

```
                               +-----------------------------+
                               |    Incoming Support Issue   |
                               +--------------+--------------+
                                              |
                     +------------------------+------------------------+
                     |                                                 |
                     v                                                 v
           [Dense Vector Search]                             [Sparse Full-Text]
        gemini-embedding-001 (768d)                         PostgreSQL tsvector
            pgvector HNSW Cosine                                 ts_rank_cd
                     |                                                 |
                     +------------------------+------------------------+
                                              |
                                              v
                             [Reciprocal Rank Fusion (RRF)]
                             RRF(d) = sum(1.0 / (60 + rank))
                                              |
                                              v
                                      Top 20 Candidates
                                              |
                                              v
                                [Gemini Neural Reranking]
                                  gemini-3.5-flash-lite
                                  (Structured JSON list)
                                              |
                                              v
                                  Top 5 Grounded Runbooks
                                              |
                                              v
                               [Grounded Ticket Diagnosis]
```

---

## 📂 Project Directory Layout

```
digiplus-ai-service-desk/
├── ai-service/                         # Python FastAPI AI Microservice
│   ├── app/
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   └── connection.py           # Neon PostgreSQL connection with DNS fallback
│   │   ├── rag/
│   │   │   ├── __init__.py
│   │   │   ├── chunker.py              # Overlapping Markdown chunking (300-500 tokens)
│   │   │   ├── embeddings.py           # Gemini gemini-embedding-001 (768d) client
│   │   │   ├── indexer.py              # Idempotent batch KB chunk & vector indexer
│   │   │   ├── retriever.py            # Cosine vector search, tsvector search & RRF
│   │   │   ├── reranker.py             # Gemini neural reranker (Top 20 -> Top 5)
│   │   │   └── pipeline.py             # Feature-flagged retrieval orchestrator
│   │   ├── config.py                   # Pydantic v2 BaseSettings & environment loader
│   │   ├── main.py                     # FastAPI endpoints (/health, /analyze-ticket, /search, /index)
│   │   └── schemas.py                  # Pydantic request/response models
│   ├── tests/
│   │   ├── test_api.py                 # FastAPI endpoint validation tests
│   │   ├── test_chunker.py             # Markdown chunking unit tests
│   │   └── test_rag.py                 # RRF, embedding, and reranker unit tests
│   ├── Dockerfile
│   └── requirements.txt                # Python dependencies
├── data/
│   ├── seed/
│   │   ├── kb_articles.jsonl           # 40 canonical technical runbooks across 8 categories
│   │   └── tickets.jsonl               # 300 historical incident tickets
│   ├── support_desk.db                 # Preserved original SQLite database
│   └── support_desk.db.backup          # Byte-for-byte SQLite backup
├── db/
│   └── migrations/
│       └── 001_initial_schema.sql      # PostgreSQL DDL (pgvector, tickets, kb_articles, kb_chunks)
├── eval/
│   └── golden_set.jsonl                # 60 held-out evaluation tickets for clean benchmarking
├── scripts/
│   ├── generate_seed_data.py           # Synthetic seed dataset generator
│   ├── index_kb.py                     # CLI script to chunk and embed KB into pgvector
│   ├── load_seed.py                    # Loader for SQLite / PostgreSQL seed datasets
│   └── migrate_sqlite_to_postgres.py   # Complete SQLite-to-PostgreSQL migration script
├── src/                                # Next.js Application Source
│   ├── app/
│   │   ├── api/                        # Next.js API Routes (PostgreSQL CRUD)
│   │   │   ├── ai/chat/                # Ticket AI assistant chat endpoint
│   │   │   ├── dataset/import/         # Bulk dataset import endpoint
│   │   │   ├── knowledge-base/         # Knowledge base query endpoint
│   │   │   ├── stats/                  # Dashboard metrics calculation endpoint
│   │   │   └── tickets/                # Ticket creation, retrieval, and updates
│   │   ├── knowledge-base/             # Knowledge base browsing and search UI
│   │   ├── tickets/                    # Ticket list and filtering UI
│   │   │   └── [id]/                   # Ticket detail, AI analysis, chat & similarity UI
│   │   ├── layout.tsx                  # Global navigation and styling layout
│   │   └── page.tsx                    # Executive incident dashboard
│   ├── components/                     # Reusable React UI Components
│   │   ├── Badges.tsx                  # Status, Priority, Category badges
│   │   ├── CreateTicketModal.tsx       # New incident creation modal
│   │   ├── DatasetImportModal.tsx      # Batch dataset import modal
│   │   ├── Navbar.tsx                  # Top navigation bar
│   │   ├── SimilarIncidentsSection.tsx # Historical incident similarity component
│   │   └── TicketChatAssistant.tsx     # In-ticket conversational AI assistant
│   └── lib/
│       ├── ai.ts                       # Next.js -> FastAPI client with heuristic fallback
│       ├── chat.ts                     # In-memory ticket chat storage and prompt assembly
│       ├── dataset.ts                  # Dataset import utilities and schema mappers
│       ├── db.ts                       # Legacy SQLite client (read-only backup)
│       ├── postgres.ts                 # Production Neon PostgreSQL client with DNS resilience
│       ├── similarity.ts               # Semantic TF-IDF similarity matcher
│       └── types.ts                    # Core TypeScript interfaces
├── tests/
│   └── test_seed_data.py               # Seed dataset schema and golden set tests
├── .env.example                        # Template environment variables
├── .env.local                          # Active local environment variables (git-ignored)
├── package.json                        # Node.js dependencies and scripts
├── test-e2e.mjs                        # Full-stack E2E incident lifecycle verification script
└── README.md                           # Project documentation
```

---

## 🔄 End-to-End User Workflows

### Workflow 1: Submitting & Auto-Triaging an Incident
1. Click **"Create Ticket 🎫"** from the top navbar or dashboard hero.
2. Enter the issue title (e.g., *"Cannot connect to corporate VPN from remote office"*), description, and initial category.
3. Upon submission, the ticket is instantly committed to Neon PostgreSQL with status `Open`.
4. The dashboard KPIs immediately update to reflect the newly reported incident.

### Workflow 2: Automated AI Diagnosis with Grounded Runbooks
1. Open the newly created ticket from the dashboard or ticket list.
2. Click **"Analyze with AI 🤖"**.
3. Next.js triggers a POST call to `ai-service/app/main.py: /analyze-ticket`.
4. The Hybrid RAG engine queries `kb_chunks` via pgvector cosine search and `tsvector` keyword search, blends rankings using RRF ($k=60$), and reranks candidates using `gemini-3.5-flash-lite`.
5. The top matching runbook (e.g., *VPN Gateway Troubleshooting & Tunnel Reset*) is injected into the Gemini prompt.
6. The UI renders:
   - Root cause hypothesis.
   - Grounded runbook citations.
   - Step-by-step terminal remediation checklist with one-click copy buttons.

### Workflow 3: Interactive Troubleshooting with the AI Copilot
1. In the **"AI Incident Assistant"** drawer on the ticket page, review suggested questions or type a custom query.
2. Ask: *"What log file should I inspect to verify the VPN handshake?"*
3. The AI assistant responds in real-time with specific log paths (`/var/log/openvpn.log`) and filtering commands (`grep -i 'tls-error'`).
4. Conversations are automatically preserved across page reloads.

### Workflow 4: Checking Similar Historical Incidents
1. Scroll to the **"Similar Past Incidents"** section on the ticket page.
2. The system surfaces past resolved tickets sharing semantic overlap (e.g., *Ticket #12: VPN tunnel dropping on UDP 1194 - 94% Match*).
3. Expand the incident to view the exact resolution notes entered by the prior engineer.

### Workflow 5: Resolving & Closing the Incident
1. Execute the remediation steps.
2. Enter the resolution notes in the **"Incident Resolution"** box.
3. Update the ticket status to `Resolved` or `Closed`.
4. Click **"Save Resolution"**—the ticket updates in PostgreSQL and the dashboard resolution rate reflects the closed ticket.

---

## 🗄️ Database Schema & Data Models

### PostgreSQL Tables (Neon Serverless)

#### 1. `tickets`
Stores active and historical IT incident records:
```sql
CREATE TABLE tickets (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    priority VARCHAR(50) NOT NULL,
    category VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Open',
    resolution TEXT,
    ai_summary TEXT,
    ai_cause TEXT,
    ai_solution TEXT,
    ai_suggested_category VARCHAR(100),
    ai_suggested_priority VARCHAR(50),
    source VARCHAR(50) DEFAULT 'manual',
    external_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. `kb_articles`
Canonical technical runbooks and documentation:
```sql
CREATE TABLE kb_articles (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    summary TEXT,
    content TEXT NOT NULL,
    tags JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

#### 3. `kb_chunks`
Vectorized and full-text indexed chunks for Hybrid RAG:
```sql
CREATE TABLE kb_chunks (
    id SERIAL PRIMARY KEY,
    article_id INTEGER NOT NULL REFERENCES kb_articles(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768),
    tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX kb_chunks_embedding_idx ON kb_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX kb_chunks_tsv_idx ON kb_chunks USING gin (tsv);
```

#### 4. `agent_runs` & `feedback`
Audit logs for autonomous agent runs and user feedback:
```sql
CREATE TABLE agent_runs (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER REFERENCES tickets(id) ON DELETE SET NULL,
    agent_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    prompt TEXT,
    response TEXT,
    tool_calls JSONB DEFAULT '[]'::jsonb,
    latency_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE feedback (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER REFERENCES tickets(id) ON DELETE CASCADE,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comments TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

## 📡 API Endpoints Reference

### AI Microservice (Port 8000)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Healthcheck verifying PostgreSQL, `pgvector`, and Gemini models |
| `GET` | `/search` | Executes Hybrid RAG search (`?q=...&category=...&limit=...`) |
| `POST` | `/analyze-ticket` | Generates structured diagnostic and remediation grounded in runbooks |
| `POST` | `/index` | Triggers re-chunking and re-embedding of all knowledge base articles |

#### Sample Request: `POST /analyze-ticket`
```json
{
  "ticket": {
    "id": 105,
    "title": "PostgreSQL connection pool exhausted",
    "description": "API services reporting FATAL: remaining connection slots are reserved",
    "category": "database",
    "priority": "P1"
  }
}
```

#### Sample Response: `POST /analyze-ticket`
```json
{
  "diagnostic": "PostgreSQL backend client connection pool saturation.",
  "root_cause": "Unclosed database sessions from long-running batch transactions exceeding max_connections.",
  "suggested_steps": [
    "Query pg_stat_activity for idle-in-transaction connections.",
    "Terminate long-running unpooled queries.",
    "Increase PgBouncer pool ceiling or restart connection pooling layer."
  ],
  "grounded_runbooks": [
    {
      "article_title": "PostgreSQL Connection Pooling & Saturation Recovery",
      "category": "database"
    }
  ],
  "confidence": 0.95
}
```

### Next.js Full-Stack Application (Port 3000)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/stats` | Aggregated dashboard metrics and category breakdowns |
| `GET` | `/api/tickets` | Query tickets with search, pagination, and multi-field filters |
| `POST` | `/api/tickets` | Create a new incident ticket in PostgreSQL |
| `GET` | `/api/tickets/[id]` | Fetch ticket details by ID with AI analysis |
| `PATCH` | `/api/tickets/[id]` | Update ticket status, priority, category, or resolution |
| `GET` | `/api/knowledge-base` | Search runbooks and retrieve relevant articles |
| `GET` | `/api/ai/chat` | Retrieve ticket-specific conversation history |
| `POST` | `/api/ai/chat` | Send a message to the in-ticket AI copilot |
| `POST` | `/api/dataset/import` | Ingest batch synthetic seed dataset |

---

## ⚙️ Environment Configuration

Create a `.env.local` file in the project root (git-ignored, never committed):

```env
# ==========================================
# Google Gemini API
# ==========================================
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
EMBED_MODEL=gemini-embedding-001
EMBED_DIM=768

# ==========================================
# Neon Hosted PostgreSQL
# ==========================================
DATABASE_URL=postgresql://neondb_owner:YOUR_PASSWORD@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require

# ==========================================
# AI Service & Retrieval Feature Flags
# ==========================================
AI_SERVICE_URL=http://localhost:8000
USE_HYBRID=true
USE_RERANK=true
```

| Variable | Default Value | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://...` | Neon PostgreSQL connection string with `?sslmode=require` |
| `GEMINI_API_KEY` | *(Secret)* | Google Gemini API Key from Google AI Studio |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Primary LLM model for analysis, chat, and reranking |
| `EMBED_MODEL` | `gemini-embedding-001` | Embedding model for dense vector search |
| `EMBED_DIM` | `768` | Vector dimension matching `vector(768)` in PostgreSQL |
| `AI_SERVICE_URL` | `http://localhost:8000` | URL where the FastAPI microservice is listening |
| `USE_HYBRID` | `true` | Enables vector + full-text RRF search |
| `USE_RERANK` | `true` | Enables Gemini neural reranking on top RRF candidates |

---

## 🚀 Step-by-Step Setup & Execution

### 1. Prerequisites
- **Node.js:** 18.18+ (tested with Node 20+)
- **Python:** 3.10+ (tested with Python 3.12)
- **Neon Account:** Free serverless PostgreSQL project at [neon.tech](https://neon.tech/)
- **Gemini API Key:** Free API key from [Google AI Studio](https://aistudio.google.com/)

### 2. Install Dependencies
```bash
# Install Node.js frontend and API dependencies
npm install

# Install Python AI microservice dependencies
pip install -r ai-service/requirements.txt
```

### 3. Run Knowledge Base Indexing
Chunk, embed, and index all runbooks into Neon `pgvector`:
```bash
python scripts/index_kb.py
```

### 4. Start the Application Servers
Open two terminal windows:

**Terminal 1 — FastAPI AI Microservice:**
```bash
python -m uvicorn app.main:app --app-dir ai-service --host 127.0.0.1 --port 8000
```

**Terminal 2 — Next.js Full-Stack Web App:**
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🧪 Automated Testing & Quality Verification

DigiPlus includes an extensive automated test suite covering unit logic, RAG pipelines, API contracts, TypeScript types, and end-to-end incident workflows:

```bash
# 1. Run all Python unit and integration tests (Chunker, RAG, API, Seed data):
$env:PYTHONPATH="ai-service"; python -m pytest ai-service/tests/ tests/test_seed_data.py -v

# 2. Run TypeScript strict type-check:
npx tsc --noEmit

# 3. Run full-stack End-to-End incident lifecycle verification:
node test-e2e.mjs
```

### Test Suite Breakdown:
- **`ai-service/tests/test_chunker.py` (6 tests):** Short/long article splitting, context overlap, duplicate prevention, and metadata preservation.
- **`ai-service/tests/test_rag.py` (12 tests):** RRF formula accuracy, embedding dimension checks, reranker hallucination drop guards, fallback mechanisms, and feature flag routing.
- **`ai-service/tests/test_api.py` (8 tests):** FastAPI `/health`, `/analyze-ticket`, `/search`, `/index` schema conformity and input validation.
- **`tests/test_seed_data.py` (9 tests):** Seed datasets, schema coverage, category coverage, and golden set benchmark isolation.
- **`test-e2e.mjs` (11 suites):** End-to-end verification of ticket creation, AI analysis, runbook matching, ticket resolution, dataset batch import, semantic duplicate detection, conversational AI assistant, and dashboard recalculation.

---

## 📈 Implementation Progress (Phases 0–2)

### Phase 0: Synthetic IT Helpdesk Datasets & Evaluation Benchmark ✅
- Created 40 canonical technical runbooks across 8 categories (`data/seed/kb_articles.jsonl`).
- Created 300 historical incident tickets (`data/seed/tickets.jsonl`).
- Created 60 held-out golden evaluation tickets strictly isolated from the searchable index (`eval/golden_set.jsonl`).
- Implemented synthetic data generator and dataset loaders.

### Phase 1: Neon PostgreSQL, `pgvector`, FastAPI & SQLite Migration ✅
- Configured Neon serverless PostgreSQL with `pgvector` 0.8.7 (no local Docker required).
- Applied schema migration `001_initial_schema.sql`.
- Migrated existing SQLite database to PostgreSQL with 100% field parity and sequence resets.
- Preserved byte-for-byte SQLite backup (`data/support_desk.db.backup`).
- Implemented FastAPI AI microservice with `/health` and `/analyze-ticket`.
- Implemented resilient public DNS resolution with TLS SNI in Python and Node.js.

### Phase 2: Hybrid Retrieval (Hybrid RAG) Engine ✅
- Implemented overlapping Markdown chunker (300–500 tokens, 50–100 token overlap).
- Integrated `gemini-embedding-001` pinned to 768 dimensions with batching and exponential backoff retries.
- Implemented dense vector cosine search over pgvector HNSW index.
- Implemented sparse keyword search using PostgreSQL `tsvector` and GIN index.
- Implemented Reciprocal Rank Fusion ($k=60$) combining vector and keyword rankings.
- Implemented Gemini neural reranker (`gemini-3.5-flash-lite`) evaluating Top 20 candidates into Top 5.
- Integrated grounded runbook injection into `/analyze-ticket` for context-grounded diagnostics.

---

## 🔮 Upcoming Roadmap (Phases 3 & 4)

### Phase 3: Tool-Using Autonomous LLM Agent Loop
- Autonomous incident investigation loop with Gemini Function Calling.
- Diagnostic tools: Knowledge search, incident history lookup, status updater.
- `agent_runs` PostgreSQL audit logging with step-by-step reasoning traces.

### Phase 4: Automated Evaluation & Golden Set Benchmarking
- Automated offline evaluation pipeline evaluating golden set tickets against historical incident resolutions.
- Retrieval recall metrics (Recall@K, MRR) and LLM diagnostic accuracy scoring.

---

## 🔒 Security & Best Practices

- **Zero Hardcoded Secrets:** All credentials, database connection strings, and API keys are strictly loaded via `.env.local`.
- **Git Protection:** `.env*` files (except `.env.example`), `.backup` files, and database binaries are strictly ignored in `.gitignore`.
- **Hallucination Prevention:** Gemini reranker strictly verifies returned IDs against input candidate lists; invented IDs are systematically discarded.
- **Fail-Safe Heuristic Fallback:** If external AI services or quotas are unavailable, the system automatically falls back to deterministic rule-based analysis, ensuring business continuity.
- **TLS SNI & Public DNS Fallback:** Prevents network connection failures caused by local ISP DNS filtering on cloud database subdomains.
