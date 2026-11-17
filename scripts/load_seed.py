"""
Seed Data Loader for DigiPlus AI Service Desk.

Loads:
- data/seed/kb_articles.jsonl into the database.
- data/seed/tickets.jsonl into the database.
Strictly verifies:
- eval/golden_set.jsonl tickets are absent from the database index.

Supports:
- SQLite (default for existing app: data/support_desk.db).
- PostgreSQL (when --db-type postgres or DATABASE_URL is set).

Usage:
    python scripts/load_seed.py [--db-type sqlite|postgres] [--db-path data/support_desk.db]
"""

import argparse
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Set


def extract_summary_and_tags(title: str, body: str, category: str) -> tuple[str, str]:
    """Extracts a short 1-sentence summary and JSON tags array for SQLite compatibility."""
    # Find Problem Overview paragraph or first sentence
    match = re.search(r"### Problem Overview\s*\n(.*?)(?=\n\n|\n###|\Z)", body, re.DOTALL)
    if match:
        summary = match.group(1).strip().replace("\n", " ")
        if len(summary) > 200:
            summary = summary[:197] + "..."
    else:
        summary = f"Technical runbook for resolving {title}."

    # Extract keywords as tags
    words = re.findall(r"\b[a-zA-Z0-9-]{3,15}\b", f"{title} {category}")
    unique_tags = list(dict.fromkeys([w.lower() for w in words if w.lower() not in {"and", "the", "for", "with"}]))
    tags_json = json.dumps(unique_tags[:8])
    return summary, tags_json


def load_seed_sqlite(
    db_path: Path,
    kb_path: Path,
    tickets_path: Path,
    golden_path: Path,
) -> Dict[str, Any]:
    """Loads seed data into SQLite and verifies golden set exclusion."""
    if not db_path.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Ensure tables exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_base (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            summary TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'Medium',
            category TEXT NOT NULL DEFAULT 'Other',
            status TEXT NOT NULL DEFAULT 'Open',
            resolution TEXT,
            ai_summary TEXT,
            ai_cause TEXT,
            ai_solution TEXT,
            ai_suggested_category TEXT,
            ai_suggested_priority TEXT,
            source TEXT DEFAULT 'manual',
            external_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 1. Load KB Articles
    with open(kb_path, "r", encoding="utf-8") as f:
        kb_records = [json.loads(line) for line in f if line.strip()]

    kb_inserted = 0
    kb_updated = 0
    for kb in kb_records:
        summary, tags_json = extract_summary_and_tags(kb["title"], kb["body"], kb["category"])
        cursor.execute("SELECT id FROM knowledge_base WHERE id = ?", (kb["id"],))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("""
                UPDATE knowledge_base
                SET title = ?, category = ?, summary = ?, content = ?, tags = ?
                WHERE id = ?
            """, (kb["title"], kb["category"], summary, kb["body"], tags_json, kb["id"]))
            kb_updated += 1
        else:
            cursor.execute("""
                INSERT INTO knowledge_base (id, title, category, summary, content, tags)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (kb["id"], kb["title"], kb["category"], summary, kb["body"], tags_json))
            kb_inserted += 1

    # 2. Load Historical Tickets
    with open(tickets_path, "r", encoding="utf-8") as f:
        ticket_records = [json.loads(line) for line in f if line.strip()]

    tickets_inserted = 0
    tickets_updated = 0
    for t in ticket_records:
        external_id = f"seed-{t['id']}"
        cursor.execute("SELECT id FROM tickets WHERE external_id = ? OR id = ?", (external_id, t["id"]))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("""
                UPDATE tickets
                SET title = ?, description = ?, category = ?, priority = ?, status = 'Resolved',
                    resolution = ?, source = 'seed', external_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (t["title"], t["description"], t["category"], t["priority"], t["resolution"], external_id, existing[0]))
            tickets_updated += 1
        else:
            cursor.execute("""
                INSERT INTO tickets (id, title, description, priority, category, status, resolution, source, external_id)
                VALUES (?, ?, ?, ?, ?, 'Resolved', ?, 'seed', ?)
            """, (t["id"], t["title"], t["description"], t["priority"], t["category"], t["resolution"], external_id))
            tickets_inserted += 1

    conn.commit()

    # 3. Golden Set Isolation Verification
    with open(golden_path, "r", encoding="utf-8") as f:
        golden_records = [json.loads(line) for line in f if line.strip()]

    golden_ids = [g["ticket_id"] for g in golden_records]
    placeholders = ",".join("?" for _ in golden_ids)
    cursor.execute(f"SELECT id FROM tickets WHERE id IN ({placeholders})", golden_ids)
    found_golden = cursor.fetchall()

    conn.close()

    if found_golden:
        raise ValueError(f"🚨 CRITICAL ERROR: Found {len(found_golden)} golden set tickets inside the indexed tickets table!")

    return {
        "db_type": "sqlite",
        "kb_inserted": kb_inserted,
        "kb_updated": kb_updated,
        "total_kb": len(kb_records),
        "tickets_inserted": tickets_inserted,
        "tickets_updated": tickets_updated,
        "total_tickets": len(ticket_records),
        "golden_set_checked": len(golden_records),
        "golden_set_in_index": 0,
    }


def load_seed_postgres(
    db_url: str,
    kb_path: Path,
    tickets_path: Path,
    golden_path: Path,
) -> Dict[str, Any]:
    """Loads seed data into PostgreSQL with pgvector schema."""
    try:
        import psycopg2
    except ImportError:
        raise ImportError("psycopg2-binary is required for PostgreSQL loading. Run: pip install psycopg2-binary")

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    # Load KB Articles
    with open(kb_path, "r", encoding="utf-8") as f:
        kb_records = [json.loads(line) for line in f if line.strip()]

    for kb in kb_records:
        cursor.execute("""
            INSERT INTO kb_articles (id, title, body, category)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE
            SET title = EXCLUDED.title, body = EXCLUDED.body, category = EXCLUDED.category
        """, (kb["id"], kb["title"], kb["body"], kb["category"]))

    # Load Tickets
    with open(tickets_path, "r", encoding="utf-8") as f:
        ticket_records = [json.loads(line) for line in f if line.strip()]

    for t in ticket_records:
        cursor.execute("""
            INSERT INTO tickets (id, title, description, category, priority, status, resolution)
            VALUES (%s, %s, %s, %s, %s, 'Resolved', %s)
            ON CONFLICT (id) DO UPDATE
            SET title = EXCLUDED.title, description = EXCLUDED.description,
                category = EXCLUDED.category, priority = EXCLUDED.priority,
                status = 'Resolved', resolution = EXCLUDED.resolution
        """, (t["id"], t["title"], t["description"], t["category"], t["priority"], t["resolution"]))

    conn.commit()

    # Verify Golden Set Exclusion
    with open(golden_path, "r", encoding="utf-8") as f:
        golden_records = [json.loads(line) for line in f if line.strip()]

    golden_ids = [g["ticket_id"] for g in golden_records]
    cursor.execute("SELECT id FROM tickets WHERE id = ANY(%s)", (golden_ids,))
    found_golden = cursor.fetchall()

    conn.close()

    if found_golden:
        raise ValueError(f"🚨 CRITICAL ERROR: Found {len(found_golden)} golden set tickets inside PostgreSQL index!")

    return {
        "db_type": "postgres",
        "total_kb": len(kb_records),
        "total_tickets": len(ticket_records),
        "golden_set_checked": len(golden_records),
        "golden_set_in_index": 0,
    }


def main():
    parser = argparse.ArgumentParser(description="Load seed dataset into DigiPlus database.")
    parser.add_argument("--db-type", choices=["sqlite", "postgres"], default="sqlite", help="Target database type.")
    parser.add_argument("--db-path", type=Path, default=Path("data/support_desk.db"), help="Path to SQLite database.")
    parser.add_argument("--db-url", type=str, default=os.getenv("DATABASE_URL", ""), help="PostgreSQL connection URL.")
    parser.add_argument("--seed-dir", type=Path, default=Path("data/seed"), help="Directory containing seed JSONL files.")
    parser.add_argument("--eval-dir", type=Path, default=Path("eval"), help="Directory containing golden set.")
    args = parser.parse_args()

    kb_path = args.seed_dir / "kb_articles.jsonl"
    tickets_path = args.seed_dir / "tickets.jsonl"
    golden_path = args.eval_dir / "golden_set.jsonl"

    for p in [kb_path, tickets_path, golden_path]:
        if not p.exists():
            print(f"❌ Error: Required file not found: {p}", file=sys.stderr)
            print("Please run: python scripts/generate_seed_data.py first.", file=sys.stderr)
            sys.exit(1)

    print(f"📥 Loading seed data into {args.db_type.upper()}...")
    if args.db_type == "sqlite":
        result = load_seed_sqlite(args.db_path, kb_path, tickets_path, golden_path)
    else:
        if not args.db_url:
            print("❌ Error: --db-url or DATABASE_URL must be specified for postgres.", file=sys.stderr)
            sys.exit(1)
        result = load_seed_postgres(args.db_url, kb_path, tickets_path, golden_path)

    print("\n📊 Load Summary:")
    print(f"  • Database: {result['db_type']}")
    print(f"  • KB Articles: {result['total_kb']} loaded")
    print(f"  • Historical Tickets: {result['total_tickets']} loaded")
    print(f"  • Golden Set Verified: {result['golden_set_checked']} tickets checked")
    print(f"  • Golden Set in Index: {result['golden_set_in_index']} (Strictly Excluded ✅)")
    print("\n🎉 Seed data loaded successfully!")


if __name__ == "__main__":
    main()
