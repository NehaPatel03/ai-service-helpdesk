# DigiPlus AI-Powered Service Desk 🤖🎫

[![Next.js](https://img.shields.io/badge/Next.js-16.0-black?style=flat&logo=next.js)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19.0-blue?style=flat&logo=react)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18.7-336791?style=flat&logo=postgresql)](https://www.postgresql.org/)
[![pgvector](https://img.shields.io/badge/pgvector-0.8.7-336791?style=flat)](https://github.com/pgvector/pgvector)
[![Google Gemini](https://img.shields.io/badge/Google_Gemini-3.5_Flash_Lite-4285F4?style=flat&logo=google)](https://ai.google.dev/)
[![Tests](https://img.shields.io/badge/Tests-62%2F62_Passing-brightgreen?style=flat)](file:///d:/ai-service-desk/digiplus-ai-service-desk/ai-service/tests)
[![TypeScript](https://img.shields.io/badge/TypeScript-Strict_Mode-blue?style=flat&logo=typescript)](https://www.typescriptlang.org/)

**DigiPlus AI-Powered Service Desk** is a full-stack, enterprise-grade IT Service Management (ITSM) and automated incident remediation platform. Engineered for IT Support Engineers, SREs, and Helpdesk teams, DigiPlus streamlines the entire incident resolution lifecycle—from natural language ticket ingestion and automated triage to AI-powered root-cause diagnosis, contextual runbook retrieval via **Hybrid RAG**, and an autonomous **Tool-Using AI Agent** with verified structured outputs.

Powered by a modern full-stack architecture featuring **Next.js 16 (App Router, React 19)**, a high-performance **FastAPI AI Microservice**, **Neon Serverless PostgreSQL with `pgvector`**, and **Google Gemini (Generative AI, Function Calling & Dense Embeddings)**.

---

## 📑 Table of Contents
- [Executive Overview & Purpose](#-executive-overview--purpose)
- [Comprehensive Feature Suite](#-comprehensive-feature-suite)
  - [1. Executive Analytics & Incident Dashboard](#1-executive-analytics--incident-dashboard)
  - [2. End-to-End Ticket Lifecycle Management](#2-end-to-end-ticket-lifecycle-management)
  - [3. Autonomous Tool-Using AI Agent (Phase 3)](#3-autonomous-tool-using-ai-agent-phase-3)
  - [4. Interactive Incident Chat Assistant (AI Copilot)](#4-interactive-incident-chat-assistant-ai-copilot)
  - [5. Historical Similar Incident Detection](#5-historical-similar-incident-detection)
  - [6. Technical Knowledge Base & Runbook Repository](#6-technical-knowledge-base--runbook-repository)
  - [7. Production Hybrid Retrieval Engine (Hybrid RAG)](#7-production-hybrid-retrieval-engine-hybrid-rag)
  - [8. Synthetic Dataset Benchmarking & Bulk Ingestion](#8-synthetic-dataset-benchmarking--bulk-ingestion)
  - [9. High Availability, Fault Tolerance & DNS Resilience](#9-high-availability-fault-tolerance--dns-resilience)
- [System Architecture](#-system-architecture)
- [Project Directory Layout](#-project-directory-layout)
- [Phase 3 Agent Deep-Dive](#-phase-3-agent-deep-dive)
  - [Agent Execution Flow](#agent-execution-flow)
  - [Diagnostic Tools Suite](#diagnostic-tools-suite)
  - [Pydantic Structured Output](#pydantic-structured-output)
  - [Grounding Verification System](#grounding-verification-system)
  - [Persistent Conversation Memory](#persistent-conversation-memory)
  - [PostgreSQL Telemetry & Logging](#postgresql-telemetry--logging)
- [End-to-End User Workflows](#-end-to-end-user-workflows)
- [Database Schema & Migrations](#-database-schema--migrations)
- [API Endpoints Reference](#-api-endpoints-reference)
- [Environment Configuration](#-environment-configuration)
- [Step-by-Step Setup & Execution](#-step-by-step-setup--execution)
- [Automated Testing & Quality Verification](#-automated-testing--quality-verification)
- [Implementation Progress (Phases 0–3)](#-implementation-progress-phases-03)
- [Upcoming Roadmap (Phase 4)](#-upcoming-roadmap-phase-4)
- [Security & Best Practices](#-security--best-practices)

---

## 🎯 Executive Overview & Purpose

Modern IT operations face high ticket volumes, fragmented documentation, and prolonged Mean Time to Resolution (MTTR). Support engineers often spend critical minutes manually categorizing tickets, searching through stale documentation, or re-solving problems that were already resolved in prior incidents.

**DigiPlus AI Service Desk** solves this by uniting automated triage, dense semantic search, autonomous agent investigation, and generative AI:
- **Reduces MTTR:** Generates instant root-cause diagnostics and step-by-step remediation checklists within seconds of ticket submission.
- **Autonomous Multi-Step Agent:** Deploys a Gemini function-calling agent that actively searches runbooks, investigates similar historical incidents, retrieves ticket audit histories, and suggests team assignments.
- **Eliminates Hallucinations via Strict Grounding:** Validates cited runbook IDs and ticket IDs against actual tool outputs before delivering responses.
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

### 3. Autonomous Tool-Using AI Agent (Phase 3)
- **Multi-Turn Reasoning Loop:** Driven by Google Gemini (`gemini-3.5-flash-lite`), the agent actively inspects incident details and chooses the optimal diagnostic tools.
- **4 Native Investigation Tools:**
  1. `search_similar_tickets`: Discovers related historical incidents and prior resolutions.
  2. `search_kb`: Queries canonical runbooks using Phase 2 Hybrid RAG (pgvector + tsvector + RRF).
  3. `get_ticket_history`: Retrieves audit history, prior agent runs, and status records.
  4. `suggest_assignee`: Recommends the responsible engineering team based on category mappings.
- **Pydantic Structured Output:** Enforces strict validation of root cause, confidence levels, remediation steps, and cited references.
- **One-Retry Schema Recovery:** Automatically passes validation errors back to Gemini for self-correction if an output is malformed.
- **Grounding Verification:** Enforces that cited ticket and runbook IDs were genuinely returned by tool executions during that specific run.
- **Persistent Conversation Memory:** Maintains a rolling summary per ticket in PostgreSQL to preserve context across repeated analyses.
- **Full Observability Logging:** Records every tool call, argument, execution latency, token counts, schema status, and grounding outcome into `agent_runs`.

### 4. Interactive Incident Chat Assistant (AI Copilot)
- **Contextual In-Ticket Copilot:** Embedded drawer directly inside the incident workspace that understands the current ticket's title, description, category, and priority.
- **Multi-Turn Interactive Dialogue:** Support engineers can converse with the AI copilot to ask follow-up questions, simplify technical explanations, or request alternative steps.
- **Quick-Prompt Suggestions:** One-click pre-composed prompts to accelerate triage.
- **Persistent Chat History:** Chat messages are saved per ticket and restored upon subsequent visits.

### 5. Historical Similar Incident Detection
- **Semantic & TF-IDF Incident Matching:** Analyzes the incident title and description against historical incidents using high-dimensional TF-IDF vectors and bigram contextual awareness.
- **Relevance Scoring:** Computes mathematical similarity percentages (e.g., `92% Match`).
- **Prior Resolution Reuse:** Displays the exact resolution text applied to previous incidents so engineers can resolve recurring issues in seconds.

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

### 8. Synthetic Dataset Benchmarking & Bulk Ingestion
- **Automated Seed Generator (`scripts/generate_seed_data.py`):** Generates reproducible, realistic IT helpdesk datasets with deterministic random seeds.
- **40 Canonical Technical Runbooks (`data/seed/kb_articles.jsonl`):** Deep troubleshooting procedures covering VPN gateways, Kubernetes pods, database replication lag, disk full errors, OAuth SSO loops, and more.
- **300 Historical Incident Tickets (`data/seed/tickets.jsonl`):** Diverse tickets with realistic timestamps, priority distributions, and verified resolutions.
- **60 Held-Out Golden Benchmark Tickets (`eval/golden_set.jsonl`):** Strictly isolated from the searchable knowledge base to enable clean, uncontaminated offline evaluation.

### 9. High Availability, Fault Tolerance & DNS Resilience
- **Dual Database Architecture:**
  - **Neon PostgreSQL (Active Production):** Serverless, scalable cloud database with `pgvector` 0.8.7.
  - **SQLite Backup (`data/support_desk.db.backup`):** Byte-for-byte preserved snapshot of the original system.
- **ISP DNS Resilience:** Restrictive local ISP routers frequently fail to resolve `*.neon.tech` subdomains. Both the Python microservice (`dnspython`) and Node.js (`dns.Resolver`) feature built-in programmatic fallback to public resolvers (`8.8.8.8`, `1.1.1.1`) with TLS Server Name Indication (`SNI`), eliminating connection dropouts.

---

## 🏗️ System Architecture

```
                                  +---------------------------------------+
                                  |     Next.js 16 Full-Stack Web App     |
                                  |     (React 19, TypeScript, Tailwind)  |
                                  +--------+---------------------+--------+
                                           |                     |
                               Next.js API |                     | Fast REST Calls
                                  Routes   |                     | (60s resilient timeout)
                                           v                     v
                        +--------------------+        +----------------------+
                        |  Neon PostgreSQL   |        |  FastAPI AI Service  |
                        |  - tickets         |        |  - Health: /health   |
                        |  - kb_articles     |        |  - Analyze: /analyze |
                        |  - kb_chunks       |        |  - Search: /search   |
                        |  - agent_runs      |        |  - Index: /index     |
                        |  - pgvector (768d) |        +----------+-----------+
                        |  - GIN tsvector    |                   |
                        +--------------------+                   | google-genai SDK
                                                                 v
                                                      +----------------------+
                                                      |  Google Gemini API   |
                                                      |  - gemini-3.5-flash-lite
                                                      |  - Function Calling  |
                                                      |  - gemini-embedding-001
                                                      +----------------------+
```

---

## 🤖 Phase 3 Agent Deep-Dive

### Agent Execution Flow

```
                                   +-------------------------+
                                   | Incident Ticket Details |
                                   +------------+------------+
                                                |
                                                v
                              +------------------------------------+
                              | Load Memory & Construct Context    |
                              | - Rolling Summary from PostgreSQL  |
                              | - System Prompt & Tool Declarations|
                              +-----------------+------------------+
                                                |
                                                v
                     +------------------------->+
                     |                          |
                     |                          v
                     |             +-------------------------+
                     |             | Google Gemini Reasoning |
                     |             +------------+------------+
                     |                          |
                     |              Tool Call?  |  Final Output?
                     |             +------------+------------+
                     |             |                         |
                     |             v                         v
                     |    +------------------+     +--------------------+
                     |    | Execute Tool     |     | Validate Pydantic  |
                     |    | - search_kb      |     | Analysis Schema    |
                     |    | - similar_tickets|     +---------+----------+
                     |    | - ticket_history |               |
                     |    | - suggest_assign |      Valid?   | Invalid?
                     |    +--------+---------+     +---------+----------+
                     |             |               |                    |
                     |             v               v                    v
                     |     [Part (role=user)]   [Success]      +------------------+
                     |             |               |           | Retry Prompt (1x)|
                     +-------------+               |           +--------+---------+
                                                   |                    |
                                                   v                    v
                                     +---------------------------+  [Recovered]
                                     | Grounding Verification    |
                                     | - Check kb_sources        |
                                     | - Check related_ticket_ids|
                                     +-------------+-------------+
                                                   |
                                                   v
                                     +---------------------------+
                                     | Persist to PostgreSQL     |
                                     | - Update conversation_sum |
                                     | - Log trace to agent_runs |
                                     +-------------+-------------+
                                                   |
                                                   v
                                     [Return Validated Analysis]
```

### Diagnostic Tools Suite

| Tool | Parameters | Purpose | Implementation Source |
|---|---|---|---|
| `search_similar_tickets` | `query: str`, `category: str \| None` | Searches historical resolved tickets in PostgreSQL using pgvector cosine distance and text fallback | [`ai-service/app/agent/tools.py`](file:///d:/ai-service-desk/digiplus-ai-service-desk/ai-service/app/agent/tools.py#L90) |
| `search_kb` | `query: str`, `category: str \| None` | Searches knowledge base runbooks using Phase 2 Hybrid RAG (pgvector + tsvector + RRF + reranking) | [`ai-service/app/agent/tools.py`](file:///d:/ai-service-desk/digiplus-ai-service-desk/ai-service/app/agent/tools.py#L170) |
| `get_ticket_history` | `ticket_id: int` | Retrieves audit history, previous analysis summaries, and prior agent execution runs | [`ai-service/app/agent/tools.py`](file:///d:/ai-service-desk/digiplus-ai-service-desk/ai-service/app/agent/tools.py#L210) |
| `suggest_assignee` | `category: str` | Recommends the responsible engineering team, operational tier, and escalation contact | [`ai-service/app/agent/tools.py`](file:///d:/ai-service-desk/digiplus-ai-service-desk/ai-service/app/agent/tools.py#L275) |

### Pydantic Structured Output

The agent strictly validates the final model response against the Pydantic `Analysis` model:

```python
class Analysis(BaseModel):
    root_cause: str = Field(..., description="Identified or suspected technical root cause")
    confidence: Literal["low", "medium", "high"] = Field(..., description="Confidence assessment")
    suggested_steps: List[str] = Field(default_factory=list, description="Ordered remediation steps")
    related_ticket_ids: List[int] = Field(default_factory=list, description="IDs of historical incidents cited")
    kb_sources: List[int] = Field(default_factory=list, description="IDs of runbook articles cited")
```

If validation fails, the agent sends the exact validation error back to Gemini in a retry turn. If the retry also fails, it returns a safe fallback and records `valid_schema: false`.

### Grounding Verification System

To prevent hallucinated ticket or runbook IDs:
1. All IDs returned by tool calls during the run are extracted into `grounded_ticket_ids` and `grounded_kb_ids`.
2. The model's `related_ticket_ids` and `kb_sources` are verified against these sets.
3. Unsupported IDs are flagged, removed via `sanitize_grounded_analysis()`, and recorded in `agent_runs.grounding_details`.

### Persistent Conversation Memory

- Each ticket maintains a concise rolling summary in the `tickets.conversation_summary` column.
- When an incident is re-analyzed, prior investigation findings are automatically loaded into the agent's context.
- Upon successful agent completion, the rolling summary is updated with the latest diagnostic points (capped at 500 characters to prevent token bloat).

### PostgreSQL Telemetry & Logging

Every execution is committed to the `agent_runs` table:
- `ticket_id`: Foreign key to `tickets` (or `NULL` if ad-hoc)
- `input`: Sanitized JSON of ticket title, category, priority, and description
- `tool_calls`: JSONB list of tool names, arguments, execution latencies, and returned results
- `output`: JSONB of the final `Analysis`
- `latency_ms`: Total execution time in milliseconds
- `tokens_in` / `tokens_out`: Prompt and candidate token usage
- `valid_schema`: Boolean flag recording Pydantic compliance
- `grounding_valid`: Boolean flag recording grounding verification
- `grounding_details`: JSONB breakdown of grounded vs unsupported IDs
- `steps_count`: Total reasoning turns executed (max 5)
- `status`: Execution outcome (`success`, `max_steps_reached`, `api_error`, `validation_failed`, `fallback`)
- `used_fallback`: Boolean indicating whether heuristic fallback was invoked

---

## 📂 Project Directory Layout

```
digiplus-ai-service-desk/
├── ai-service/                         # Python FastAPI AI Microservice
│   ├── app/
│   │   ├── agent/                      # Phase 3 Tool-Using Agent Package
│   │   │   ├── prompts/
│   │   │   │   ├── system.txt          # Agent system instructions & grounding rules
│   │   │   │   └── retry.txt           # Schema validation retry template
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                # Multi-step Gemini agent loop (max 5 steps)
│   │   │   ├── grounding.py            # Reference validation & ID sanitization
│   │   │   ├── logger.py               # PostgreSQL agent_runs telemetry logger
│   │   │   ├── memory.py               # Persistent rolling summary memory manager
│   │   │   ├── schemas.py              # Pydantic Analysis & telemetry models
│   │   │   └── tools.py                # 4 Diagnostic tools for Gemini function calling
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
│   │   └── schemas.py                  # API request/response models (preserving legacy + Phase 3)
│   ├── tests/
│   │   ├── test_agent_grounding.py     # Grounding verification unit tests
│   │   ├── test_agent_loop.py          # Multi-step agent loop & retry unit tests
│   │   ├── test_agent_memory.py        # Persistent conversation memory unit tests
│   │   ├── test_agent_tools.py         # 4 Diagnostic tools unit tests
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
│       ├── 001_initial_schema.sql      # PostgreSQL DDL (pgvector, tickets, kb_articles, kb_chunks)
│       └── 002_agent_phase3_schema.sql # Phase 3 DDL (agent_runs telemetry, conversation_summary)
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
│   │   │   ├── ai/
│   │   │   │   ├── analyze/            # Ticket AI analysis proxy to FastAPI agent
│   │   │   │   └── chat/               # Ticket AI assistant chat endpoint
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

### Workflow 2: Investigating with the Autonomous AI Agent
1. Open the newly created ticket from the dashboard or ticket list.
2. Click **"Analyze with AI 🤖"**.
3. Next.js triggers `POST /api/ai/analyze`, which calls FastAPI `POST /analyze-ticket`.
4. The Phase 3 Gemini Agent initializes, loads any prior ticket conversation memory, and begins tool investigation:
   - Queries `search_kb` for matching runbooks.
   - Queries `search_similar_tickets` for past resolution patterns.
   - Queries `get_ticket_history` to verify prior updates.
   - Queries `suggest_assignee` for engineering team escalation.
5. Gemini synthesizes the findings and outputs the structured `Analysis` JSON.
6. The Grounding Verification engine validates cited runbook IDs and ticket IDs.
7. Telemetry is saved to `agent_runs` and rolling memory is updated on the ticket.
8. The UI renders root causes, actionable steps with copy buttons, and verified runbook citations.

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

## 🗄️ Database Schema & Migrations

### Migrations List
- [`db/migrations/001_initial_schema.sql`](file:///d:/ai-service-desk/digiplus-ai-service-desk/db/migrations/001_initial_schema.sql): Initial schema with `vector(768)` extension, `tickets`, `kb_articles`, `kb_chunks`, and base `agent_runs`.
- [`db/migrations/002_agent_phase3_schema.sql`](file:///d:/ai-service-desk/digiplus-ai-service-desk/db/migrations/002_agent_phase3_schema.sql): Phase 3 schema extensions adding `status`, `steps_count`, `used_fallback`, `grounding_valid`, and `grounding_details` to `agent_runs`, plus `conversation_summary` to `tickets`.

### Applying Migrations
```bash
# Connect to Neon and execute migration 002
psql "$DATABASE_URL" -f db/migrations/002_agent_phase3_schema.sql
```

---

## 📡 API Endpoints Reference

### AI Microservice (Port 8000)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Healthcheck verifying PostgreSQL, `pgvector`, and Gemini models |
| `GET` | `/search` | Executes Hybrid RAG search (`?q=...&category=...&limit=...`) |
| `POST` | `/analyze-ticket` | Executes Phase 3 Tool-Using AI Agent investigation and returns structured Analysis |
| `POST` | `/index` | Triggers re-chunking and re-embedding of all knowledge base articles |

#### Sample Request: `POST /analyze-ticket`
```json
{
  "ticket": {
    "id": 1,
    "title": "PostgreSQL RDS connection pool exhausted during peak billing batch",
    "description": "During the 2AM billing job, clients receive 500 Internal Server Error. Active connections reached 100/100 limit. RDS CPU at 95%.",
    "category": "database",
    "priority": "Urgent"
  }
}
```

#### Sample Response: `POST /analyze-ticket`
```json
{
  "summary": "Incident Analysis: PostgreSQL RDS connection pool is exhausted (reaching the 100/100 limit) and CPU utilization is at 95%...",
  "suggestedCategory": "database",
  "suggestedPriority": "Urgent",
  "possibleCause": "PostgreSQL RDS connection pool is exhausted (reaching the 100/100 limit) and CPU utilization is at 95% due to peak billing batch processing holding active connections and long-running queries.",
  "suggestedSolution": "1. Inspect active connections using: SELECT count(*), state FROM pg_stat_activity GROUP BY state;\n2. Identify long-running or locked queries using: SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state FROM pg_stat_activity WHERE state != 'idle' ORDER BY 2 DESC LIMIT 10;\n3. Terminate runaway zombie connections or queries using: SELECT pg_terminate_backend(PID); and tune PgBouncer connection pool limits.",
  "relevantArticleIds": [3],
  "keyTroubleshootingSteps": [
    "1. Inspect active connections using: SELECT count(*), state FROM pg_stat_activity GROUP BY state;",
    "2. Identify long-running or locked queries using: SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state FROM pg_stat_activity WHERE state != 'idle' ORDER BY 2 DESC LIMIT 10;",
    "3. Terminate runaway zombie connections or queries using: SELECT pg_terminate_backend(PID); and tune PgBouncer connection pool limits."
  ],
  "confidence": "high",
  "engine": "gemini_agent",
  "root_cause": "PostgreSQL RDS connection pool is exhausted...",
  "suggested_steps": [
    "Inspect active connections",
    "Identify long-running queries",
    "Terminate runaway queries and tune PgBouncer"
  ],
  "related_ticket_ids": [],
  "kb_sources": [3],
  "steps_count": 3,
  "grounding_valid": true
}
```

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

### 3. Apply Phase 3 Database Migration
```bash
python -c "
import psycopg2, os
from dotenv import load_dotenv
load_dotenv('.env.local')
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
with open('db/migrations/002_agent_phase3_schema.sql') as f:
    conn.cursor().execute(f.read())
conn.commit()
print('Migration 002 applied!')
"
```

### 4. Run Knowledge Base Indexing
Chunk, embed, and index all runbooks into Neon `pgvector`:
```bash
python scripts/index_kb.py
```

### 5. Start the Application Servers
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

DigiPlus includes an extensive automated test suite covering unit logic, agent loops, grounding verification, conversation memory, RAG pipelines, API contracts, TypeScript types, and end-to-end incident workflows:

```bash
# 1. Run all 62 Python unit and integration tests:
$env:PYTHONPATH="ai-service"; python -m pytest ai-service/tests/ tests/test_seed_data.py -v

# 2. Run TypeScript strict type-check:
npx tsc --noEmit

# 3. Run full-stack End-to-End incident lifecycle verification (all 11 suites):
node test-e2e.mjs
```

### Test Suite Breakdown (**62 / 62 Tests Passing**):
- **`ai-service/tests/test_agent_tools.py` (9 tests):** Tool argument validation, known/unknown category assignee mapping, empty query handling, and ticket history retrieval.
- **`ai-service/tests/test_agent_grounding.py` (6 tests):** Valid references, invented KB article IDs, invented ticket IDs, empty tool results, and mixed valid/invalid citation filtering.
- **`ai-service/tests/test_agent_memory.py` (4 tests):** First analysis summary creation, multi-turn rolling summary composition, PostgreSQL memory persistence, and non-existent ticket handling.
- **`ai-service/tests/test_agent_loop.py` (8 tests):** Single/multiple tool execution, invalid tool handling, max 5-step limit protection, API failure fallback, Pydantic validation retry recovery, and telemetry tracking.
- **`ai-service/tests/test_api.py` (8 tests):** FastAPI `/health`, `/analyze-ticket`, `/search`, `/index` schema conformity and input validation.
- **`ai-service/tests/test_chunker.py` (6 tests):** Short/long article splitting, context overlap, duplicate prevention, and metadata preservation.
- **`ai-service/tests/test_rag.py` (12 tests):** RRF formula accuracy, embedding dimension checks, reranker hallucination drop guards, fallback mechanisms, and feature flag routing.
- **`tests/test_seed_data.py` (9 tests):** Seed datasets, schema coverage, category coverage, and golden set benchmark isolation.
- **`test-e2e.mjs` (11 suites):** End-to-end verification of ticket creation, Phase 3 AI analysis, runbook matching, ticket resolution, dataset batch import, semantic duplicate detection, conversational AI assistant, and dashboard recalculation.

---

## 📈 Implementation Progress (Phases 0–3)

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

### Phase 3: Tool-Using AI Agent with Structured Output ✅
- Built multi-step autonomous agent loop (`ai-service/app/agent/agent.py`) with max 5 steps protection.
- Exposed 4 Gemini function-calling tools (`search_similar_tickets`, `search_kb`, `get_ticket_history`, `suggest_assignee`).
- Enforced Pydantic `Analysis` structured output schema with automatic 1-retry self-correction.
- Implemented grounding verification engine filtering ungrounded KB article and ticket citations.
- Built persistent rolling conversation memory in Neon PostgreSQL (`conversation_summary` on `tickets`).
- Created database migration `002_agent_phase3_schema.sql` and implemented telemetry logging to `agent_runs`.
- Fully integrated agent into Next.js full-stack application with 100% backwards compatibility.

---

## 🔮 Upcoming Roadmap (Phase 4)

### Phase 4: Automated Evaluation & Golden Set Benchmarking
- Automated offline evaluation pipeline evaluating 60 golden set tickets against historical incident resolutions.
- Retrieval recall metrics (Recall@K, MRR) across pure vector, pure text, and hybrid RAG.
- LLM diagnostic accuracy scoring and tool-use precision evaluation.

---

## 🔒 Security & Best Practices

- **Zero Hardcoded Secrets:** All credentials, database connection strings, and API keys are strictly loaded via `.env.local`.
- **Git Protection:** `.env*` files (except `.env.example`), `.backup` files, and database binaries are strictly ignored in `.gitignore`.
- **Hallucination Prevention:** Grounding engine strictly validates cited IDs against tool outputs; invented references are discarded.
- **Fail-Safe Heuristic Fallback:** If external AI services or quotas are unavailable, the system automatically falls back to deterministic rule-based analysis, ensuring business continuity.
- **TLS SNI & Public DNS Fallback:** Prevents network connection failures caused by local ISP DNS filtering on cloud database subdomains.
