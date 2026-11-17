"""
Gemini Neural Reranker Module for DigiPlus AI Service.

Reranks hybrid search candidate chunks using Gemini to compute deep relevance
scores and re-order candidate runbooks before final selection.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.config import settings
from app.rag.retriever import CandidateChunk

logger = logging.getLogger(__name__)


def rerank_candidates(
    query: str,
    candidates: List[CandidateChunk],
    top_k: int = 5,
    client = None,
) -> List[CandidateChunk]:
    """
    Reranks candidate chunks using Gemini with strict safeguards.

    Safeguards:
    1. Only top 20 candidates from RRF are sent to prevent context overflow.
    2. Validates every returned chunk_id against the input candidate list.
    3. Drops any invented/hallucinated chunk IDs.
    4. Automatically falls back to RRF ranking if Gemini reranking fails or returns invalid JSON.
    5. Preserves all original chunk and article metadata.

    Args:
        query: User search query or incident title/description.
        candidates: Pre-ranked candidates from RRF.
        top_k: Number of final chunks to return (default 5).
        client: Optional genai.Client instance.

    Returns:
        List of CandidateChunk instances sorted by reranked relevance.
    """
    if not candidates:
        return []

    # If only 1 candidate, no need for deep reranking
    if len(candidates) == 1:
        c = candidates[0].model_copy()
        c.method = "rerank_pass"
        return [c]

    # Select top 20 candidates for neural reranking
    pool = candidates[:20]
    candidate_map: Dict[int, CandidateChunk] = {c.chunk_id: c for c in pool}

    # Initialize Gemini client if available
    gemini_client = client
    if gemini_client is None and settings.GEMINI_API_KEY:
        try:
            from google import genai
            gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        except Exception as e:
            logger.warning("Could not initialize Gemini client for reranking: %s", e)

    if gemini_client is None:
        logger.info("Gemini client unavailable for reranking; using RRF fallback order.")
        return [c.model_copy() for c in candidates[:top_k]]

    from google.genai import types

    # Compact representation for LLM reranker
    items_for_prompt = [
        {
            "chunk_id": c.chunk_id,
            "article_id": c.article_id,
            "title": c.article_title,
            "category": c.category,
            "content": c.content[:400] + ("..." if len(c.content) > 400 else ""),
        }
        for c in pool
    ]

    prompt = f"""You are an expert IT Service Desk retrieval reranker.
Rank the following technical knowledge base candidate chunks by their direct relevance to resolving the given support query.

Query: "{query}"

Candidates to Rank:
{json.dumps(items_for_prompt, indent=2)}

Instructions:
1. Only rank the candidate chunk_ids provided above. NEVER invent or hallucinate new IDs.
2. Assign a relevance_score between 0.0 and 1.0 (1.0 = most relevant).
3. Return ONLY a valid JSON array of objects sorted by relevance_score descending:
[
  {{"chunk_id": 123, "relevance_score": 0.95, "reasoning": "Direct match for VPN gateway timeout"}}
]"""

    models_to_try = [settings.GEMINI_MODEL, "gemini-3.1-flash-lite", "gemini-3.8-flash"]
    reranked_data: Optional[List[Dict[str, Any]]] = None

    for model_name in models_to_try:
        try:
            response = gemini_client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,
                ),
            )
            raw_text = response.text or ""
            cleaned = re.sub(r"^```json\s*", "", raw_text, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned).strip()
            parsed = json.loads(cleaned)

            if isinstance(parsed, list) and len(parsed) > 0:
                reranked_data = parsed
                break
        except Exception as e:
            logger.warning("Gemini reranking attempt with %s failed: %s", model_name, e)

    # If reranking failed or gave invalid response, fall back to RRF ranking
    if not reranked_data:
        logger.info("Falling back to RRF candidate order.")
        results = []
        for rank, c in enumerate(candidates[:top_k], start=1):
            item = c.model_copy()
            item.method = f"{item.method}_fallback"
            item.rank = rank
            results.append(item)
        return results

    # Process and validate returned rankings
    results: List[CandidateChunk] = []
    seen_chunk_ids = set()

    for item in reranked_data:
        if not isinstance(item, dict):
            continue
        cid = item.get("chunk_id")

        # Safeguard: Validate ID against candidate pool
        if cid is None or cid not in candidate_map or cid in seen_chunk_ids:
            continue

        seen_chunk_ids.add(cid)
        original = candidate_map[cid]

        try:
            rel_score = float(item.get("relevance_score", 0.5))
        except (ValueError, TypeError):
            rel_score = 0.5

        meta = dict(original.metadata)
        meta["rerank_reasoning"] = item.get("reasoning", "")
        meta["pre_rerank_score"] = original.score
        meta["pre_rerank_method"] = original.method

        results.append(
            CandidateChunk(
                chunk_id=original.chunk_id,
                article_id=original.article_id,
                article_title=original.article_title,
                category=original.category,
                chunk_index=original.chunk_index,
                content=original.content,
                score=round(rel_score, 4),
                method="gemini_rerank",
                rank=len(results) + 1,
                metadata=meta,
            )
        )

        if len(results) >= top_k:
            break

    # If any candidate slots remain, fill with remaining RRF candidates
    if len(results) < top_k:
        for c in pool:
            if c.chunk_id not in seen_chunk_ids:
                item = c.model_copy()
                item.rank = len(results) + 1
                item.method = "rrf_fill"
                results.append(item)
                seen_chunk_ids.add(c.chunk_id)
                if len(results) >= top_k:
                    break

    return results
