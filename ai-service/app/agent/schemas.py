"""
Pydantic schemas for the Phase 3 Tool-Using AI Agent.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class Analysis(BaseModel):
    """Structured incident analysis output produced by the AI Agent."""
    root_cause: str = Field(..., description="Identified or suspected technical root cause of the incident")
    confidence: Literal["low", "medium", "high"] = Field(..., description="Confidence assessment in the diagnosis")
    suggested_steps: List[str] = Field(default_factory=list, description="Ordered technical remediation steps")
    related_ticket_ids: List[int] = Field(default_factory=list, description="IDs of historical incidents cited as evidence")
    kb_sources: List[int] = Field(default_factory=list, description="IDs of knowledge base articles cited as evidence")


class ToolCallRecord(BaseModel):
    """Record of a single tool invocation during an agent execution step."""
    step: int
    tool_name: str
    args: Dict[str, Any] = Field(default_factory=dict)
    result: Any = None
    latency_ms: int = 0
    error: Optional[str] = None


class GroundingResult(BaseModel):
    """Result of grounding validation against tool-collected evidence."""
    is_valid: bool = True
    grounded_kb_ids: List[int] = Field(default_factory=list)
    unsupported_kb_ids: List[int] = Field(default_factory=list)
    grounded_ticket_ids: List[int] = Field(default_factory=list)
    unsupported_ticket_ids: List[int] = Field(default_factory=list)


class AgentExecutionTrace(BaseModel):
    """Comprehensive observability trace of an agent investigation run."""
    ticket_id: int
    steps_count: int = 0
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    final_analysis: Optional[Analysis] = None
    valid_schema: bool = True
    grounding: GroundingResult = Field(default_factory=GroundingResult)
    latency_ms: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    status: Literal["success", "max_steps_reached", "api_error", "validation_failed", "fallback"] = "success"
    used_fallback: bool = False
    error: Optional[str] = None
