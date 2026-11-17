"""
Agent Execution Logging and Observability Module.

Logs execution traces, tool calls, latencies, tokens, and grounding metrics to PostgreSQL.
"""

import json
import logging
from typing import Any, Dict, Optional

from app.agent.schemas import AgentExecutionTrace
from app.db.connection import get_db_connection

logger = logging.getLogger(__name__)


def log_agent_run(trace: AgentExecutionTrace, input_details: Dict[str, Any]) -> Optional[int]:
    """
    Persists an agent execution run record into the PostgreSQL `agent_runs` table.

    Args:
        trace: AgentExecutionTrace containing telemetry, tool calls, and grounding outcomes.
        input_details: Dictionary containing input ticket details.

    Returns:
        Integer run ID if persisted successfully, None otherwise.
    """
    conn = get_db_connection()
    if conn is None:
        logger.warning("Database unavailable, skipping agent run persistence")
        return None

    try:
        # Sanitize tool calls for JSON serialization
        serialized_tool_calls = []
        for call in trace.tool_calls:
            serialized_tool_calls.append({
                "step": call.step,
                "tool_name": call.tool_name,
                "args": call.args,
                "result": call.result,
                "latency_ms": call.latency_ms,
                "error": call.error,
            })

        # Sanitize final analysis output
        output_data = trace.final_analysis.model_dump() if trace.final_analysis else None

        grounding_data = {
            "is_valid": trace.grounding.is_valid,
            "grounded_ticket_ids": trace.grounding.grounded_ticket_ids,
            "unsupported_ticket_ids": trace.grounding.unsupported_ticket_ids,
            "grounded_kb_ids": trace.grounding.grounded_kb_ids,
            "unsupported_kb_ids": trace.grounding.unsupported_kb_ids,
        }

        # Ensure no sensitive tokens or keys are captured
        safe_input = {
            "id": input_details.get("id"),
            "title": input_details.get("title"),
            "category": input_details.get("category"),
            "priority": input_details.get("priority"),
            "description": input_details.get("description", "")[:500],
        }

        with conn.cursor() as cur:
            # Verify ticket exists to respect foreign key constraint
            db_ticket_id = None
            if trace.ticket_id:
                cur.execute("SELECT 1 FROM tickets WHERE id = %s;", (trace.ticket_id,))
                if cur.fetchone():
                    db_ticket_id = trace.ticket_id

            cur.execute("""
                INSERT INTO agent_runs (
                    ticket_id,
                    input,
                    tool_calls,
                    output,
                    latency_ms,
                    tokens_in,
                    tokens_out,
                    valid_schema,
                    status,
                    steps_count,
                    used_fallback,
                    grounding_valid,
                    grounding_details
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) RETURNING id;
            """, (
                db_ticket_id,
                json.dumps(safe_input),
                json.dumps(serialized_tool_calls),
                json.dumps(output_data) if output_data else None,
                trace.latency_ms,
                trace.tokens_in,
                trace.tokens_out,
                trace.valid_schema,
                trace.status,
                trace.steps_count,
                trace.used_fallback,
                trace.grounding.is_valid,
                json.dumps(grounding_data),
            ))
            run_id = cur.fetchone()[0]
        conn.commit()
        logger.info("Persisted agent_runs record #%d for ticket #%d", run_id, trace.ticket_id)
        return run_id
    except Exception as e:
        conn.rollback()
        logger.error("Failed to persist agent run for ticket #%d: %s", trace.ticket_id, e)
        return None
    finally:
        conn.close()
