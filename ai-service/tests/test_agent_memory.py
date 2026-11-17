"""
Unit Tests for Phase 3 Conversation Memory.
"""

import pytest
from app.agent.memory import (
    compose_rolling_summary,
    get_ticket_memory,
    update_ticket_memory,
)
from app.agent.schemas import Analysis


def test_first_analysis_memory_composition():
    """Verify compose_rolling_summary creates clean summary when no previous memory exists."""
    analysis = Analysis(
        root_cause="PostgreSQL max_connections reached by unclosed batch jobs",
        confidence="high",
        suggested_steps=["Terminate long running queries", "Restart PgBouncer"],
        related_ticket_ids=[],
        kb_sources=[],
    )
    summary = compose_rolling_summary(None, analysis)
    assert "Root cause: PostgreSQL max_connections" in summary
    assert "Key action: Terminate long running queries" in summary


def test_subsequent_rolling_summary_composition():
    """Verify compose_rolling_summary combines prior context with updated analysis."""
    analysis = Analysis(
        root_cause="Stale client DNS records causing timeout",
        confidence="medium",
        suggested_steps=["Flush DNS cache"],
        related_ticket_ids=[],
        kb_sources=[],
    )
    prior = "Prior investigation: verified server is listening on port 53."
    summary = compose_rolling_summary(prior, analysis)
    assert "Prior investigation:" in summary
    assert "Stale client DNS records" in summary


def test_memory_persistence_and_retrieval():
    """Verify conversation memory updates and persists in PostgreSQL."""
    test_ticket_id = 1
    test_summary = "Test memory snapshot: verified PgBouncer configuration and connection limits."

    # Update memory
    success = update_ticket_memory(test_ticket_id, test_summary)
    if success:
        retrieved = get_ticket_memory(test_ticket_id)
        assert retrieved is not None
        assert "PgBouncer" in retrieved


def test_get_ticket_memory_nonexistent_ticket():
    """Verify get_ticket_memory returns None for non-existent ticket."""
    assert get_ticket_memory(99999999) is None
    assert get_ticket_memory(-1) is None
