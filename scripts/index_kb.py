"""
CLI Script: Index Knowledge Base Articles into Neon PostgreSQL + pgvector.

Usage:
    python scripts/index_kb.py [--batch-size 10]
"""

import argparse
import sys
import os
from pathlib import Path

# Add ai-service to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "ai-service"))

from app.rag.indexer import index_all_articles
from app.db.connection import get_db_connection


def main():
    parser = argparse.ArgumentParser(description="Index knowledge base articles into pgvector.")
    parser.add_argument("--batch-size", type=int, default=10, help="Embedding batch size.")
    args = parser.parse_args()

    print("🚀 Starting Knowledge Base Indexing to Neon PostgreSQL + pgvector...")
    try:
        conn = get_db_connection()
        if conn is None:
            print("❌ Error: Could not connect to PostgreSQL. Check DATABASE_URL in .env.local", file=sys.stderr)
            sys.exit(1)

        result = index_all_articles(conn=conn, batch_size=args.batch_size)
        print("\n✅ Indexing Completed Successfully!")
        print(f"  • Articles Indexed: {result['articles_indexed']}")
        print(f"  • Chunks Created:   {result['chunks_created']}")
        print(f"  • Embedding Dim:    {result['embed_dim']}")
        print(f"  • Time Elapsed:     {result['duration_seconds']}s")
    except Exception as e:
        print(f"\n❌ Indexing Failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
