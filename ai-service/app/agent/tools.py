"""
Diagnostic and Investigation Tools exposed to Google Gemini Function Calling.
"""

import logging
from typing import Any, Dict, List, Optional
from psycopg2.extras import RealDictCursor

from app.db.connection import get_db_connection
from app.rag.embeddings import embed_text
from app.rag.pipeline import retrieve_relevant_chunks

logger = logging.getLogger(__name__)

# Configurable category-to-engineering-team mapping
TEAM_MAPPINGS: Dict[str, Dict[str, str]] = {
    "network": {
        "team": "Network Operations Center (NOC)",
        "tier": "Tier 2",
        "escalation_contact": "noc-oncall@digiplus.internal",
    },
    "vpn and access": {
        "team": "Network & Remote Access Operations",
        "tier": "Tier 2",
        "escalation_contact": "vpn-admins@digiplus.internal",
    },
    "database": {
        "team": "Database Reliability Engineering (DBA)",
        "tier": "Tier 3",
        "escalation_contact": "dba-oncall@digiplus.internal",
    },
    "software": {
        "team": "Enterprise Application Support",
        "tier": "Tier 2",
        "escalation_contact": "appsupport@digiplus.internal",
    },
    "software installation": {
        "team": "Client Platform & Desktop Engineering",
        "tier": "Tier 1",
        "escalation_contact": "workstation-ops@digiplus.internal",
    },
    "hardware": {
        "team": "Field & Desktop Support",
        "tier": "Tier 1",
        "escalation_contact": "field-support@digiplus.internal",
    },
    "access & security": {
        "team": "Identity & Access Management (IAM)",
        "tier": "Tier 2",
        "escalation_contact": "secops-iam@digiplus.internal",
    },
    "account and password": {
        "team": "Identity & Access Management (IAM)",
        "tier": "Tier 1",
        "escalation_contact": "iam-triage@digiplus.internal",
    },
    "email & communication": {
        "team": "Workplace Collaboration Systems",
        "tier": "Tier 2",
        "escalation_contact": "collab-eng@digiplus.internal",
    },
    "cloud & infrastructure": {
        "team": "Cloud Infrastructure & SRE",
        "tier": "Tier 3",
        "escalation_contact": "sre-alerts@digiplus.internal",
    },
    "performance": {
        "team": "Systems Performance & Observability",
        "tier": "Tier 3",
        "escalation_contact": "perf-sre@digiplus.internal",
    },
    "billing & accounts": {
        "team": "Finance Systems Operations",
        "tier": "Tier 2",
        "escalation_contact": "erp-support@digiplus.internal",
    },
}

DEFAULT_TEAM = {
    "team": "IT Service Desk General Triage",
    "tier": "Tier 1",
    "escalation_contact": "servicedesk-leads@digiplus.internal",
}


def search_similar_tickets(query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Search historical incident tickets to find related past issues and their resolutions.

    Args:
        query: Description or keywords describing the issue symptoms.
        category: Optional category filter (e.g. 'Network', 'Database', 'VPN and access').

    Returns:
        List of matching historical tickets with ticket_id, title, category, priority, resolution, and similarity score.
    """
    if not query or not query.strip():
        return []

    query = query.strip()
    conn = get_db_connection()
    if conn is None:
        logger.warning("DB unavailable for search_similar_tickets, returning empty list")
        return []

    results: List[Dict[str, Any]] = []
    try:
        query_vector = embed_text(query)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if query_vector:
                vector_str = f"[{','.join(f'{x:.6f}' for x in query_vector)}]"
                sql = """
                    SELECT id, title, description, category, priority, status, resolution,
                           ROUND((1.0 - (embedding <=> %s::vector))::numeric, 3) AS similarity
                    FROM tickets
                    WHERE embedding IS NOT NULL
                """
                params = [vector_str]
                if category and category.strip() and category.lower() != "other":
                    sql += " AND category ILIKE %s"
                    params.append(f"%{category.strip()}%")
                sql += " ORDER BY embedding <=> %s::vector ASC LIMIT 5;"
                params.append(vector_str)
                cur.execute(sql, params)
                rows = cur.fetchall()
                for row in rows:
                    results.append({
                        "ticket_id": int(row["id"]),
                        "title": row["title"],
                        "description": (row["description"] or "")[:250],
                        "category": row["category"],
                        "priority": row["priority"],
                        "status": row["status"],
                        "resolution": row["resolution"] or "No resolution recorded",
                        "similarity_score": float(row["similarity"] or 0.0),
                    })

            # If no vector results, fallback to text ILIKE query
            if not results:
                sql = """
                    SELECT id, title, description, category, priority, status, resolution
                    FROM tickets
                    WHERE title ILIKE %s OR description ILIKE %s
                """
                term = f"%{query}%"
                params = [term, term]
                if category and category.strip() and category.lower() != "other":
                    sql += " AND category ILIKE %s"
                    params.append(f"%{category.strip()}%")
                sql += " ORDER BY id DESC LIMIT 5;"
                cur.execute(sql, params)
                rows = cur.fetchall()
                for row in rows:
                    results.append({
                        "ticket_id": int(row["id"]),
                        "title": row["title"],
                        "description": (row["description"] or "")[:250],
                        "category": row["category"],
                        "priority": row["priority"],
                        "status": row["status"],
                        "resolution": row["resolution"] or "No resolution recorded",
                        "similarity_score": 0.75,
                    })
    except Exception as e:
        logger.error("Error executing search_similar_tickets: %s", e)
    finally:
        conn.close()

    return results


def search_kb(query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Search the technical knowledge base runbooks using Phase 2 Hybrid RAG retrieval.

    Args:
        query: Search keywords or problem description.
        category: Optional category filter.

    Returns:
        List of relevant runbook chunks with article_id, chunk_id, title, category, content, and relevance score.
    """
    if not query or not query.strip():
        return []

    try:
        chunks = retrieve_relevant_chunks(
            query=query.strip(),
            category=category,
            top_k=5,
        )
        return [
            {
                "article_id": int(c.article_id),
                "chunk_id": int(c.chunk_id),
                "title": c.article_title,
                "category": c.category,
                "content": c.content,
                "relevance_score": round(float(c.score), 3),
            }
            for c in chunks
        ]
    except Exception as e:
        logger.error("Error executing search_kb: %s", e)
        return []


def get_ticket_history(ticket_id: int) -> Dict[str, Any]:
    """
    Retrieve audit history, previous analysis summaries, and status records for a specific ticket.

    Args:
        ticket_id: Integer identifier of the ticket.

    Returns:
        Dictionary containing ticket details, resolution, creation timestamps, and prior agent execution summaries.
    """
    if not isinstance(ticket_id, int) or ticket_id <= 0:
        return {"status": "invalid_id", "message": f"Invalid ticket ID: {ticket_id}"}

    conn = get_db_connection()
    if conn is None:
        return {"status": "error", "message": "Database unavailable"}

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, title, description, category, priority, status, resolution,
                       created_at, updated_at, ai_summary, conversation_summary
                FROM tickets
                WHERE id = %s;
            """, (ticket_id,))
            ticket_row = cur.fetchone()
            if not ticket_row:
                return {"status": "not_found", "message": f"Ticket #{ticket_id} not found"}

            # Fetch recent agent runs
            cur.execute("""
                SELECT id, status, steps_count, latency_ms, created_at
                FROM agent_runs
                WHERE ticket_id = %s
                ORDER BY id DESC LIMIT 5;
            """, (ticket_id,))
            runs = [dict(r) for r in cur.fetchall()]
            for r in runs:
                if r.get("created_at"):
                    r["created_at"] = str(r["created_at"])

            return {
                "status": "found",
                "ticket_id": int(ticket_row["id"]),
                "title": ticket_row["title"],
                "category": ticket_row["category"],
                "priority": ticket_row["priority"],
                "current_status": ticket_row["status"],
                "resolution": ticket_row["resolution"] or "No resolution recorded",
                "created_at": str(ticket_row["created_at"]),
                "updated_at": str(ticket_row["updated_at"]),
                "previous_summary": ticket_row.get("conversation_summary") or ticket_row.get("ai_summary") or "No prior summary recorded",
                "prior_runs_count": len(runs),
                "prior_runs": runs,
                "history_note": "Retrieved from Neon PostgreSQL database.",
            }
    except Exception as e:
        logger.error("Error fetching ticket history for #%d: %s", ticket_id, e)
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def suggest_assignee(category: str) -> Dict[str, str]:
    """
    Recommend the responsible engineering support team based on incident category.

    Args:
        category: Incident category (e.g., 'Network', 'Database', 'Cloud & Infrastructure').

    Returns:
        Dictionary containing assigned team name, operational tier, and escalation contact.
    """
    if not category:
        norm_cat = "other"
    else:
        norm_cat = category.strip().lower()

    mapping = TEAM_MAPPINGS.get(norm_cat)
    if not mapping:
        # Check partial keyword match
        for key, val in TEAM_MAPPINGS.items():
            if key in norm_cat or norm_cat in key:
                mapping = val
                break

    if not mapping:
        mapping = DEFAULT_TEAM

    return {
        "category": category or "Other",
        "team": mapping["team"],
        "tier": mapping["tier"],
        "escalation_contact": mapping["escalation_contact"],
    }


# Tool registry mapping tool names to callable Python functions
TOOL_REGISTRY = {
    "search_similar_tickets": search_similar_tickets,
    "search_kb": search_kb,
    "get_ticket_history": get_ticket_history,
    "suggest_assignee": suggest_assignee,
}

# Exposed tools list for Google GenAI SDK
ALL_TOOLS = [
    search_similar_tickets,
    search_kb,
    get_ticket_history,
    suggest_assignee,
]
