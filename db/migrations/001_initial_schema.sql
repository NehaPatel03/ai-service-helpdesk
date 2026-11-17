-- ==============================================================================
-- DigiPlus AI Service Desk: PostgreSQL + pgvector Initial Schema Migration
-- Migration: 001_initial_schema.sql
-- ==============================================================================

-- 1. Enable pgvector extension for dense vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Knowledge Base Articles
CREATE TABLE IF NOT EXISTS kb_articles (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    category TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_kb_articles_category ON kb_articles(category);

-- 3. Knowledge Base Chunks (Hybrid Search: Dense Vector + Sparse Full-Text)
-- EMBED_DIM is strictly pinned to 768 to match Gemini text-embedding-004
CREATE TABLE IF NOT EXISTS kb_chunks (
    id SERIAL PRIMARY KEY,
    article_id INT NOT NULL REFERENCES kb_articles(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768),
    tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Fast HNSW cosine distance vector index
CREATE INDEX IF NOT EXISTS kb_chunks_embedding_idx ON kb_chunks USING hnsw (embedding vector_cosine_ops);

-- GIN inverted index for PostgreSQL full-text search
CREATE INDEX IF NOT EXISTS kb_chunks_tsv_idx ON kb_chunks USING gin (tsv);

CREATE INDEX IF NOT EXISTS idx_kb_chunks_article_id ON kb_chunks(article_id);

-- 4. Incident Tickets (Extended from existing SQLite schema)
CREATE TABLE IF NOT EXISTS tickets (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'Other',
    priority TEXT NOT NULL DEFAULT 'Medium',
    status TEXT NOT NULL DEFAULT 'Open',
    resolution TEXT,
    source TEXT DEFAULT 'manual',
    external_id TEXT,
    ai_summary TEXT,
    ai_cause TEXT,
    ai_solution TEXT,
    ai_suggested_category TEXT,
    ai_suggested_priority TEXT,
    embedding vector(768),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_priority ON tickets(priority);
CREATE INDEX IF NOT EXISTS idx_tickets_category ON tickets(category);
CREATE INDEX IF NOT EXISTS idx_tickets_external_id ON tickets(external_id);

-- Optional HNSW index on ticket embeddings for similar incident retrieval
CREATE INDEX IF NOT EXISTS tickets_embedding_idx ON tickets USING hnsw (embedding vector_cosine_ops);

-- 5. Agent Execution Runs (Audit, Observability, and Evaluation Logs)
CREATE TABLE IF NOT EXISTS agent_runs (
    id SERIAL PRIMARY KEY,
    ticket_id INT REFERENCES tickets(id) ON DELETE SET NULL,
    input TEXT NOT NULL,
    tool_calls JSONB DEFAULT '[]'::jsonb,
    output JSONB,
    latency_ms INT,
    tokens_in INT,
    tokens_out INT,
    valid_schema BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_ticket_id ON agent_runs(ticket_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_valid_schema ON agent_runs(valid_schema);

-- 6. User Feedback (Quality and Reinforcement Tracking)
CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    agent_run_id INT REFERENCES agent_runs(id) ON DELETE CASCADE,
    helpful BOOLEAN NOT NULL,
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_feedback_agent_run_id ON feedback(agent_run_id);
