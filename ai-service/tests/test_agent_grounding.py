"""
Unit Tests for Phase 3 Grounding Verification.
"""

import pytest
from app.agent.grounding import (
    extract_tool_grounded_ids,
    sanitize_grounded_analysis,
    verify_grounding,
)
from app.agent.schemas import Analysis, ToolCallRecord


def test_extract_tool_grounded_ids():
    """Verify tool execution traces correctly aggregate valid ticket and KB IDs."""
    calls = [
        ToolCallRecord(
            step=1,
            tool_name="search_similar_tickets",
            args={"query": "vpn"},
            result=[
                {"ticket_id": 10, "title": "Ticket A"},
                {"ticket_id": 20, "title": "Ticket B"},
            ],
        ),
        ToolCallRecord(
            step=2,
            tool_name="search_kb",
            args={"query": "vpn"},
            result=[
                {"article_id": 5, "chunk_id": 105, "title": "Runbook A"},
                {"article_id": 12, "chunk_id": 112, "title": "Runbook B"},
            ],
        ),
        ToolCallRecord(
            step=3,
            tool_name="get_ticket_history",
            args={"ticket_id": 30},
            result={"status": "found", "ticket_id": 30, "title": "Ticket C"},
        ),
    ]

    t_ids, kb_ids = extract_tool_grounded_ids(calls)
    assert t_ids == {10, 20, 30}
    assert 5 in kb_ids
    assert 12 in kb_ids
    assert 105 in kb_ids


def test_fully_grounded_output():
    """Verify valid references pass grounding verification without flags."""
    analysis = Analysis(
        root_cause="Exhausted pool",
        confidence="high",
        suggested_steps=["Step 1"],
        related_ticket_ids=[10, 20],
        kb_sources=[5, 12],
    )
    grounded_tickets = {10, 20, 30}
    grounded_kb = {5, 12, 105}

    res = verify_grounding(analysis, grounded_tickets, grounded_kb)
    assert res.is_valid is True
    assert res.unsupported_ticket_ids == []
    assert res.unsupported_kb_ids == []
    assert res.grounded_ticket_ids == [10, 20]
    assert res.grounded_kb_ids == [5, 12]


def test_invented_kb_ids():
    """Verify invented/hallucinated KB article IDs are detected and flagged."""
    analysis = Analysis(
        root_cause="Exhausted pool",
        confidence="high",
        suggested_steps=["Step 1"],
        related_ticket_ids=[10],
        kb_sources=[999, 888],  # Invented
    )
    grounded_tickets = {10}
    grounded_kb = {5, 12}

    res = verify_grounding(analysis, grounded_tickets, grounded_kb)
    assert res.is_valid is False
    assert 999 in res.unsupported_kb_ids
    assert 888 in res.unsupported_kb_ids
    assert res.grounded_kb_ids == []


def test_invented_ticket_ids():
    """Verify invented ticket IDs are detected and flagged."""
    analysis = Analysis(
        root_cause="Exhausted pool",
        confidence="medium",
        suggested_steps=["Step 1"],
        related_ticket_ids=[9999],  # Invented
        kb_sources=[5],
    )
    grounded_tickets = {10, 20}
    grounded_kb = {5}

    res = verify_grounding(analysis, grounded_tickets, grounded_kb)
    assert res.is_valid is False
    assert res.unsupported_ticket_ids == [9999]
    assert res.grounded_ticket_ids == []
    assert res.grounded_kb_ids == [5]


def test_empty_tool_results_with_claimed_sources():
    """Verify that claiming sources when tools returned no results fails grounding."""
    analysis = Analysis(
        root_cause="Exhausted pool",
        confidence="low",
        suggested_steps=["Step 1"],
        related_ticket_ids=[1],
        kb_sources=[2],
    )
    # Empty tools
    res = verify_grounding(analysis, set(), set())
    assert res.is_valid is False
    assert res.unsupported_ticket_ids == [1]
    assert res.unsupported_kb_ids == [2]


def test_mixed_valid_and_invalid_references():
    """Verify mixed lists properly separate grounded references from invented ones."""
    analysis = Analysis(
        root_cause="Exhausted pool",
        confidence="high",
        suggested_steps=["Step 1"],
        related_ticket_ids=[10, 999],  # 10 is valid, 999 is invalid
        kb_sources=[5, 888],           # 5 is valid, 888 is invalid
    )
    grounded_tickets = {10, 20}
    grounded_kb = {5, 6}

    res = verify_grounding(analysis, grounded_tickets, grounded_kb)
    assert res.is_valid is False
    assert res.grounded_ticket_ids == [10]
    assert res.unsupported_ticket_ids == [999]
    assert res.grounded_kb_ids == [5]
    assert res.unsupported_kb_ids == [888]

    # Test sanitization removes unsupported references
    sanitized = sanitize_grounded_analysis(analysis, res)
    assert sanitized.related_ticket_ids == [10]
    assert sanitized.kb_sources == [5]
