"""
RAG Pipeline Orchestrator for DigiPlus AI Service.

Controls the full retrieval pipeline based on USE_HYBRID and USE_RERANK feature flags:
- USE_HYBRID=False, USE_RERANK=False: Basic full-text keyword retrieval.
- USE_HYBRID=True,  USE_RERANK=False: Dense vector + sparse full-text fused via RRF.
- USE_HYBRID=True,  USE_RERANK=True:  Hybrid RRF retrieval followed by Gemini neural reranking.
"""

import logging
from typing import List, Optional

from app.config import settings
from app.db.connection import get_db_connection
from app.rag.retriever import (
    CandidateChunk,
    search_full_text,
    hybrid_search,
)
from app.rag.reranker import rerank_candidates

logger = logging.getLogger(__name__)


def retrieve_relevant_chunks(
    query: str,
    category: Optional[str] = None,
    top_k: int = 5,
    use_hybrid: Optional[bool] = None,
    use_rerank: Optional[bool] = None,
    conn = None,
    client = None,
) -> List[CandidateChunk]:
    """
    Retrieves the most relevant knowledge base chunks for an incident or query.

    Args:
        query: Problem description, ticket title, or keyword search query.
        category: Optional category filter.
        top_k: Final number of chunks to return (default 5).
        use_hybrid: Override for settings.USE_HYBRID flag.
        use_rerank: Override for settings.USE_RERANK flag.
        conn: Optional active database connection.
        client: Optional Gemini client.

    Returns:
        List of CandidateChunk instances ranked by relevance.
    """
    clean_query = (query or "").strip()
    if not clean_query:
        return []

    hybrid_flag = settings.USE_HYBRID if use_hybrid is None else use_hybrid
    rerank_flag = settings.USE_RERANK if use_rerank is None else use_rerank

    db_conn = conn or get_db_connection()
    if db_conn is None:
        logger.warning("Database unavailable for retrieval.")
        return []

    try:
        # 1. Mode: Basic Full-Text Retrieval
        if not hybrid_flag:
            logger.info("Retrieval: Basic full-text search (USE_HYBRID=False)")
            return search_full_text(
                conn=db_conn,
                query=clean_query,
                category=category,
                top_k=top_k,
            )

        # 2. Mode: Hybrid Search (Vector + Full-Text + RRF)
        logger.info("Retrieval: Hybrid vector + full-text search with RRF")
        # Fetch up to 20 candidates for fusion and potential reranking
        fused_candidates = hybrid_search(
            conn=db_conn,
            query=clean_query,
            category=category,
            top_k=20,
            client=client,
        )

        # 3. Mode: Neural Reranking (if USE_RERANK is enabled)
        if rerank_flag:
            logger.info("Retrieval: Applying Gemini neural reranking (USE_RERANK=True)")
            return rerank_candidates(
                query=clean_query,
                candidates=fused_candidates,
                top_k=top_k,
                client=client,
            )

        # If reranking disabled, return top_k RRF candidates directly
        return fused_candidates[:top_k]

    finally:
        if conn is None and db_conn:
            db_conn.close()
