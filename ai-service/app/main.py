"""
DigiPlus AI Service - FastAPI Application.

Provides endpoints for:
- Health checks: GET /health
- Ticket Analysis: POST /analyze-ticket
- Knowledge & Incident Search: GET /search
- Indexing & Embedding: POST /index
"""

import json
import logging
import re
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types as genai_types

from app.config import settings
from app.db.connection import check_db_health, get_all_kb_articles, get_db_connection
from app.agent.agent import run_incident_agent
from app.rag.pipeline import retrieve_relevant_chunks
from app.rag.indexer import index_all_articles
from app.schemas import (
    AnalysisResponse,
    AnalyzeTicketRequest,
    HealthResponse,
    IndexRequest,
    IndexResponse,
    SearchResponse,
    SearchResultItem,
    TicketInput,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ai_service")

# Initialize FastAPI app
app = FastAPI(
    title="DigiPlus AI Service",
    description="Python FastAPI service providing Tool-Using LLM Agent, Hybrid Retrieval, and Incident Diagnostics.",
    version=settings.APP_VERSION,
)

# Enable CORS for Next.js web application
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint welcoming visitors and directing to documentation and active endpoints."""
    return {
        "service": "DigiPlus AI Microservice",
        "version": settings.APP_VERSION,
        "status": "online",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "redoc": "/redoc",
            "search": "/search",
            "analyze_ticket": "/analyze-ticket (POST)",
            "index_kb": "/index (POST)",
        },
        "frontend": "http://localhost:3000",
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint reporting API status, database reachability, and active models."""
    db_status = check_db_health()
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        database=db_status,
        model=settings.GEMINI_MODEL,
        embed_model=settings.EMBED_MODEL,
        embed_dim=settings.EMBED_DIM,
    )


@app.post("/analyze-ticket", response_model=AnalysisResponse)
async def analyze_ticket(request: AnalyzeTicketRequest):
    """
    Analyzes an incident ticket using the Phase 3 Tool-Using Gemini Agent.
    Executes function calling across search_similar_tickets, search_kb, get_ticket_history,
    and suggest_assignee, validating grounded references, recording rolling conversation memory,
    and persisting telemetry logs to PostgreSQL.
    """
    ticket = request.ticket
    logger.info("Executing Phase 3 AI Agent for Ticket #%d: '%s' [%s / %s]", ticket.id, ticket.title, ticket.category, ticket.priority)

    try:
        analysis, trace = run_incident_agent(ticket)

        # Build clean numbered remediation guide
        steps_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(analysis.suggested_steps))
        if not steps_text:
            steps_text = "1. Apply standard technical runbook\n2. Verify system recovery"

        return AnalysisResponse(
            summary=f"Incident Analysis: {analysis.root_cause[:120]}...",
            suggestedCategory=ticket.category,
            suggestedPriority=ticket.priority,
            possibleCause=analysis.root_cause,
            suggestedSolution=steps_text,
            relevantArticleIds=analysis.kb_sources,
            keyTroubleshootingSteps=analysis.suggested_steps or ["Inspect service logs", "Execute diagnostic checklist"],
            confidence=analysis.confidence,
            engine="gemini_agent" if not trace.used_fallback else "heuristic_fallback",
            root_cause=analysis.root_cause,
            suggested_steps=analysis.suggested_steps,
            related_ticket_ids=analysis.related_ticket_ids,
            kb_sources=analysis.kb_sources,
            steps_count=trace.steps_count,
            grounding_valid=trace.grounding.is_valid,
        )
    except Exception as e:
        logger.error("Error running Phase 3 incident agent: %s", e, exc_info=True)
        return generate_fallback_analysis(ticket)


def generate_fallback_analysis(ticket: TicketInput) -> AnalysisResponse:
    """Heuristic fallback analysis ensuring 100% reliable responses without external API dependencies."""
    title_lower = f"{ticket.title} {ticket.description}".lower()

    if "vpn" in title_lower or "anyconnect" in title_lower or "globalprotect" in title_lower:
        return AnalysisResponse(
            summary=f"VPN Gateway connectivity degradation affecting {ticket.title}.",
            suggestedCategory="VPN and access",
            suggestedPriority="High",
            possibleCause="SSL tunnel handshake timeout, MTU fragmentation mismatch, or stale client authentication tokens.",
            suggestedSolution="1. Verify client reachability to gateway on port 443\n2. Clear saved credentials in VPN preferences\n3. Disable IPv6 binding and adjust MTU to 1360",
            relevantArticleIds=[11, 5, 12],
            keyTroubleshootingSteps=[
                "Check %LOCALAPPDATA%\\Palo Alto Networks\\GlobalProtect\\PanGPS.log",
                "Disable IPv6 on active Wi-Fi adapter via PowerShell",
                "Switch client gateway selection to secondary failover gateway"
            ],
            confidence="high",
            engine="heuristic_fallback",
        )
    elif "postgres" in title_lower or "rds" in title_lower or "connection pool" in title_lower or "deadlock" in title_lower:
        return AnalysisResponse(
            summary=f"Database resource saturation identified in {ticket.title}.",
            suggestedCategory="database",
            suggestedPriority="Urgent",
            possibleCause="Connection pool exhaustion (max_connections reached) caused by unindexed long-running queries or connection leaks.",
            suggestedSolution="1. Inspect active transactions via pg_stat_activity\n2. Terminate blocking backend queries with pg_terminate_backend\n3. Configure PgBouncer pool multiplexing and verify application connection pooling",
            relevantArticleIds=[31, 35],
            keyTroubleshootingSteps=[
                "Query pg_stat_activity for queries running longer than 60 seconds",
                "Kill locking long-running transactions via pg_terminate_backend",
                "Check CloudWatch DatabaseConnections metric over the past 2 hours"
            ],
            confidence="high",
            engine="heuristic_fallback",
        )
    elif "dns" in title_lower or "nxdomain" in title_lower or "servfail" in title_lower:
        return AnalysisResponse(
            summary=f"Domain name resolution failure affecting {ticket.title}.",
            suggestedCategory="network",
            suggestedPriority="High",
            possibleCause="Internal DNS forwarder timeout, cache corruption, or root hints reachability failure.",
            suggestedSolution="1. Verify DNS resolver responds on UDP port 53\n2. Flush resolver cache on server and client\n3. Restart DNS server service and verify forward lookup zones",
            relevantArticleIds=[3, 1],
            keyTroubleshootingSteps=[
                "Execute nslookup against authoritative domain controller",
                "Flush client DNS cache via ipconfig /flushdns",
                "Restart named or Windows DNS server service"
            ],
            confidence="high",
            engine="heuristic_fallback",
        )
    elif "lockout" in title_lower or "badpwdcount" in title_lower or "password" in title_lower:
        return AnalysisResponse(
            summary=f"Account authentication failure and lockout cycle for {ticket.title}.",
            suggestedCategory="account and password",
            suggestedPriority="Medium",
            possibleCause="Active Directory BadPwdCount loop triggered by mobile device Wi-Fi profile or legacy scheduled task.",
            suggestedSolution="1. Check Security Event ID 4740 on PDC for caller computer\n2. Clear stored stale credentials in Windows Credential Manager\n3. Unlock account via Unlock-ADAccount",
            relevantArticleIds=[26, 27],
            keyTroubleshootingSteps=[
                "Query PDC Security log for Event ID 4740",
                "Purge cached network credentials on caller device",
                "Unlock account in Active Directory Users and Computers"
            ],
            confidence="high",
            engine="heuristic_fallback",
        )
    else:
        return AnalysisResponse(
            summary=f"Incident assessment for {ticket.title}.",
            suggestedCategory=ticket.category if ticket.category != "Other" else "Software",
            suggestedPriority=ticket.priority,
            possibleCause="Service configuration mismatch, process termination, or network resource constraint.",
            suggestedSolution="1. Check service diagnostic logs\n2. Verify resource consumption (CPU/Memory/Disk)\n3. Restart affected service and confirm operational status",
            relevantArticleIds=[1, 21, 36],
            keyTroubleshootingSteps=[
                "Inspect error logs in system event viewer or container stdout",
                "Confirm network reachability and authorization permissions",
                "Apply standard remediation runbook and verify resolution"
            ],
            confidence="medium",
            engine="heuristic_fallback",
        )


@app.get("/search", response_model=SearchResponse)
async def search(
    query: str = Query(..., min_length=2, description="Search query string"),
    category: Optional[str] = Query(None, description="Optional category filter"),
    top_k: int = Query(5, ge=1, le=20, description="Number of results to return"),
):
    """
    Search across knowledge-base runbooks using Hybrid RAG (pgvector + full-text + RRF + Gemini rerank).
    """
    logger.info("Search requested: query='%s', category=%s, top_k=%d", query, category, top_k)

    candidates = retrieve_relevant_chunks(
        query=query,
        category=category,
        top_k=top_k,
    )

    results: List[SearchResultItem] = [
        SearchResultItem(
            chunk_id=c.chunk_id,
            article_id=c.article_id,
            title=c.article_title,
            category=c.category,
            chunk_index=c.chunk_index,
            content=c.content,
            score=c.score,
            method=c.method,
            rank=c.rank,
            source_type="kb",
        )
        for c in candidates
    ]

    return SearchResponse(
        query=query,
        category=category,
        count=len(results),
        results=results,
        use_hybrid=settings.USE_HYBRID,
        use_rerank=settings.USE_RERANK,
    )


@app.post("/index", response_model=IndexResponse)
async def index_data(request: IndexRequest):
    """
    Indexes knowledge-base articles and chunks with embeddings into PostgreSQL pgvector.
    """
    logger.info("Indexing requested (reindex_all=%s)", request.reindex_all)

    conn = get_db_connection()
    if conn is None:
        return IndexResponse(
            success=False,
            articles_indexed=0,
            chunks_created=0,
            tickets_indexed=0,
            message="PostgreSQL database offline. Please configure DATABASE_URL in .env.local",
        )

    try:
        index_result = index_all_articles(conn=conn)

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM tickets;")
            ticket_count = cur.fetchone()[0]

        return IndexResponse(
            success=True,
            articles_indexed=index_result["articles_indexed"],
            chunks_created=index_result["chunks_created"],
            tickets_indexed=ticket_count,
            message=f"Successfully indexed {index_result['articles_indexed']} articles into {index_result['chunks_created']} chunks in {index_result['duration_seconds']}s.",
        )
    except Exception as e:
        logger.error("Error during indexing: %s", e)
        return IndexResponse(
            success=False,
            articles_indexed=0,
            chunks_created=0,
            tickets_indexed=0,
            message=f"Indexing error: {str(e)}",
        )
    finally:
        conn.close()
