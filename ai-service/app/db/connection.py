"""
Database connection and query helpers for PostgreSQL.
"""

import logging
from typing import Any, Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from app.config import settings

logger = logging.getLogger(__name__)


def get_db_connection():
    """Returns a new psycopg2 connection to PostgreSQL."""
    try:
        conn = psycopg2.connect(settings.DATABASE_URL)
        return conn
    except Exception as e:
        logger.warning("Could not connect to PostgreSQL database: %s", e)
        return None


def check_db_health() -> str:
    """Checks whether the PostgreSQL database is reachable and pgvector is enabled."""
    conn = get_db_connection()
    if conn is None:
        return "disconnected (PostgreSQL not reachable or offline)"

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector';")
            vector_ext = cur.fetchone()
            ext_status = "vector enabled" if vector_ext else "vector extension not installed"
        conn.close()
        return f"connected ({ext_status})"
    except Exception as e:
        return f"error: {str(e)}"


def get_all_kb_articles() -> List[Dict[str, Any]]:
    """Fetches all KB articles from PostgreSQL if available."""
    conn = get_db_connection()
    if conn is None:
        return []

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, title, body, category FROM kb_articles ORDER BY id ASC;")
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.warning("Error fetching KB articles from Postgres: %s", e)
        return []
    finally:
        conn.close()
