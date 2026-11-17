# DigiPlus AI-Powered Service Desk 🤖🎫

[![Next.js](https://img.shields.io/badge/Next.js-16.0-black?style=flat&logo=next.js)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19.0-blue?style=flat&logo=react)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18.7-336791?style=flat&logo=postgresql)](https://www.postgresql.org/)
[![pgvector](https://img.shields.io/badge/pgvector-0.8.7-336791?style=flat)](https://github.com/pgvector/pgvector)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-3.5_Flash_Lite-4285F4?style=flat&logo=google)](https://ai.google.dev/)
[![Tests](https://img.shields.io/badge/Tests-35%2F35_Passing-brightgreen?style=flat)](file:///d:/ai-service-desk/digiplus-ai-service-desk/ai-service/tests)

A production-grade, enterprise IT Service Desk and automated incident remediation system upgraded with **Neon Serverless PostgreSQL**, **`pgvector` dense vector embeddings**, **PostgreSQL full-text search**, a **FastAPI AI microservice**, and **Google Gemini (Generative AI & Embeddings)**.

The system triages natural language incidents, calculates automated root-cause diagnostics, retrieves technical runbooks with **Hybrid RAG (Dense Vector + Full-Text + RRF + Neural Reranking)**, and tracks the complete incident resolution lifecycle.

---

## 📑 Table of Contents
- [Upgraded Architecture](#-upgraded-architecture)
- [Project Directory Structure](#-project-directory-structure)
- [Implementation Progress](#-implementation-progress)
  - [Phase 0: Synthetic Datasets & Golden Benchmark](#phase-0-synthetic-datasets--golden-benchmark)
  - [Phase 1: Neon PostgreSQL, pgvector & FastAPI](#phase-1-neon-postgresql-pgvector--fastapi)
  - [Phase 2: Hybrid Retrieval (Hybrid RAG) Engine](#phase-2-hybrid-retrieval-hybrid-rag-engine)
- [API Endpoints Reference](#-api-endpoints-reference)
- [Environment Configuration](#-environment-configuration)
- [Step-by-Step Setup & Execution](#-step-by-step-setup--execution)
- [Automated Testing & Verification](#-automated-testing--verification)
- [Security & Resilience](#-security--resilience)
- [Upcoming Roadmap (Phase 3 & 4)](#-upcoming-roadmap)

---

## 🌟 Upgraded Architecture

```
                      +-----------------------------------+
                      |   Next.js 16 Full-Stack Web App   |
                      |   (React 19, TypeScript, Tailwind)|
                      +--------+-----------------+--------+
                               |                 |
                   Next.js API |                 | Fast REST Calls
                      Routes   |                 | (15s resilient timeout)
                               v                 v
            +--------------------+    +----------------------+
            | Neon PostgreSQL    |    | FastAPI AI Service   |
            | - tickets          |    | - Health: /health    |
            | - kb_articles      |    | - Analyze: /analyze  |
            | - kb_chunks        |    | - Search: /search    |
            | - pgvector (768d)  |    | - Index: /index      |
            | - GIN tsvector     |    +----------+-----------+
            +--------------------+               |
                                                 | google-genai SDK
                                                 v
                                      +----------------------+
                                      | Google Gemini API    |
                                      | - gemini-3.5-flash-lite
                                      | - gemini-embedding-001
                                      +----------------------+
```

### Technology Stack
- **Frontend & Web Gateway:** Next.js (App Router), React, TypeScript strict mode, Tailwind CSS.
- **AI Microservice:** Python 3.12, FastAPI, Uvicorn, Pydantic v2 validation.
- **Database:** Neon hosted Serverless PostgreSQL 18.7 with native `pgvector` 0.8.7.
- **Vector Search:** `pgvector` HNSW index with cosine distance (`<=>`).
- **Full-Text Search:** PostgreSQL `tsvector` with inverted GIN index and `ts_rank_cd`.
- **Large Language Model:** Google Gemini (`gemini-3.5-flash-lite`, with fallback to `gemini-3.1-flash-lite` / `gemini-3.8-flash`).
- **Embedding Model:** `gemini-embedding-001` pinned to `EMBED_DIM=768` (`output_dimensionality=768`).
- **Legacy Storage:** SQLite (`data/support_desk.db`) preserved with automatic migration to PostgreSQL.

---

## 📂 Project Directory Structure

```
digiplus-ai-service-desk/
├── ai-service/                         # Python FastAPI AI Microservice
│   ├── app/
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   └── connection.py           # Resilient Neon connection with DNS fallback
│   │   ├── rag/
│   │   │   ├── __init__.py
│   │   │   ├── chunker.py              # Overlapping Markdown chunking (300-500 tokens)
│   │   │   ├── embeddings.py           # Gemini gemini-embedding-001 (768d) client
│   │   │   ├── indexer.py              # Idempotent batch KB chunk & vector indexer
│   │   │   ├── retriever.py            # Cosine vector search, tsvector search & RRF
│   │   │   ├── reranker.py             # Gemini neural reranker (Top 20 -> Top 5)
│   │   │   └── pipeline.py             # Feature-flagged retrieval orchestrator
│   │   ├── config.py                   # Pydantic v2 BaseSettings & environment loader
│   │   ├── main.py                     # FastAPI entrypoint (/health, /analyze-ticket, /search, /index)
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
│   │   │   ├── knowledge-base/
│   │   │   ├── stats/
│   │   │   └── tickets/
│   │   ├── knowledge-base/             # Knowledge base browsing UI
│   │   ├── tickets/                    # Ticket lifecycle management UI
│   │   ├── layout.tsx
│   │   └── page.tsx                    # Executive incident dashboard
│   ├── components/                     # React UI Components
│   └── lib/
│       ├── ai.ts                       # Next.js -> FastAPI client with heuristic fallback
│       ├── db.ts                       # Legacy SQLite client (read-only backup)
│       ├── postgres.ts                 # Production Neon PostgreSQL client with DNS resilience
│       └── types.ts                    # Core TypeScript interfaces
├── tests/
│   └── test_seed_data.py               # Seed dataset schema and golden set tests
├── .env.example                        # Template environment variables
├── .env.local                          # Active local environment variables (git-ignored)
├── package.json                        # Node.js dependencies and scripts
├── test-e2e.mjs                        # Full-stack E2E incident lifecycle verification script
└── README.md
```

---

## 📋 Implementation Progress

### Phase 0: Synthetic Datasets & Golden Benchmark
- **`data/seed/kb_articles.jsonl`**: 40 canonical technical runbooks spanning 8 core IT categories (`network`, `email`, `VPN and access`, `hardware`, `software installation`, `account and password`, `database`, `performance`).
- **`data/seed/tickets.jsonl`**: 300 realistic historical incident tickets with verified resolutions and category mappings.
- **`eval/golden_set.jsonl`**: 60 held-out evaluation tickets strictly isolated from the searchable index to ensure clean, uncontaminated benchmarking.
- **Data Generator & Loader:**
  ```bash
  python scripts/generate_seed_data.py --seed 42
  python scripts/load_seed.py --db-type sqlite
  python -m pytest tests/test_seed_data.py -v
  ```

---

### Phase 1: Neon PostgreSQL, `pgvector`, FastAPI & SQLite Migration
- **Neon Hosted Database:** Fully serverless hosted PostgreSQL, bypassing local Docker requirements.
- **pgvector Extension:** Enabled native `vector` extension (v0.8.7) on PostgreSQL 18.7.
- **Database Schema Migration:** Applied [`db/migrations/001_initial_schema.sql`](file:///d:/ai-service-desk/digiplus-ai-service-desk/db/migrations/001_initial_schema.sql) defining `kb_articles`, `kb_chunks`, `tickets`, `agent_runs`, and `feedback`.
- **Data Migration:** [`scripts/migrate_sqlite_to_postgres.py`](file:///d:/ai-service-desk/digiplus-ai-service-desk/scripts/migrate_sqlite_to_postgres.py) migrated existing tickets and KB articles with 100% field fidelity, sequence resets, and SQLite backup preservation (`data/support_desk.db.backup`).
- **FastAPI AI Microservice:** Implemented in `ai-service/app/main.py`:
  - `GET /health`: Verifies database connectivity, pgvector extension, and configured Gemini models.
  - `POST /analyze-ticket`: Generates diagnostic root cause analysis and step-by-step remediation via Gemini.
- **DNS Resilience:** Integrated resilient DNS resolution via `dnspython` and Node.js custom TLS SNI to resolve Neon domains reliably across restrictive local ISP DNS filters.

---

### Phase 2: Hybrid Retrieval (Hybrid RAG) Engine
Combines dense vector embeddings, sparse full-text search, Reciprocal Rank Fusion (RRF), and Gemini neural reranking:

```
                           +----------------------+
                           | Incoming Query/Issue |
                           +----------+-----------+
                                      |
                 +--------------------+--------------------+
                 |                                         |
                 v                                         v
       [Dense Vector Search]                     [Sparse Full-Text]
    gemini-embedding-001 (768d)                 PostgreSQL tsvector
        pgvector HNSW Cosine                        ts_rank_cd
                 |                                         |
                 +--------------------+--------------------+
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
```

#### 1. Knowledge Base Chunking Strategy ([`ai-service/app/rag/chunker.py`](file:///d:/ai-service-desk/digiplus-ai-service-desk/ai-service/app/rag/chunker.py))
- **Chunk Size:** 300–500 tokens (~1200–2000 characters), splitting at natural Markdown section and paragraph boundaries.
- **Overlap:** 50–100 tokens (~200–400 characters) to preserve technical context across boundary cuts.
- **Context Grounding:** Every chunk prepends a metadata header `[{category}] {title}` to maximize vector retrieval accuracy.
- **Idempotency:** Short articles within the target threshold are preserved as a single chunk without unnecessary splitting.

#### 2. Dense Vector Embeddings ([`ai-service/app/rag/embeddings.py`](file:///d:/ai-service-desk/digiplus-ai-service-desk/ai-service/app/rag/embeddings.py))
- **Model:** `gemini-embedding-001` via the official `google-genai` SDK.
- **Dimensions:** Strict constant `EMBED_DIM=768` (`output_dimensionality=768`), validated before database insertion.
- **Reliability:** Built-in batching, exponential backoff (`1s, 2s, 4s`), and rate-limit recovery.

#### 3. Idempotent Indexing ([`scripts/index_kb.py`](file:///d:/ai-service-desk/digiplus-ai-service-desk/scripts/index_kb.py))
- Chunks articles from `kb_articles`, generates Gemini embeddings, and populates `kb_chunks`.
- Deletes prior chunks for an article before re-indexing to prevent duplicate or orphaned chunks.

#### 4. Semantic Vector Search & Full-Text Search ([`ai-service/app/rag/retriever.py`](file:///d:/ai-service-desk/digiplus-ai-service-desk/ai-service/app/rag/retriever.py))
- **Cosine Distance:** `1.0 - (c.embedding <=> query_vector::vector)` over pgvector HNSW index.
- **Keyword Search:** `ts_rank_cd(c.tsv, query)` against PostgreSQL `tsvector` with GIN indexing.
- **Category Filtering:** Supports technical category filters (`Network`, `Database`, etc.).

#### 5. Reciprocal Rank Fusion (RRF)
Fuses dense vector and sparse keyword rankings without mixing incompatible score distributions:
$$\text{RRF\_Score}(d) = \sum_{m \in \{\text{vector}, \text{text}\}} \frac{1.0}{k + \text{rank}_m(d)}$$
- **Default Smoothing Constant:** $k = 60$.
- Deduplicates results by `chunk_id` and sorts in descending order.

#### 6. Gemini Neural Reranking ([`ai-service/app/rag/reranker.py`](file:///d:/ai-service-desk/digiplus-ai-service-desk/ai-service/app/rag/reranker.py))
- Evaluates Top 20 RRF candidates using `gemini-3.5-flash-lite`.
- Generates structured relevance scores (0.0 to 1.0) and technical reasoning.
- **Strict Safeguards:** Drops hallucinated/invented chunk IDs and automatically falls back to RRF candidate order on malformed JSON or API errors.

#### 7. Grounded Incident Analysis Integration
In [`POST /analyze-ticket`](file:///d:/ai-service-desk/digiplus-ai-service-desk/ai-service/app/main.py), top retrieved and reranked runbook chunks are formatted and injected directly into the Gemini prompt:
- Grounds root cause diagnostics in actual organization runbooks.
- Cites specific matched runbook titles and categories.
- Produces actionable, context-aware remediation steps.

#### 8. Feature Flag Matrix ([`ai-service/app/rag/pipeline.py`](file:///d:/ai-service-desk/digiplus-ai-service-desk/ai-service/app/rag/pipeline.py))

| `USE_HYBRID` | `USE_RERANK` | Active Retrieval Pipeline |
|---|---|---|
| `false` | `false` | Basic PostgreSQL full-text search (`tsvector`) |
| `true` | `false` | Dense vector + sparse full-text search fused with RRF |
| `true` | `true` | Hybrid search + RRF + Gemini neural reranking (default) |

---

## 📡 API Endpoints Reference

### AI Microservice (Port 8000)

#### `GET /health`
Verifies database connectivity, pgvector extension, and configured model settings.
```json
{
  "status": "healthy",
  "database": "connected",
  "vector_extension": "available",
  "llm_model": "gemini-3.5-flash-lite",
  "embed_model": "gemini-embedding-001",
  "embed_dim": 768
}
```

#### `GET /search?q={query}&category={category}&limit={limit}`
Executes hybrid retrieval over knowledge-base runbooks.
```json
{
  "query": "VPN connection timed out error 403",
  "total": 5,
  "pipeline": "hybrid_rerank",
  "results": [
    {
      "chunk_id": 14,
      "article_id": 4,
      "article_title": "VPN Gateway Troubleshooting & Tunnel Reset",
      "category": "network",
      "chunk_index": 0,
      "content": "[network] VPN Gateway Troubleshooting...",
      "score": 0.94,
      "rerank_score": 0.94,
      "rerank_reason": "Directly matches VPN gateway timeout symptoms and provides reset commands."
    }
  ]
}
```

#### `POST /analyze-ticket`
Generates grounded incident diagnostics using Gemini and matching runbooks.
- **Request:**
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
- **Response:**
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

#### `POST /index`
Triggers full re-chunking and re-embedding of all knowledge-base articles.
```json
{
  "status": "indexed",
  "articles_indexed": 6,
  "chunks_created": 6
}
```

---

## ⚙️ Environment Configuration

Configure your local `.env.local` file (git-ignored, never committed):

| Variable | Default Value | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://...` | Neon PostgreSQL connection string with `?sslmode=require` |
| `GEMINI_API_KEY` | *(Secret)* | Google Gemini API Key from Google AI Studio |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Primary LLM model for analysis and reranking |
| `EMBED_MODEL` | `gemini-embedding-001` | Embedding model for dense vector search |
| `EMBED_DIM` | `768` | Vector dimension matching pgvector column |
| `AI_SERVICE_URL` | `http://localhost:8000` | URL where the FastAPI service is listening |
| `USE_HYBRID` | `true` | Enables vector + full-text RRF search |
| `USE_RERANK` | `true` | Enables Gemini neural reranking on top RRF candidates |

---

## 🚀 Step-by-Step Setup & Execution

### 1. Install Node.js & Python Dependencies
```bash
# Node.js dependencies
npm install

# Python AI Service dependencies
pip install -r ai-service/requirements.txt
```

### 2. Configure Environment (`.env.local`)
Create or edit `.env.local`:
```env
# Google Gemini API
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
EMBED_MODEL=gemini-embedding-001
EMBED_DIM=768

# Database (Neon PostgreSQL)
DATABASE_URL=postgresql://neondb_owner:YOUR_PASSWORD@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require

# AI Service & Feature Flags
AI_SERVICE_URL=http://localhost:8000
USE_HYBRID=true
USE_RERANK=true
```

### 3. Run Knowledge Base Indexing
To chunk and embed all runbooks into Neon `pgvector`:
```bash
python scripts/index_kb.py
```

### 4. Start the Application Servers
Open two terminal windows:

**Terminal 1 — FastAPI AI Microservice:**
```bash
python -m uvicorn app.main:app --app-dir ai-service --host 127.0.0.1 --port 8000
```

**Terminal 2 — Next.js Full-Stack Application:**
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🧪 Automated Testing & Verification

The project includes an extensive test suite verifying Python services, Next.js type safety, and full-stack incident workflows:

```bash
# 1. Run all Python unit and integration tests (Chunker, RAG, API, Seed data):
$env:PYTHONPATH="ai-service"; python -m pytest ai-service/tests/ tests/test_seed_data.py -v

# 2. Run TypeScript strict type-check:
npx tsc --noEmit

# 3. Run full-stack End-to-End incident lifecycle verification:
node test-e2e.mjs
```

### Test Suite Breakdown:
- **`ai-service/tests/test_chunker.py` (6 tests):** Short/long article splitting, context overlap, duplicate prevention, metadata preservation.
- **`ai-service/tests/test_rag.py` (12 tests):** RRF formula accuracy, embedding dimension checks, reranker hallucination drop guards, fallback mechanisms, and feature flag routing.
- **`ai-service/tests/test_api.py` (8 tests):** FastAPI `/health`, `/analyze-ticket`, `/search`, `/index` schema conformity and input validation.
- **`tests/test_seed_data.py` (9 tests):** Seed datasets, schema coverage, category coverage, and golden set benchmark isolation.
- **`test-e2e.mjs` (11 suites):** End-to-end verification of ticket creation, AI analysis, runbook matching, ticket resolution, dataset batch import, semantic duplicate detection, conversational AI assistant, and dashboard recalculation.

---

## 🔒 Security & Resilience
- **No Hardcoded Secrets:** All API keys, database URLs, and passwords reside exclusively in `.env.local` and environment variables.
- **Git Protection:** `.env*` files (except `.env.example`), `.backup` files, and database binaries are strictly ignored in `.gitignore`.
- **Hallucination Safeguards:** Gemini reranker strictly verifies returned IDs against input candidate lists; invented IDs are systematically discarded.
- **Resilient Fallback:** The application maintains 100% operational availability through heuristic fallback layers in the event of external network interruptions.
- **DNS Resilience:** Both Python and Node.js clients include automatic fallback to public DNS resolvers (`8.8.8.8`) with TLS Server Name Indication (`SNI`) to prevent connection failures caused by local ISP DNS filtering.

---

## 🔮 Upcoming Roadmap

### Phase 3: Tool-Using Autonomous LLM Agent Loop
- Autonomous incident investigation loop with Gemini Function Calling.
- Diagnostic tools: Knowledge search, incident history lookup, status updater.
- `agent_runs` PostgreSQL audit logging with step-by-step reasoning traces.

### Phase 4: Automated Evaluation & Golden Set Benchmarking
- Automated offline evaluation pipeline evaluating golden set tickets against historical incident resolutions.
- Retrieval recall metrics (Recall@K, MRR) and LLM diagnostic accuracy scoring.
