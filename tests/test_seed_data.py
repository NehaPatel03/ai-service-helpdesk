"""
Unit tests for Phase 0 Seed and Evaluation Datasets.
Verifies:
1. data/seed/kb_articles.jsonl count (30-50), fields, and category coverage.
2. data/seed/tickets.jsonl count (~300), fields, and valid kb_article_id references.
3. eval/golden_set.jsonl count (60), fields, and valid expected_kb_article_id references.
4. Complete isolation: Golden set tickets are 100% disjoint from historical tickets and absent from search index.
5. scripts/load_seed.py loads data into SQLite cleanly without indexing golden set.
"""

import json
import sqlite3
import tempfile
from pathlib import Path
import pytest

from scripts.generate_seed_data import (
    CATEGORIES,
    KBArticle,
    Ticket,
    GoldenTicket,
    generate_seed_dataset,
)
from scripts.load_seed import load_seed_sqlite

REPO_ROOT = Path(__file__).parent.parent
KB_FILE = REPO_ROOT / "data" / "seed" / "kb_articles.jsonl"
TICKETS_FILE = REPO_ROOT / "data" / "seed" / "tickets.jsonl"
GOLDEN_FILE = REPO_ROOT / "eval" / "golden_set.jsonl"


def test_kb_articles_count_and_schema():
    """Verify that KB articles file exists, has between 30 and 50 articles, and adheres to schema."""
    assert KB_FILE.exists(), f"Missing {KB_FILE}"
    articles = []
    with open(KB_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                article = KBArticle(**data)
                articles.append(article)

    # Acceptance criterion: 30 to 50 articles
    assert 30 <= len(articles) <= 50, f"Expected 30-50 KB articles, got {len(articles)}"

    # Unique IDs
    ids = [a.id for a in articles]
    assert len(ids) == len(set(ids)), "KB article IDs must be strictly unique"


def test_kb_articles_category_coverage():
    """Verify that all 8 required categories are covered by the KB articles."""
    with open(KB_FILE, "r", encoding="utf-8") as f:
        articles = [json.loads(line) for line in f if line.strip()]

    found_categories = {a["category"] for a in articles}
    for expected_cat in CATEGORIES:
        assert expected_cat in found_categories, f"Category '{expected_cat}' missing from KB articles"


def test_tickets_count_and_schema():
    """Verify historical tickets count (~300) and schema."""
    assert TICKETS_FILE.exists(), f"Missing {TICKETS_FILE}"
    tickets = []
    with open(TICKETS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                ticket = Ticket(**data)
                tickets.append(ticket)

    # Acceptance criterion: about 300 tickets
    assert 280 <= len(tickets) <= 320, f"Expected ~300 tickets, got {len(tickets)}"

    # Unique IDs
    ids = [t.id for t in tickets]
    assert len(ids) == len(set(ids)), "Historical ticket IDs must be unique"


def test_tickets_kb_references_valid():
    """Verify that all kb_article_id references in tickets.jsonl point to valid KB articles."""
    with open(KB_FILE, "r", encoding="utf-8") as f:
        kb_ids = {json.loads(line)["id"] for line in f if line.strip()}

    with open(TICKETS_FILE, "r", encoding="utf-8") as f:
        tickets = [json.loads(line) for line in f if line.strip()]

    for t in tickets:
        assert t["kb_article_id"] in kb_ids, (
            f"Ticket #{t['id']} references invalid kb_article_id {t['kb_article_id']}"
        )


def test_golden_set_count_and_schema():
    """Verify held-out evaluation dataset has exactly 60 tickets."""
    assert GOLDEN_FILE.exists(), f"Missing {GOLDEN_FILE}"
    golden_tickets = []
    with open(GOLDEN_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                gt = GoldenTicket(**data)
                golden_tickets.append(gt)

    # Acceptance criterion: exactly 60 tickets
    assert len(golden_tickets) == 60, f"Expected exactly 60 golden tickets, got {len(golden_tickets)}"


def test_golden_set_kb_references_valid():
    """Verify that expected_kb_article_id in golden set points to valid KB articles."""
    with open(KB_FILE, "r", encoding="utf-8") as f:
        kb_ids = {json.loads(line)["id"] for line in f if line.strip()}

    with open(GOLDEN_FILE, "r", encoding="utf-8") as f:
        golden_tickets = [json.loads(line) for line in f if line.strip()]

    for gt in golden_tickets:
        assert gt["expected_kb_article_id"] in kb_ids, (
            f"Golden ticket #{gt['ticket_id']} references invalid expected_kb_article_id {gt['expected_kb_article_id']}"
        )


def test_golden_set_disjoint_from_tickets():
    """CRITICAL ACCEPTANCE CRITERION: Golden-set tickets must NOT be in the searchable index/tickets."""
    with open(TICKETS_FILE, "r", encoding="utf-8") as f:
        ticket_ids = {json.loads(line)["id"] for line in f if line.strip()}

    with open(GOLDEN_FILE, "r", encoding="utf-8") as f:
        golden_ids = {json.loads(line)["ticket_id"] for line in f if line.strip()}

    overlap = ticket_ids.intersection(golden_ids)
    assert len(overlap) == 0, (
        f"Critical contamination: Golden set IDs found in historical tickets: {overlap}"
    )


def test_load_seed_sqlite_and_golden_exclusion():
    """Verify load_seed_sqlite creates database and ensures golden set is excluded."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_db = Path(tmpdir) / "test_load.db"
        result = load_seed_sqlite(tmp_db, KB_FILE, TICKETS_FILE, GOLDEN_FILE)

        assert result["total_kb"] >= 30
        assert result["total_tickets"] >= 280
        assert result["golden_set_checked"] == 60
        assert result["golden_set_in_index"] == 0

        # Query database directly to confirm
        conn = sqlite3.connect(tmp_db)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM knowledge_base")
        kb_count = c.fetchone()[0]
        assert kb_count == result["total_kb"]

        c.execute("SELECT COUNT(*) FROM tickets")
        ticket_count = c.fetchone()[0]
        assert ticket_count == result["total_tickets"]

        # Ensure no golden ticket IDs are in tickets table
        with open(GOLDEN_FILE, "r", encoding="utf-8") as f:
            golden_ids = [json.loads(line)["ticket_id"] for line in f if line.strip()]

        placeholders = ",".join("?" for _ in golden_ids)
        c.execute(f"SELECT COUNT(*) FROM tickets WHERE id IN ({placeholders})", golden_ids)
        leaked_count = c.fetchone()[0]
        assert leaked_count == 0, "Golden set tickets leaked into indexed tickets table!"
        conn.close()


def test_deterministic_generation():
    """Verify running generate_seed_dataset produces deterministic identical counts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        generate_seed_dataset(output_dir=tmp_path, seed=42)

        gen_kb = tmp_path / "data" / "seed" / "kb_articles.jsonl"
        gen_tickets = tmp_path / "data" / "seed" / "tickets.jsonl"
        gen_golden = tmp_path / "eval" / "golden_set.jsonl"

        assert gen_kb.exists()
        assert gen_tickets.exists()
        assert gen_golden.exists()

        with open(gen_kb, "r", encoding="utf-8") as f:
            assert len(f.readlines()) == 40
        with open(gen_tickets, "r", encoding="utf-8") as f:
            assert len(f.readlines()) == 300
        with open(gen_golden, "r", encoding="utf-8") as f:
            assert len(f.readlines()) == 60
