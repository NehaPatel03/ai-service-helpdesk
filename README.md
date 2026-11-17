# DigiPlus AI-Powered Service Desk 🤖🎫

A production-grade, full-stack IT Service Desk and automated incident remediation system upgraded with **Neon Serverless PostgreSQL**, **`pgvector` dense vector embeddings**, **PostgreSQL full-text search**, a **FastAPI AI microservice**, and **Google Gemini (Generative AI & Embeddings)**.

The system empowers IT support engineers by triaging natural language incidents, calculating automated root-cause diagnostics, searching runbooks with **Hybrid RAG (Dense Vector + Full-Text + RRF + Neural Reranking)**, and tracking the complete incident resolution lifecycle.

---

## 🌟 Upgraded Architecture Overview

```
                      +-----------------------------------+
                      |   Next.js 16 Full-Stack Web App   |
                      |   (React 19, TypeScript, Tailwind)|
                      +--------+-----------------+--------+
                               |                 |
                   Next.js API |                 | Fast REST Calls
                      Routes   |                 |
                               v                 v
            +--------------------+    +----------------------+
            | Neon PostgreSQL    |    | FastAPI AI Service   |
            | - tickets          |    | - Health: /health    |
            | - kb_articles      |    | - Analyze: /analyze  |
            | - kb_chunks        |    | - Search: /search    |
            | - pgvector (768d)  |    | - Index: /index      |
            | - GIN tsvector     |    +----------+-----------+
            +--------------------+               |
                                                 | google-genai
                                                 v
                                      +----------------------+
                                      | Google Gemini API    |
                                      | - gemini-3.5-flash-lite
                                      | - gemini-embedding-001
                                      +----------------------+
```

### Technology Stack
- **Frontend & Full-Stack Gateway:** Next.js (App Router), React, TypeScript strict mode, Tailwind CSS.
- **AI Microservice:** Python 3.12, FastAPI, Uvicorn, Pydantic v2 validation.
- **Database:** Neon hosted Serverless PostgreSQL 18.7 with native `pgvector` 0.8.7.
- **Vector Search:** `pgvector` HNSW index with cosine distance (`<=>`).
- **Full-Text Search:** PostgreSQL `tsvector` with inverted GIN index and `ts_rank_cd`.
- **Large Language Model:** Google Gemini (`gemini-3.5-flash-lite`, with fallback to `gemini-3.1-flash-lite` / `gemini-3.8-flash`).
- **Embedding Model:** `gemini-embedding-001` pinned to `EMBED_DIM=768` (`output_dimensionality=768`).
- **Legacy Storage:** SQLite (`data/support_desk.db`) preserved with automatic migration to PostgreSQL.

---

## 📋 Implementation Progress & Completed Phases

### Phase 0: Synthetic IT Helpdesk Datasets & Evaluation Benchmark
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
- **Neon Hosted Database:** Configured without requiring Docker Desktop, saving host disk space.
- **pgvector Extension:** Enabled `vector` extension version `0.8.7` on PostgreSQL 18.7.
- **Database Schema Migration:** [`db/migrations/001_initial_schema.sql`](file:///d:/ai-service-desk/digiplus-ai-service-desk/db/migrations/001_initial_schema.sql) defining `kb_articles`, `kb_chunks`, `tickets`, `agent_runs`, and `feedback`.
- **Data Migration:** [`scripts/migrate_sqlite_to_postgres.py`](file:///d:/ai-service-desk/digiplus-ai-service-desk/scripts/migrate_sqlite_to_postgres.py) migrated existing tickets and KB articles with 100% parity, sequence resets, and SQLite backup preservation (`data/support_desk.db.backup`).
- **FastAPI AI Microservice:** Implemented in `ai-service/` with endpoints:
  - `GET /health`: Database connection status, vector extension verification, model constants.
  - `POST /analyze-ticket`: Structured incident diagnosis, root cause analysis, and remediation steps.
- **DNS Resilience:** Integrated resilient DNS resolution via `dnspython` and Node.js custom TLS SNI to bypass restrictive local ISP DNS filters.

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
- **Chunk Size:** 300–500 tokens (~1200–2000 characters), splitting at natural markdown section and paragraph boundaries.
- **Overlap:** 50–100 tokens (~200–400 characters) to preserve technical context across boundary cuts.
- **Context Grounding:** Every chunk prepends a metadata header `[{category}] {title}` to maximize vector retrieval accuracy.
- **Idempotency:** Short articles within the target threshold are stored as a single chunk without unnecessary splitting.

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

#### 7. Feature Flag Matrix ([`ai-service/app/rag/pipeline.py`](file:///d:/ai-service-desk/digiplus-ai-service-desk/ai-service/app/rag/pipeline.py))

| `USE_HYBRID` | `USE_RERANK` | Active Retrieval Pipeline |
|---|---|---|
| `false` | `false` | Basic PostgreSQL full-text search (`tsvector`) |
| `true` | `false` | Dense vector + sparse full-text search fused with RRF |
| `true` | `true` | Hybrid search + RRF + Gemini neural reranking (default) |

---

## ⚙️ Environment Variables Reference

Configure these in your local `.env.local` file (git-ignored, never committed):

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

## 🧪 Comprehensive Automated Testing

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

## 🔒 Security & Best Practices
- **No Hardcoded Secrets:** All API keys, database URLs, and passwords reside exclusively in `.env.local` and environment variables.
- **Git Protection:** `.env*` files (except `.env.example`), `.backup` files, and database binaries are strictly ignored in `.gitignore`.
- **Hallucination Safeguards:** Gemini reranker strictly verifies returned IDs against input candidate lists; invented IDs are systematically discarded.
- **Resilient Fallback:** The application maintains 100% operational availability through heuristic fallback layers in the event of external network interruptions.
