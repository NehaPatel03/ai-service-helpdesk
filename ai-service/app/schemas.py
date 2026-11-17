"""
Pydantic Request and Response Schemas for DigiPlus AI Service.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# ==============================================================================
# Health Check Schemas
# ==============================================================================
class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    database: str
    model: str
    embed_model: str
    embed_dim: int


# ==============================================================================
# Ticket & Analysis Schemas
# ==============================================================================
class TicketInput(BaseModel):
    id: int
    title: str = Field(..., min_length=3)
    description: str = Field(..., min_length=5)
    category: str = "Other"
    priority: str = "Medium"


class AnalyzeTicketRequest(BaseModel):
    ticket: TicketInput


class AnalysisResponse(BaseModel):
    summary: str
    suggestedCategory: str
    suggestedPriority: str
    possibleCause: str
    suggestedSolution: str
    relevantArticleIds: List[int] = Field(default_factory=list)
    keyTroubleshootingSteps: List[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "high"
    engine: str = "gemini_agent"

    # Phase 3 Structured Output Fields
    root_cause: Optional[str] = None
    suggested_steps: List[str] = Field(default_factory=list)
    related_ticket_ids: List[int] = Field(default_factory=list)
    kb_sources: List[int] = Field(default_factory=list)
    steps_count: Optional[int] = None
    grounding_valid: Optional[bool] = None
    agent_run_id: Optional[int] = None


# ==============================================================================
# Retrieval & Search Schemas
# ==============================================================================
class SearchResultItem(BaseModel):
    chunk_id: int
    article_id: int
    title: str
    category: str = "General"
    chunk_index: int = 0
    content: str
    score: float
    method: str = "hybrid"
    rank: Optional[int] = None
    source_type: str = "kb"


class SearchResponse(BaseModel):
    query: str
    category: Optional[str] = None
    count: int
    results: List[SearchResultItem]
    use_hybrid: bool = True
    use_rerank: bool = True


# ==============================================================================
# Indexing Schemas
# ==============================================================================
class IndexRequest(BaseModel):
    reindex_all: bool = False


class IndexResponse(BaseModel):
    success: bool
    articles_indexed: int
    chunks_created: int
    tickets_indexed: int
    message: str
