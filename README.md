# DigiPlus AI-Powered Service Desk 🤖🎫

A clean, modern, and intelligent IT Service Desk web application built for the **DigiPlus Technical Assessment**. The application assists support engineers in triaging natural language incident descriptions, generating automated AI root-cause diagnostics, matching relevant technical knowledge-base runbooks, and recording incident resolutions with persistent SQLite storage.

---

## 🌟 Key Features

## Main Features

### 1. Dashboard
- Shows total, open, in-progress, and resolved incidents.
- Displays recent incidents.
- Shows incident priority and category summaries.

### 2. Ticket Management
- Create tickets with title, description, priority, and category.
- Search and filter tickets.
- Move tickets through Open, In Progress, Resolved, and Closed.
- Add root cause and resolution details.

### 3. AI Incident Analysis
- Analyze incidents using Google Gemini.
- Generates a short summary, possible root cause, and suggested solution.
- Recommends the appropriate priority and category.
- Allows AI-generated solutions to be copied into the resolution notes.

### 4. Knowledge Base
- Includes support guides for common technical issues.
- Shows relevant guides based on the incident.
- Allows engineers to view and copy troubleshooting steps.

### 5. Data Storage
- Uses SQLite to store incidents and knowledge-base data.
- Data remains available after refreshing or restarting the application.
- Includes sample incidents and support guides.

### 6. Curated Seed Datasets & Evaluation Harness (Phase 0)
- **Dataset Notice:** The seed datasets and evaluation golden sets are **synthetic, production-style curated IT helpdesk datasets** designed for benchmarking retrieval precision and LLM incident resolution.
- **`data/seed/kb_articles.jsonl`**: 40 canonical technical runbooks covering 8 key categories (`network`, `email`, `VPN and access`, `hardware`, `software installation`, `account and password`, `database`, `performance`).
- **`data/seed/tickets.jsonl`**: 300 realistic historical incident tickets with verified resolutions and category mappings.
- **`eval/golden_set.jsonl`**: 60 held-out evaluation tickets strictly excluded from the searchable index to avoid benchmark contamination.
- **Regenerate Seed Datasets:**
  ```bash
  python scripts/generate_seed_data.py --seed 42
  ```
- **Load Seed Datasets:**
  ```bash
  python scripts/load_seed.py --db-type sqlite
  ```
- **Run Dataset Unit Tests:**
  ```bash
  python -m pytest tests/test_seed_data.py -v
  ```

## 🚀 Quick Start Guide

### Prerequisites
- [Node.js](https://nodejs.org/) (v18+ or v20+ / v22+ recommended)
- `npm` (bundled with Node.js)

### 1. Install Dependencies
```bash
npm install
```

### 2. Configure AI API Key (Optional)
Copy the example environment file:
```bash
cp .env.example .env.local
```

Edit `.env.local` and add your **Google Gemini API Key**:
```env
GEMINI_API_KEY=your_google_gemini_api_key_here
```
> 💡 *Note: If no API key is provided, the application automatically uses an intelligent built-in heuristic diagnostic engine matching HuggingFace help-desk datasets, so the application remains 100% functional out-of-the-box.*

### 3. Run the Development Server
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### 4. Production Build & Test
```bash
npm run build
npm run start
```

## 🧠 Phase 2: Hybrid Retrieval (Hybrid RAG) Architecture

The DigiPlus AI Service Desk implements a state-of-the-art **Hybrid RAG** retrieval pipeline combining dense vector embeddings, sparse full-text search, Reciprocal Rank Fusion (RRF), and Gemini neural reranking.

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

### 1. Knowledge Base Chunking Strategy
- **Chunk Size:** 300–500 tokens (~1200–2000 characters) preserving paragraph, line, and markdown sentence boundaries.
- **Overlap:** 50–100 tokens (~200–400 characters) to maintain continuity across boundary cuts.
- **Context Grounding:** Every chunk prepends a header `[{category}] {title}` to preserve contextual semantics during embedding generation.
- **Idempotency:** Short runbooks fitting within the target size are kept intact as a single chunk without unnecessary splitting.

### 2. Embedding Model & Vector Similarity
- **Model:** `gemini-embedding-001` via the official Google GenAI SDK.
- **Dimensions:** Pinned to `EMBED_DIM=768` (`output_dimensionality=768`), matching the PostgreSQL `vector(768)` column.
- **Vector Index:** PostgreSQL pgvector index using HNSW with cosine distance (`<=>`).
- **Cosine Similarity:** Calculated as `1.0 - (c.embedding <=> query_vector::vector)`.

### 3. PostgreSQL Full-Text Search
- **Column:** Generated `tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED`.
- **Index:** Inverted GIN index `kb_chunks_tsv_idx ON kb_chunks USING gin (tsv)`.
- **Ranking:** `ts_rank_cd(c.tsv, query)` using `plainto_tsquery('english', query)` with substring ILIKE fallback for punctuation-heavy strings.

### 4. Reciprocal Rank Fusion (RRF)
RRF merges disparate score distributions from dense vector search and sparse full-text search without requiring score calibration:
$$\text{RRF\_Score}(d) = \sum_{m \in \{\text{vector}, \text{text}\}} \frac{1.0}{k + \text{rank}_m(d)}$$
- **Default Smoothing Constant:** $k = 60$.
- **Deduplication:** Automatic deduplication by `chunk_id` while merging ranking metadata.

### 5. Gemini Neural Reranking
- **Model:** `gemini-3.5-flash-lite` (with automatic fallback to `gemini-3.1-flash-lite`).
- **Input:** Query + Top 20 RRF candidate chunks.
- **Output:** Structured JSON ranking with relevance scores (0.0 to 1.0) and technical reasoning.
- **Strict Safeguards:** 
  - Validates all returned `chunk_id`s against the candidate pool; strictly drops hallucinated IDs.
  - Automatically falls back to RRF ranking if Gemini response is malformed, rate-limited, or unavailable.

### 6. Feature Flags

Configured in `.env.local` or environment variables:

| `USE_HYBRID` | `USE_RERANK` | Active Retrieval Pipeline |
|---|---|---|
| `false` | `false` | Basic PostgreSQL full-text keyword retrieval |
| `true` | `false` | Dense vector + sparse full-text search fused with RRF |
| `true` | `true` | Hybrid search + RRF + Gemini neural reranking (default) |

### 7. How to Index and Re-Index Knowledge Base Articles

Run the reusable indexing CLI script:
```bash
python scripts/index_kb.py --batch-size 10
```
Or trigger via the FastAPI AI service endpoint:
```bash
curl -X POST http://127.0.0.1:8000/index -H "Content-Type: application/json" -d '{"reindex_all": true}'
```

### 8. Running the Complete Test Suite

```bash
# 1. Run all Python unit and integration tests (Chunking, RAG, API, Seed data):
$env:PYTHONPATH="ai-service"; python -m pytest ai-service/tests/ tests/test_seed_data.py -v

# 2. Run TypeScript strict type-check:
npx tsc --noEmit

# 3. Run full-stack End-to-End verification:
node test-e2e.mjs
```

---

## 🧪 Automated End-to-End Testing

To run the automated verification script testing the entire incident lifecycle (Ticket Creation ➡️ AI Analysis ➡️ Runbook Matching ➡️ Resolution ➡️ Dashboard Stats):

```bash
node test-e2e.mjs
```

---

