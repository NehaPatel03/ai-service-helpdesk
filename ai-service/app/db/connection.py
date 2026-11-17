"""
Database connection and query helpers for PostgreSQL.
"""

import logging
import urllib.parse
from typing import Any, Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from app.config import settings

logger = logging.getLogger(__name__)


def _resolve_host_addr(hostname: str) -> Optional[str]:
    """Resolves hostname via Google Public DNS (8.8.8.8) to handle local ISP DNS filters."""
    if not hostname or hostname in ("localhost", "127.0.0.1") or hostname.replace(".", "").isdigit():
        return None
    try:
        import dns.resolver
        res = dns.resolver.Resolver()
        res.nameservers = ["8.8.8.8", "1.1.1.1"]
        answers = res.resolve(hostname, "A")
        if answers:
            return str(answers[0])
    except Exception:
        pass
    return None


def get_db_connection():
    """Returns a new psycopg2 connection to PostgreSQL with resilient DNS resolution."""
    try:
        return psycopg2.connect(settings.DATABASE_URL)
    except Exception as initial_err:
        try:
            parsed = urllib.parse.urlparse(settings.DATABASE_URL)
            if parsed.hostname:
                ip = _resolve_host_addr(parsed.hostname)
                if ip:
                    return psycopg2.connect(
                        host=parsed.hostname,
                        hostaddr=ip,
                        port=parsed.port or 5432,
                        user=parsed.username,
                        password=parsed.password,
                        dbname=parsed.path.lstrip("/"),
                        sslmode="require" if "sslmode" in settings.DATABASE_URL else "prefer",
                    )
        except Exception:
            pass
        logger.warning("Could not connect to PostgreSQL database: %s", initial_err)
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
