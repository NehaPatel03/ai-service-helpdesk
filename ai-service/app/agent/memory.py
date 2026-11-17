"""
Conversation and Incident Memory Management for Tickets.

Stores and retrieves persistent rolling incident summaries in PostgreSQL.
"""

import logging
from typing import Optional
from psycopg2.extras import RealDictCursor

from app.agent.schemas import Analysis
from app.db.connection import get_db_connection

logger = logging.getLogger(__name__)

MAX_MEMORY_CHARS = 500


def get_ticket_memory(ticket_id: int) -> Optional[str]:
    """
    Retrieves the persistent conversation memory summary for a ticket from PostgreSQL.

    Args:
        ticket_id: Integer identifier of the ticket.

    Returns:
        String summary or None if no prior memory exists.
    """
    if not ticket_id or ticket_id <= 0:
        return None

    conn = get_db_connection()
    if conn is None:
        logger.warning("DB unavailable for get_ticket_memory, returning None")
        return None

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT conversation_summary, ai_summary
                FROM tickets
                WHERE id = %s;
            """, (ticket_id,))
            row = cur.fetchone()
            if row:
                summary = row.get("conversation_summary") or row.get("ai_summary")
                if summary and summary.strip():
                    return summary.strip()
            return None
    except Exception as e:
        logger.error("Error retrieving conversation memory for ticket #%d: %s", ticket_id, e)
        return None
    finally:
        conn.close()


def update_ticket_memory(ticket_id: int, summary: str) -> bool:
    """
    Persists an updated concise rolling memory summary for a ticket into PostgreSQL.

    Args:
        ticket_id: Integer identifier of the ticket.
        summary: Updated concise summary string.

    Returns:
        True if persisted successfully, False otherwise.
    """
    if not ticket_id or ticket_id <= 0 or not summary:
        return False

    trimmed_summary = summary.strip()
    if len(trimmed_summary) > MAX_MEMORY_CHARS:
        trimmed_summary = trimmed_summary[:MAX_MEMORY_CHARS - 3] + "..."

    conn = get_db_connection()
    if conn is None:
        logger.warning("DB unavailable for update_ticket_memory")
        return False

    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE tickets
                SET conversation_summary = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s;
            """, (trimmed_summary, ticket_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logger.error("Error updating conversation memory for ticket #%d: %s", ticket_id, e)
        return False
    finally:
        conn.close()


def compose_rolling_summary(previous_summary: Optional[str], current_analysis: Analysis) -> str:
    """
    Composes a concise rolling summary combining previous context with latest diagnosis.
    """
    latest_points = f"Root cause: {current_analysis.root_cause}. Key action: {current_analysis.suggested_steps[0] if current_analysis.suggested_steps else 'Pending triage'}."
    if not previous_summary or not previous_summary.strip():
        return latest_points

    combined = f"{previous_summary.strip()} | Latest: {latest_points}"
    if len(combined) > MAX_MEMORY_CHARS:
        combined = combined[-MAX_MEMORY_CHARS:]
    return combined
