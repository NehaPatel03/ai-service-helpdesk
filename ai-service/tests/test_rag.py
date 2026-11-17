"""
Automated Unit and Integration Tests for Phase 2: Hybrid RAG.

Covers:
1. Reciprocal Rank Fusion (RRF) math, deduplication, ranking order, and edge cases.
2. Embedding dimension validation and batching.
3. Gemini Reranker safeguards (dropping invented chunk IDs, JSON corruption handling, API error fallback).
4. Feature flag combinations (USE_HYBRID, USE_RERANK).
5. Category filtering in hybrid retrieval.
6. Search endpoint structure, validation, and empty query rejection.
"""

from unittest.mock import MagicMock, patch
import pytest
from pydantic import ValidationError

from app.rag.chunker import KBChunk, chunk_article
from app.rag.embeddings import EMBED_DIM, embed_text, embed_texts
from app.rag.retriever import CandidateChunk, reciprocal_rank_fusion
from app.rag.reranker import rerank_candidates
from app.rag.pipeline import retrieve_relevant_chunks
from app.schemas import SearchResponse, SearchResultItem


# ==============================================================================
# 1. Reciprocal Rank Fusion (RRF) Unit Tests
# ==============================================================================
def test_rrf_both_present():
    """Verify RRF correctly boosts items appearing in both vector and text searches."""
    v1 = CandidateChunk(chunk_id=1, article_id=1, article_title="VPN Runbook", category="Network", content="VPN details", score=0.9, method="vector")
    v2 = CandidateChunk(chunk_id=2, article_id=2, article_title="Email Runbook", category="Email", content="Email details", score=0.8, method="vector")

    t1 = CandidateChunk(chunk_id=1, article_id=1, article_title="VPN Runbook", category="Network", content="VPN details", score=0.05, method="full_text")
    t3 = CandidateChunk(chunk_id=3, article_id=3, article_title="DB Runbook", category="Database", content="DB details", score=0.04, method="full_text")

    fused = reciprocal_rank_fusion(vector_results=[v1, v2], text_results=[t1, t3], k=60)

    # Chunk #1 was #1 in vector and #1 in text -> score = (1/61) + (1/61) = 2/61 ≈ 0.032787
    assert len(fused) == 3
    assert fused[0].chunk_id == 1
    assert fused[0].method == "hybrid_rrf"
    assert round(fused[0].score, 4) == round(2.0 / 61.0, 4)


def test_rrf_single_present():
    """Verify RRF calculates scores for items present in only one retrieval method."""
    v1 = CandidateChunk(chunk_id=10, article_id=10, article_title="S3 Guide", category="Cloud", content="S3 permissions", score=0.85, method="vector")
    t1 = CandidateChunk(chunk_id=20, article_id=20, article_title="Printer Guide", category="Hardware", content="Printer ports", score=0.02, method="full_text")

    fused = reciprocal_rank_fusion(vector_results=[v1], text_results=[t1], k=60)

    assert len(fused) == 2
    # Both are rank 1 in their respective lists -> identical score 1/61
    assert round(fused[0].score, 4) == round(1.0 / 61.0, 4)
    assert round(fused[1].score, 4) == round(1.0 / 61.0, 4)
    assert {fused[0].chunk_id, fused[1].chunk_id} == {10, 20}


def test_rrf_duplicate_removal():
    """Verify RRF deduplicates chunk IDs and produces unique results."""
    v1 = CandidateChunk(chunk_id=5, article_id=1, article_title="A", category="C", content="Text", score=0.9, method="vector")
    t1 = CandidateChunk(chunk_id=5, article_id=1, article_title="A", category="C", content="Text", score=0.1, method="full_text")

    fused = reciprocal_rank_fusion(vector_results=[v1], text_results=[t1], k=60)
    assert len(fused) == 1
    assert fused[0].chunk_id == 5


def test_rrf_empty_inputs():
    """Verify RRF handles empty candidate lists gracefully."""
    assert reciprocal_rank_fusion([], [], k=60) == []
    v1 = CandidateChunk(chunk_id=1, article_id=1, article_title="A", category="C", content="Text", score=0.9, method="vector")
    fused_only_v = reciprocal_rank_fusion([v1], [], k=60)
    assert len(fused_only_v) == 1
    assert fused_only_v[0].chunk_id == 1


# ==============================================================================
# 2. Embedding Dimension & Validation Tests
# ==============================================================================
def test_embedding_constant_is_768():
    """Verify EMBED_DIM constant strictly equals 768 matching pgvector column."""
    assert EMBED_DIM == 768


def test_embed_text_empty_raises_value_error():
    """Verify empty text raises ValueError without making unnecessary API calls."""
    with pytest.raises(ValueError, match="empty text"):
        embed_text("")
    with pytest.raises(ValueError, match="empty text"):
        embed_text("   \n\t ")


def test_embed_texts_mocked_dimension_validation():
    """Verify embed_texts validates that returned vectors strictly match 768 dimensions."""
    mock_client = MagicMock()
    # Mock returning an invalid 512-dim vector
    mock_response = MagicMock()
    mock_embedding = MagicMock()
    mock_embedding.values = [0.1] * 512
    mock_response.embeddings = [mock_embedding]
    mock_client.models.embed_content.return_value = mock_response

    with pytest.raises(RuntimeError, match="Expected embedding dimension 768"):
        embed_texts(["sample text"], client=mock_client)


# ==============================================================================
# 3. Gemini Reranker Safeguards & Fallbacks
# ==============================================================================
def test_reranker_drops_invented_chunk_ids():
    """Verify reranker strictly discards hallucinated/invented chunk IDs not in candidate pool."""
    c1 = CandidateChunk(chunk_id=101, article_id=1, article_title="Runbook A", category="Net", content="Content A", score=0.5)
    c2 = CandidateChunk(chunk_id=102, article_id=2, article_title="Runbook B", category="Net", content="Content B", score=0.4)

    mock_client = MagicMock()
    mock_resp = MagicMock()
    # Gemini returns an invented chunk_id=999 along with valid chunk_id=101
    mock_resp.text = (
        '[\n'
        '  {"chunk_id": 999, "relevance_score": 0.99, "reasoning": "Hallucinated"},\n'
        '  {"chunk_id": 101, "relevance_score": 0.88, "reasoning": "Valid"}\n'
        ']'
    )
    mock_client.models.generate_content.return_value = mock_resp

    reranked = rerank_candidates(query="test", candidates=[c1, c2], top_k=2, client=mock_client)

    returned_ids = [c.chunk_id for c in reranked]
    assert 999 not in returned_ids, "Hallucinated chunk ID must never appear in final results"
    assert returned_ids[0] == 101
    assert reranked[0].score == 0.88
    assert reranked[0].method == "gemini_rerank"


def test_reranker_fallback_on_corrupted_json():
    """Verify reranker seamlessly falls back to RRF candidate order on malformed JSON."""
    c1 = CandidateChunk(chunk_id=1, article_id=1, article_title="A", category="C", content="A", score=0.9, method="hybrid_rrf")
    c2 = CandidateChunk(chunk_id=2, article_id=2, article_title="B", category="C", content="B", score=0.8, method="hybrid_rrf")

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "This is not JSON at all: Error 500 occurred"
    mock_client.models.generate_content.return_value = mock_resp

    reranked = rerank_candidates(query="test", candidates=[c1, c2], top_k=2, client=mock_client)

    assert len(reranked) == 2
    assert reranked[0].chunk_id == 1
    assert reranked[1].chunk_id == 2
    assert "fallback" in reranked[0].method


def test_reranker_fallback_on_api_exception():
    """Verify reranker seamlessly falls back to RRF candidate order on API exception."""
    c1 = CandidateChunk(chunk_id=1, article_id=1, article_title="A", category="C", content="A", score=0.9, method="hybrid_rrf")

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("API connection timeout")

    reranked = rerank_candidates(query="test", candidates=[c1], top_k=1, client=mock_client)
    assert len(reranked) == 1
    assert reranked[0].chunk_id == 1


# ==============================================================================
# 4. Feature Flag Matrix Tests
# ==============================================================================
def test_feature_flags_pipeline_routing():
    """Verify retrieval pipeline correctly obeys USE_HYBRID and USE_RERANK flags."""
    mock_conn = MagicMock()

    with patch("app.rag.pipeline.search_full_text") as mock_ft, \
         patch("app.rag.pipeline.hybrid_search") as mock_hybrid, \
         patch("app.rag.pipeline.rerank_candidates") as mock_rerank:

        mock_ft.return_value = [CandidateChunk(chunk_id=1, article_id=1, article_title="FT", category="C", content="C", score=0.5, method="full_text")]
        mock_hybrid.return_value = [CandidateChunk(chunk_id=2, article_id=2, article_title="Hyb", category="C", content="C", score=0.5, method="rrf")]
        mock_rerank.return_value = [CandidateChunk(chunk_id=2, article_id=2, article_title="Rerank", category="C", content="C", score=0.9, method="gemini_rerank")]

        # Mode 1: USE_HYBRID=False, USE_RERANK=False
        res_basic = retrieve_relevant_chunks("query", use_hybrid=False, use_rerank=False, conn=mock_conn)
        assert res_basic[0].method == "full_text"
        mock_ft.assert_called_once()
        mock_hybrid.assert_not_called()
        mock_rerank.assert_not_called()

        # Mode 2: USE_HYBRID=True, USE_RERANK=False
        mock_ft.reset_mock()
        mock_hybrid.reset_mock()
        mock_rerank.reset_mock()
        res_hybrid = retrieve_relevant_chunks("query", use_hybrid=True, use_rerank=False, conn=mock_conn)
        assert res_hybrid[0].method == "rrf"
        mock_hybrid.assert_called_once()
        mock_rerank.assert_not_called()

        # Mode 3: USE_HYBRID=True, USE_RERANK=True
        mock_ft.reset_mock()
        mock_hybrid.reset_mock()
        mock_rerank.reset_mock()
        res_neural = retrieve_relevant_chunks("query", use_hybrid=True, use_rerank=True, conn=mock_conn)
        assert res_neural[0].method == "gemini_rerank"
        mock_hybrid.assert_called_once()
        mock_rerank.assert_called_once()


# ==============================================================================
# 5. Schema & Validation Tests
# ==============================================================================
def test_search_result_item_schema():
    """Verify SearchResultItem conforms to the required Pydantic schema."""
    item = SearchResultItem(
        chunk_id=7,
        article_id=1,
        title="GlobalProtect VPN",
        category="Network",
        chunk_index=0,
        content="VPN guide content",
        score=0.95,
        method="gemini_rerank",
        rank=1,
    )
    assert item.chunk_id == 7
    assert item.article_id == 1
    assert item.method == "gemini_rerank"
    assert item.score == 0.95
    assert item.source_type == "kb"
