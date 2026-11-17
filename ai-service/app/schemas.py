"""
Pydantic Request and Response Schemas for DigiPlus AI Service.
"""

from typing import List, Literal, Optional
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
    engine: Literal["gemini", "heuristic_fallback"] = "gemini"


# ==============================================================================
# Retrieval & Search Schemas
# ==============================================================================
class SearchResultItem(BaseModel):
    chunk_id: int
    article_id: int
    title: str
    content: str
    score: float
    source_type: str = "kb"


class SearchResponse(BaseModel):
    query: str
    count: int
    results: List[SearchResultItem]


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
