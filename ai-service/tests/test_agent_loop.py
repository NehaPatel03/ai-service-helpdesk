"""
Unit Tests for Phase 3 Multi-Step Agent Loop, Structured Output, and Logging.

Uses mocked Gemini client to verify:
1. Single and multi-turn tool calling
2. Result forwarding back to model
3. Max 5-step loop limit protection
4. Invalid tool call handling
5. Pydantic structured output validation and retry logic
6. API failure and fallback handling
7. Execution logging and telemetry capture
"""

import json
from unittest.mock import MagicMock
import pytest
from pydantic import ValidationError

from app.agent.agent import run_incident_agent, generate_fallback_analysis_pydantic
from app.agent.schemas import Analysis, ToolCallRecord, AgentExecutionTrace
from app.schemas import TicketInput


class MockFunctionCall:
    def __init__(self, name: str, args: dict):
        self.name = name
        self.args = args


class MockUsageMetadata:
    def __init__(self, prompt_tokens: int = 150, candidate_tokens: int = 90):
        self.prompt_token_count = prompt_tokens
        self.candidates_token_count = candidate_tokens


class MockResponse:
    def __init__(
        self,
        function_calls=None,
        text="",
        prompt_tokens=150,
        candidate_tokens=90,
    ):
        self.function_calls = function_calls
        self.text = text
        self.candidates = [MagicMock(content=MagicMock())]
        self.usage_metadata = MockUsageMetadata(prompt_tokens, candidate_tokens)


class MockModelsService:
    def __init__(self, responses):
        self.responses = list(responses)
        self.call_count = 0

    def generate_content(self, model, contents, config):
        if self.call_count < len(self.responses):
            res = self.responses[self.call_count]
            self.call_count += 1
            return res
        # Default response
        return MockResponse(
            text=json.dumps({
                "root_cause": "Default test root cause",
                "confidence": "high",
                "suggested_steps": ["Step 1", "Step 2"],
                "related_ticket_ids": [],
                "kb_sources": [],
            })
        )


class MockGenAIClient:
    def __init__(self, responses):
        self.models = MockModelsService(responses)


# ==============================================================================
# Agent Loop & Function Calling Tests
# ==============================================================================

def test_agent_requests_single_tool_and_produces_analysis():
    """Verify agent invokes requested tool, receives result, and parses structured output."""
    ticket = TicketInput(
        id=1,
        title="VPN connection failed on remote client",
        description="User cannot connect to gateway on port 443 with timeout 504.",
        category="VPN and access",
        priority="High",
    )

    # Step 1: Model requests search_kb tool
    step1_response = MockResponse(
        function_calls=[MockFunctionCall("search_kb", {"query": "VPN connection gateway"})]
    )

    # Step 2: Model finishes with valid Analysis JSON citing returned KB article #4
    step2_response = MockResponse(
        text=json.dumps({
            "root_cause": "VPN Gateway SSL tunnel handshake timeout due to client MTU mismatch.",
            "confidence": "high",
            "suggested_steps": [
                "Clear client credentials",
                "Set MTU to 1360",
                "Restart GlobalProtect service",
            ],
            "related_ticket_ids": [],
            "kb_sources": [4],
        })
    )

    mock_client = MockGenAIClient([step1_response, step2_response])
    analysis, trace = run_incident_agent(ticket, max_steps=5, client=mock_client)

    assert trace.status == "success"
    assert trace.used_fallback is False
    assert trace.valid_schema is True
    assert len(trace.tool_calls) == 1
    assert trace.tool_calls[0].tool_name == "search_kb"
    assert trace.tool_calls[0].args == {"query": "VPN connection gateway"}
    assert analysis.root_cause.startswith("VPN Gateway")
    assert analysis.confidence == "high"
    assert len(analysis.suggested_steps) == 3


def test_agent_requests_multiple_tools():
    """Verify agent can execute multiple tools in sequence."""
    ticket = TicketInput(
        id=1,
        title="PostgreSQL connection pool exhausted",
        description="500 Internal Server Error during peak batch.",
        category="database",
        priority="Urgent",
    )

    # Step 1: Request search_similar_tickets
    step1 = MockResponse(
        function_calls=[MockFunctionCall("search_similar_tickets", {"query": "connection pool exhausted"})]
    )
    # Step 2: Request suggest_assignee
    step2 = MockResponse(
        function_calls=[MockFunctionCall("suggest_assignee", {"category": "database"})]
    )
    # Step 3: Model produces final output
    step3 = MockResponse(
        text=json.dumps({
            "root_cause": "PostgreSQL unclosed client transaction leak.",
            "confidence": "high",
            "suggested_steps": ["Inspect pg_stat_activity", "Restart connection pooler"],
            "related_ticket_ids": [],
            "kb_sources": [],
        })
    )

    mock_client = MockGenAIClient([step1, step2, step3])
    analysis, trace = run_incident_agent(ticket, max_steps=5, client=mock_client)

    assert trace.status == "success"
    assert len(trace.tool_calls) == 2
    assert trace.tool_calls[0].tool_name == "search_similar_tickets"
    assert trace.tool_calls[1].tool_name == "suggest_assignee"
    assert trace.steps_count == 3


def test_agent_handles_invalid_tool_call():
    """Verify agent handles hallucinated/invalid tool names safely without crashing."""
    ticket = TicketInput(
        id=1,
        title="DNS resolution failure",
        description="Lookup returns NXDOMAIN.",
        category="network",
        priority="Medium",
    )

    # Step 1: Model requests unknown tool
    step1 = MockResponse(
        function_calls=[MockFunctionCall("restart_nuclear_reactor", {"core_id": 1})]
    )
    # Step 2: Model finishes with fallback
    step2 = MockResponse(
        text=json.dumps({
            "root_cause": "Local resolver cache stale.",
            "confidence": "medium",
            "suggested_steps": ["Flush DNS cache"],
            "related_ticket_ids": [],
            "kb_sources": [],
        })
    )

    mock_client = MockGenAIClient([step1, step2])
    analysis, trace = run_incident_agent(ticket, max_steps=5, client=mock_client)

    assert len(trace.tool_calls) == 1
    assert trace.tool_calls[0].error is not None
    assert "not recognized" in trace.tool_calls[0].error
    assert trace.status == "success"


def test_agent_max_step_limit_protection():
    """Verify agent terminates gracefully when max 5 steps are reached in an infinite loop."""
    ticket = TicketInput(
        id=1,
        title="Stuck in loop",
        description="Infinite tool calling simulation.",
        category="Other",
        priority="Low",
    )

    # 6 responses all requesting search_kb repeatedly
    infinite_tool_responses = [
        MockResponse(function_calls=[MockFunctionCall("search_kb", {"query": f"loop {i}"})])
        for i in range(7)
    ]

    mock_client = MockGenAIClient(infinite_tool_responses)
    analysis, trace = run_incident_agent(ticket, max_steps=5, client=mock_client)

    assert trace.steps_count == 5
    assert trace.status == "max_steps_reached"
    assert trace.used_fallback is True
    assert isinstance(analysis, Analysis)


def test_agent_api_failure_fallback():
    """Verify unhandled API exceptions trigger safe heuristic fallback."""
    ticket = TicketInput(
        id=1,
        title="API Crash Simulation",
        description="Testing API error recovery.",
        category="Other",
        priority="Medium",
    )

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("503 Service Unavailable")

    analysis, trace = run_incident_agent(ticket, max_steps=5, client=mock_client)

    assert trace.status == "api_error"
    assert trace.used_fallback is True
    assert "503 Service Unavailable" in trace.error
    assert isinstance(analysis, Analysis)


# ==============================================================================
# Structured Output & Retry Tests
# ==============================================================================

def test_pydantic_validation_retry_success():
    """Verify that malformed JSON triggers validation retry and successfully recovers."""
    ticket = TicketInput(
        id=1,
        title="Schema Retry Test",
        description="First attempt returns invalid confidence value.",
        category="software",
        priority="Medium",
    )

    # Step 1: Invalid confidence "extremely_super_high"
    step1_invalid = MockResponse(
        text=json.dumps({
            "root_cause": "Bug in code",
            "confidence": "extremely_super_high",  # Invalid literal
            "suggested_steps": ["Fix bug"],
            "related_ticket_ids": [],
            "kb_sources": [],
        })
    )

    # Step 2: Retry with valid confidence "high"
    step2_corrected = MockResponse(
        text=json.dumps({
            "root_cause": "Bug in code",
            "confidence": "high",  # Corrected
            "suggested_steps": ["Fix bug"],
            "related_ticket_ids": [],
            "kb_sources": [],
        })
    )

    mock_client = MockGenAIClient([step1_invalid, step2_corrected])
    analysis, trace = run_incident_agent(ticket, max_steps=5, client=mock_client)

    assert trace.status == "success"
    assert trace.valid_schema is True
    assert analysis.confidence == "high"


def test_pydantic_validation_retry_failure():
    """Verify that repeated validation failures result in safe fallback with valid_schema=False."""
    ticket = TicketInput(
        id=1,
        title="Unrecoverable Schema Test",
        description="Both attempts return unparseable garbage text.",
        category="software",
        priority="Medium",
    )

    # Both attempts return plain text instead of JSON
    step1_garbage = MockResponse(text="I cannot help you today.")
    step2_garbage = MockResponse(text="Still not JSON.")

    mock_client = MockGenAIClient([step1_garbage, step2_garbage])
    analysis, trace = run_incident_agent(ticket, max_steps=5, client=mock_client)

    assert trace.status == "validation_failed"
    assert trace.valid_schema is False
    assert trace.used_fallback is True
    assert isinstance(analysis, Analysis)


# ==============================================================================
# Telemetry & Observability Tests
# ==============================================================================

def test_telemetry_captures_tokens_and_latency():
    """Verify token counts and latency metrics are tracked in the execution trace."""
    ticket = TicketInput(
        id=1,
        title="Telemetry Test",
        description="Check tokens_in and tokens_out.",
        category="database",
        priority="High",
    )

    step1 = MockResponse(
        text=json.dumps({
            "root_cause": "Connection limits exceeded",
            "confidence": "high",
            "suggested_steps": ["Increase limits"],
            "related_ticket_ids": [],
            "kb_sources": [],
        }),
        prompt_tokens=220,
        candidate_tokens=110,
    )

    mock_client = MockGenAIClient([step1])
    analysis, trace = run_incident_agent(ticket, max_steps=5, client=mock_client)

    assert trace.tokens_in >= 220
    assert trace.tokens_out >= 110
    assert trace.latency_ms >= 0
    assert trace.steps_count == 1
