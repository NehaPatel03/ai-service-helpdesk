-- ==============================================================================
-- DigiPlus AI Service Desk: Phase 3 Agent Execution & Memory Migration
-- Migration: 002_agent_phase3_schema.sql
-- ==============================================================================

-- 1. Extend agent_runs table for complete execution telemetry
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'success';
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS steps_count INT DEFAULT 1;
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS used_fallback BOOLEAN DEFAULT false;
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS grounding_valid BOOLEAN DEFAULT true;
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS grounding_details JSONB DEFAULT '{}'::jsonb;

-- 2. Extend tickets table with conversation memory summary
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS conversation_summary TEXT;

-- 3. Indexes for observability queries
CREATE INDEX IF NOT EXISTS idx_agent_runs_status ON agent_runs(status);
CREATE INDEX IF NOT EXISTS idx_agent_runs_grounding_valid ON agent_runs(grounding_valid);
