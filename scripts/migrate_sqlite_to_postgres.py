"""
Migration Script: SQLite to PostgreSQL + pgvector.

Copies existing historical data from SQLite (data/support_desk.db) into
PostgreSQL, preserving all existing incident IDs, categories, priorities,
resolutions, and timestamps. Resets PostgreSQL SERIAL sequences after import.

Usage:
    python scripts/migrate_sqlite_to_postgres.py [--sqlite-path data/support_desk.db] [--pg-url postgresql://...] [--dry-run]
"""

import argparse
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def migrate_data(
    sqlite_path: Path,
    pg_url: str,
    dry_run: bool = False,
) -> Dict[str, int]:
    """
    Migrates SQLite data into PostgreSQL.
    
    Args:
        sqlite_path: Path to existing SQLite database file.
        pg_url: Target PostgreSQL connection URL.
        dry_run: If True, inspects records without writing to PostgreSQL.
    
    Returns:
        Dict with counts of migrated records.
    """
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database not found at {sqlite_path}")

    # 1. Read SQLite
    print(f"📖 Reading existing data from SQLite: {sqlite_path}")
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    s_cur = sqlite_conn.cursor()

    # Read KB Articles
    s_cur.execute("SELECT id, title, category, summary, content FROM knowledge_base ORDER BY id ASC")
    sqlite_kb = [dict(row) for row in s_cur.fetchall()]
    print(f"  • Found {len(sqlite_kb)} knowledge base articles in SQLite.")

    # Read Tickets
    s_cur.execute("""
        SELECT id, title, description, priority, category, status, resolution,
               source, external_id, ai_summary, ai_cause, ai_solution,
               ai_suggested_category, ai_suggested_priority, created_at, updated_at
        FROM tickets ORDER BY id ASC
    """)
    sqlite_tickets = [dict(row) for row in s_cur.fetchall()]
    print(f"  • Found {len(sqlite_tickets)} tickets in SQLite.")

    sqlite_conn.close()

    if dry_run:
        print("🔍 Dry run completed. No data written to PostgreSQL.")
        return {
            "kb_articles": len(sqlite_kb),
            "tickets": len(sqlite_tickets),
            "dry_run": True,
        }

    # 2. Connect to PostgreSQL
    try:
        import psycopg2
        from psycopg2.extras import execute_batch
    except ImportError:
        raise ImportError("psycopg2-binary is required. Run: pip install psycopg2-binary")

    print(f"🔌 Connecting to PostgreSQL...")
    pg_conn = psycopg2.connect(pg_url)
    p_cur = pg_conn.cursor()

    # 3. Ensure Schema Exists
    migration_file = Path(__file__).parent.parent / "db" / "migrations" / "001_initial_schema.sql"
    if migration_file.exists():
        with open(migration_file, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        p_cur.execute(schema_sql)
        pg_conn.commit()
        print("✅ Verified/applied PostgreSQL schema migrations.")

    # 4. Migrate KB Articles
    kb_upsert_sql = """
        INSERT INTO kb_articles (id, title, body, category)
        VALUES (%(id)s, %(title)s, %(content)s, %(category)s)
        ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            body = EXCLUDED.body,
            category = EXCLUDED.category;
    """
    execute_batch(p_cur, kb_upsert_sql, sqlite_kb)
    print(f"✅ Migrated {len(sqlite_kb)} KB articles to PostgreSQL.")

    # 5. Migrate Tickets
    ticket_upsert_sql = """
        INSERT INTO tickets (
            id, title, description, category, priority, status, resolution,
            source, external_id, ai_summary, ai_cause, ai_solution,
            ai_suggested_category, ai_suggested_priority, created_at, updated_at
        ) VALUES (
            %(id)s, %(title)s, %(description)s, %(category)s, %(priority)s, %(status)s, %(resolution)s,
            %(source)s, %(external_id)s, %(ai_summary)s, %(ai_cause)s, %(ai_solution)s,
            %(ai_suggested_category)s, %(ai_suggested_priority)s, %(created_at)s, %(updated_at)s
        )
        ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            category = EXCLUDED.category,
            priority = EXCLUDED.priority,
            status = EXCLUDED.status,
            resolution = EXCLUDED.resolution,
            source = EXCLUDED.source,
            external_id = EXCLUDED.external_id,
            ai_summary = EXCLUDED.ai_summary,
            ai_cause = EXCLUDED.ai_cause,
            ai_solution = EXCLUDED.ai_solution,
            ai_suggested_category = EXCLUDED.ai_suggested_category,
            ai_suggested_priority = EXCLUDED.ai_suggested_priority,
            updated_at = EXCLUDED.updated_at;
    """
    execute_batch(p_cur, ticket_upsert_sql, sqlite_tickets)
    print(f"✅ Migrated {len(sqlite_tickets)} tickets to PostgreSQL.")

    # 6. Reset SERIAL Sequences
    p_cur.execute("SELECT setval(pg_get_serial_sequence('kb_articles', 'id'), COALESCE(MAX(id), 1)) FROM kb_articles;")
    p_cur.execute("SELECT setval(pg_get_serial_sequence('tickets', 'id'), COALESCE(MAX(id), 1)) FROM tickets;")
    pg_conn.commit()
    print("✅ Reset PostgreSQL SERIAL sequences.")

    p_cur.close()
    pg_conn.close()

    print("\n🎉 Migration completed successfully!")
    return {
        "kb_articles": len(sqlite_kb),
        "tickets": len(sqlite_tickets),
        "dry_run": False,
    }


def main():
    parser = argparse.ArgumentParser(description="Migrate SQLite support desk data to PostgreSQL.")
    parser.add_argument("--sqlite-path", type=Path, default=Path("data/support_desk.db"), help="Path to SQLite database.")
    parser.add_argument("--pg-url", type=str, default=os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/support_desk"), help="PostgreSQL connection URL.")
    parser.add_argument("--dry-run", action="store_true", help="Inspect records without inserting into PostgreSQL.")
    args = parser.parse_args()

    try:
        migrate_data(sqlite_path=args.sqlite_path, pg_url=args.pg_url, dry_run=args.dry_run)
    except Exception as e:
        print(f"❌ Migration error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
