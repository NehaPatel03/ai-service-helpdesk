"""
Unit and Integration Tests for FastAPI AI Service.

Tests:
1. GET /health - verifies service status and configuration constants.
2. POST /analyze-ticket - verifies structured output schema compliance.
3. POST /analyze-ticket input validation (HTTP 422 on invalid payload).
4. GET /search - verifies search query results structure.
5. POST /index - verifies indexing endpoint response.
6. Configuration settings and EMBED_DIM constant check.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)


def test_health_check_endpoint():
    """Verify /health returns HTTP 200 with required status and configuration constants."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert data["embed_dim"] == 768
    assert data["embed_model"] == "text-embedding-004"
    assert "version" in data
    assert "database" in data


def test_analyze_ticket_endpoint():
    """Verify /analyze-ticket processes an incident and returns the full structured AnalysisResponse."""
    payload = {
        "ticket": {
            "id": 101,
            "title": "PostgreSQL RDS connection pool exhausted during peak billing batch",
            "description": "During the 2AM billing job, clients receive 500 Internal Server Error. Connection pool exhausted (100/100 active connections).",
            "category": "database",
            "priority": "Urgent"
        }
    }
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Validate schema fields
    assert "summary" in data and len(data["summary"]) > 5
    assert "possibleCause" in data and len(data["possibleCause"]) > 5
    assert "suggestedSolution" in data and len(data["suggestedSolution"]) > 5
    assert "suggestedCategory" in data
    assert "suggestedPriority" in data
    assert "relevantArticleIds" in data and isinstance(data["relevantArticleIds"], list)
    assert "keyTroubleshootingSteps" in data and len(data["keyTroubleshootingSteps"]) > 0
    assert data["confidence"] in ["low", "medium", "high"]


def test_analyze_ticket_vpn_context():
    """Verify /analyze-ticket produces VPN-specific diagnostic steps."""
    payload = {
        "ticket": {
            "id": 102,
            "title": "GlobalProtect VPN Gateway timeout Error 504 on home Wi-Fi",
            "description": "Staff in Chicago unable to establish VPN tunnel. GlobalProtect reports gateway not responding.",
            "category": "VPN and access",
            "priority": "High"
        }
    }
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "vpn" in data["summary"].lower() or "vpn" in data["possibleCause"].lower()
    assert data["suggestedCategory"] == "VPN and access"


def test_analyze_ticket_validation_error():
    """Verify /analyze-ticket returns HTTP 422 for malformed requests."""
    # Missing required 'ticket' object
    response = client.post("/analyze-ticket", json={"invalid_field": 123})
    assert response.status_code == 422

    # Missing required 'title' within ticket
    response = client.post("/analyze-ticket", json={"ticket": {"id": 1, "description": "Too short"}})
    assert response.status_code == 422


def test_search_endpoint():
    """Verify GET /search returns formatted search results."""
    response = client.get("/search?query=vpn&top_k=3")
    assert response.status_code == 200
    data = response.json()

    assert data["query"] == "vpn"
    assert "count" in data
    assert "results" in data
    assert isinstance(data["results"], list)
    if data["results"]:
        first = data["results"][0]
        assert "article_id" in first
        assert "title" in first
        assert "content" in first
        assert "score" in first


def test_search_endpoint_validation():
    """Verify GET /search requires query parameter with minimum length 2."""
    # Missing query
    response = client.get("/search")
    assert response.status_code == 422

    # Query too short
    response = client.get("/search?query=a")
    assert response.status_code == 422


def test_index_endpoint():
    """Verify POST /index responds with structured index metadata."""
    response = client.post("/index", json={"reindex_all": False})
    assert response.status_code == 200
    data = response.json()

    assert "success" in data
    assert "articles_indexed" in data
    assert "chunks_created" in data
    assert "tickets_indexed" in data
    assert "message" in data


def test_config_constants():
    """Verify embedding dimension constant EMBED_DIM is 768 matching Gemini text-embedding-004."""
    assert settings.EMBED_DIM == 768
    assert settings.EMBED_MODEL == "text-embedding-004"
