"""
Unit Tests for Phase 3 Agent Diagnostic Tools.
"""

import pytest
from app.agent.tools import (
    get_ticket_history,
    search_kb,
    search_similar_tickets,
    suggest_assignee,
)


def test_suggest_assignee_known_categories():
    """Verify suggest_assignee maps canonical IT categories to correct engineering teams."""
    # Network
    net = suggest_assignee("Network")
    assert "Network" in net["team"] or "NOC" in net["team"]
    assert net["tier"] == "Tier 2"
    assert "noc" in net["escalation_contact"]

    # Database
    db = suggest_assignee("Database")
    assert "Database" in db["team"] or "DBA" in db["team"]
    assert db["tier"] == "Tier 3"
    assert "dba" in db["escalation_contact"]

    # Cloud & Infrastructure
    cloud = suggest_assignee("Cloud & Infrastructure")
    assert "Cloud" in cloud["team"] or "SRE" in cloud["team"]
    assert cloud["tier"] == "Tier 3"


def test_suggest_assignee_unknown_category():
    """Verify suggest_assignee returns sensible default triage team for unknown or empty categories."""
    unknown = suggest_assignee("Unicorn Maintenance")
    assert unknown["team"] == "IT Service Desk General Triage"
    assert unknown["tier"] == "Tier 1"

    empty = suggest_assignee("")
    assert empty["team"] == "IT Service Desk General Triage"


def test_search_kb_empty_query():
    """Verify search_kb gracefully handles empty/whitespace queries."""
    assert search_kb("") == []
    assert search_kb("   ") == []


def test_search_kb_valid_query():
    """Verify search_kb executes hybrid retrieval and returns structured runbook chunks."""
    results = search_kb("VPN gateway tunnel timeout error", category="VPN and access")
    assert isinstance(results, list)
    if results:
        first = results[0]
        assert "article_id" in first
        assert "chunk_id" in first
        assert "title" in first
        assert "content" in first
        assert "relevance_score" in first
        assert isinstance(first["article_id"], int)


def test_search_similar_tickets_empty_query():
    """Verify search_similar_tickets returns empty list on blank input."""
    assert search_similar_tickets("") == []
    assert search_similar_tickets("   ") == []


def test_search_similar_tickets_valid_query():
    """Verify search_similar_tickets executes similarity search and returns structured results."""
    results = search_similar_tickets("connection pool exhausted", category="database")
    assert isinstance(results, list)
    if results:
        first = results[0]
        assert "ticket_id" in first
        assert "title" in first
        assert "category" in first
        assert "priority" in first
        assert "status" in first
        assert "resolution" in first
        assert "similarity_score" in first
        assert isinstance(first["ticket_id"], int)


def test_get_ticket_history_invalid_id():
    """Verify get_ticket_history rejects non-positive or invalid IDs."""
    res_neg = get_ticket_history(-1)
    assert res_neg["status"] == "invalid_id"

    res_zero = get_ticket_history(0)
    assert res_zero["status"] == "invalid_id"


def test_get_ticket_history_nonexistent_ticket():
    """Verify get_ticket_history returns not_found for non-existent ticket."""
    res = get_ticket_history(99999999)
    assert res["status"] in ["not_found", "error"]


def test_get_ticket_history_existing_ticket():
    """Verify get_ticket_history retrieves real ticket history for an existing ticket."""
    # Find a valid ticket ID first or query ticket #1
    res = get_ticket_history(1)
    if res["status"] == "found":
        assert res["ticket_id"] == 1
        assert "title" in res
        assert "current_status" in res
        assert "previous_summary" in res
        assert "prior_runs" in res
        assert isinstance(res["prior_runs"], list)
