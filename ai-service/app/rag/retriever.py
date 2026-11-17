"""
Hybrid Retrieval Module for DigiPlus AI Service.

Combines pgvector cosine similarity search with PostgreSQL full-text search
using Reciprocal Rank Fusion (RRF).
"""

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from psycopg2.extras import RealDictCursor

from app.rag.embeddings import embed_text
from app.db.connection import get_db_connection

logger = logging.getLogger(__name__)


class CandidateChunk(BaseModel):
    """Candidate knowledge base chunk returned from retrieval stages."""
    chunk_id: int
    article_id: int
    article_title: str
    category: str
    chunk_index: int = 0
    content: str
    score: float = 0.0
    method: str = "hybrid"
    rank: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


def search_vector(
    conn,
    query: str,
    category: Optional[str] = None,
    top_k: int = 20,
    client = None,
) -> List[CandidateChunk]:
    """
    Performs dense semantic vector search in pgvector using cosine distance.

    Args:
        conn: Open psycopg2 database connection.
        query: User search text or incident title/description.
        category: Optional category filter.
        top_k: Number of candidates to return.
        client: Optional genai.Client.

    Returns:
        List of CandidateChunk instances ranked by cosine similarity (highest first).
    """
    clean_query = (query or "").strip()
    if not clean_query:
        return []

    # Generate query embedding vector (768 dim)
    query_vector = embed_text(clean_query, client=client)

    sql = """
        SELECT c.id as chunk_id, c.article_id, a.title as article_title, a.category,
               c.chunk_index, c.content,
               1.0 - (c.embedding <=> %s::vector) AS score
        FROM kb_chunks c
        JOIN kb_articles a ON c.article_id = a.id
        WHERE (%s IS NULL OR a.category ILIKE %s)
        ORDER BY c.embedding <=> %s::vector ASC
        LIMIT %s;
    """
    cat_param = f"%{category.strip()}%" if category and category != "All" else None

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, (query_vector, cat_param, cat_param, query_vector, top_k))
        rows = cur.fetchall()

    results: List[CandidateChunk] = []
    for rank, r in enumerate(rows, start=1):
        results.append(
            CandidateChunk(
                chunk_id=r["chunk_id"],
                article_id=r["article_id"],
                article_title=r["article_title"],
                category=r["category"],
                chunk_index=r["chunk_index"],
                content=r["content"],
                score=float(r["score"]),
                method="vector",
                rank=rank,
            )
        )
    return results


def search_full_text(
    conn,
    query: str,
    category: Optional[str] = None,
    top_k: int = 20,
) -> List[CandidateChunk]:
    """
    Performs sparse keyword full-text search using PostgreSQL tsvector and ts_rank_cd.

    Args:
        conn: Open psycopg2 database connection.
        query: User search text or incident title/description.
        category: Optional category filter.
        top_k: Number of candidates to return.

    Returns:
        List of CandidateChunk instances ranked by ts_rank (highest first).
    """
    clean_query = (query or "").strip()
    if not clean_query:
        return []

    cat_param = f"%{category.strip()}%" if category and category != "All" else None

    # Try plainto_tsquery first (robust against special characters)
    sql_tsquery = """
        SELECT c.id as chunk_id, c.article_id, a.title as article_title, a.category,
               c.chunk_index, c.content,
               ts_rank_cd(c.tsv, query) AS score
        FROM kb_chunks c
        JOIN kb_articles a ON c.article_id = a.id,
             plainto_tsquery('english', %s) query
        WHERE c.tsv @@ query
          AND (%s IS NULL OR a.category ILIKE %s)
        ORDER BY score DESC
        LIMIT %s;
    """

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql_tsquery, (clean_query, cat_param, cat_param, top_k))
        rows = cur.fetchall()

        # If plainto_tsquery returned 0 matches, fallback to ILIKE substring matching
        if not rows:
            fallback_sql = """
                SELECT c.id as chunk_id, c.article_id, a.title as article_title, a.category,
                       c.chunk_index, c.content,
                       0.1 AS score
                FROM kb_chunks c
                JOIN kb_articles a ON c.article_id = a.id
                WHERE (c.content ILIKE %s OR a.title ILIKE %s)
                  AND (%s IS NULL OR a.category ILIKE %s)
                ORDER BY c.id ASC
                LIMIT %s;
            """
            search_pattern = f"%{clean_query[:50]}%"
            cur.execute(fallback_sql, (search_pattern, search_pattern, cat_param, cat_param, top_k))
            rows = cur.fetchall()

    results: List[CandidateChunk] = []
    for rank, r in enumerate(rows, start=1):
        results.append(
            CandidateChunk(
                chunk_id=r["chunk_id"],
                article_id=r["article_id"],
                article_title=r["article_title"],
                category=r["category"],
                chunk_index=r["chunk_index"],
                content=r["content"],
                score=float(r["score"]),
                method="full_text",
                rank=rank,
            )
        )
    return results


def reciprocal_rank_fusion(
    vector_results: List[CandidateChunk],
    text_results: List[CandidateChunk],
    k: int = 60,
) -> List[CandidateChunk]:
    """
    Combines dense vector and sparse full-text retrieval results using Reciprocal Rank Fusion.

    Formula for each document d:
        RRF_Score(d) = sum_{m in {vector, text}} 1.0 / (k + rank_m(d))

    Args:
        vector_results: List of CandidateChunk from vector search.
        text_results: List of CandidateChunk from full-text search.
        k: Smoothing constant (default 60).

    Returns:
        Deduplicated List of CandidateChunk ranked by descending RRF score.
    """
    rrf_scores: Dict[int, float] = {}
    chunk_map: Dict[int, CandidateChunk] = {}
    methods_seen: Dict[int, List[str]] = {}
    rank_details: Dict[int, Dict[str, int]] = {}

    # Process vector results
    for rank, item in enumerate(vector_results, start=1):
        cid = item.chunk_id
        chunk_map[cid] = item
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (k + rank))
        methods_seen.setdefault(cid, []).append("vector")
        rank_details.setdefault(cid, {})["vector_rank"] = rank

    # Process text results
    for rank, item in enumerate(text_results, start=1):
        cid = item.chunk_id
        if cid not in chunk_map:
            chunk_map[cid] = item
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (k + rank))
        methods_seen.setdefault(cid, []).append("full_text")
        rank_details.setdefault(cid, {})["text_rank"] = rank

    # Sort chunks by RRF score descending
    sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)

    fused_results: List[CandidateChunk] = []
    for final_rank, cid in enumerate(sorted_chunk_ids, start=1):
        base_item = chunk_map[cid]
        methods = methods_seen[cid]
        method_str = "hybrid_rrf" if len(methods) > 1 else f"rrf_{methods[0]}"

        meta = dict(base_item.metadata)
        meta.update(rank_details[cid])
        meta["raw_rrf_score"] = rrf_scores[cid]

        fused_results.append(
            CandidateChunk(
                chunk_id=base_item.chunk_id,
                article_id=base_item.article_id,
                article_title=base_item.article_title,
                category=base_item.category,
                chunk_index=base_item.chunk_index,
                content=base_item.content,
                score=round(rrf_scores[cid], 6),
                method=method_str,
                rank=final_rank,
                metadata=meta,
            )
        )

    return fused_results


def hybrid_search(
    conn,
    query: str,
    category: Optional[str] = None,
    top_k: int = 20,
    k_rrf: int = 60,
    client = None,
) -> List[CandidateChunk]:
    """
    Executes parallel vector and full-text searches, fusing candidates with RRF.

    Args:
        conn: Open psycopg2 connection.
        query: Query string.
        category: Optional category filter.
        top_k: Number of candidates to retrieve from each method.
        k_rrf: RRF smoothing constant (default 60).
        client: Optional genai.Client.

    Returns:
        Fused list of CandidateChunk instances.
    """
    vector_candidates = search_vector(
        conn=conn,
        query=query,
        category=category,
        top_k=top_k,
        client=client,
    )
    text_candidates = search_full_text(
        conn=conn,
        query=query,
        category=category,
        top_k=top_k,
    )

    fused = reciprocal_rank_fusion(
        vector_results=vector_candidates,
        text_results=text_candidates,
        k=k_rrf,
    )
    return fused
