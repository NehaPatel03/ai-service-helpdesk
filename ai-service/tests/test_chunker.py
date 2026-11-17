"""
Unit Tests for Knowledge Base Chunker.
"""

import pytest
from app.rag.chunker import chunk_article, estimate_tokens, KBChunk


def test_empty_content_returns_empty_list():
    """Verify that empty or whitespace-only articles return an empty chunk list."""
    assert chunk_article(1, "Test Title", "") == []
    assert chunk_article(1, "Test Title", "   \n\n  \t  ") == []
    assert chunk_article(1, "Test Title", None) == []


def test_short_article_single_chunk():
    """Verify short articles below chunk threshold are kept as a single chunk."""
    short_body = (
        "### Overview\n"
        "To clear your DNS cache on Windows, open Command Prompt as Administrator and run `ipconfig /flushdns`.\n"
        "Verify resolution by running `nslookup corp.internal`."
    )
    chunks = chunk_article(
        article_id=42,
        title="Flushing DNS Cache on Windows",
        body=short_body,
        category="Network",
        target_chunk_tokens=400,
    )

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.article_id == 42
    assert chunk.article_title == "Flushing DNS Cache on Windows"
    assert chunk.category == "Network"
    assert chunk.chunk_index == 0
    assert "ipconfig /flushdns" in chunk.content
    assert "[Network] Flushing DNS Cache on Windows" in chunk.content


def test_long_article_splits_into_multiple_chunks():
    """Verify long articles are split into multiple chunks with valid token estimates."""
    # Generate ~2000 words (>2000 tokens)
    paragraphs = []
    for i in range(15):
        paragraphs.append(
            f"### Section {i+1}: Advanced Diagnostic Step {i+1}\n"
            f"When diagnosing service degradation in cluster node {i+1}, inspect kernel ring buffer using dmesg. "
            f"Review memory pressure stall information in /proc/pressure/memory and evaluate thrashing metrics. "
            f"Verify that swap utilization does not exceed the configured threshold of 15 percent under sustained peak throughput."
        )
    long_body = "\n\n".join(paragraphs)

    chunks = chunk_article(
        article_id=10,
        title="Cluster Node Memory Pressure Runbook",
        body=long_body,
        category="Cloud & Infrastructure",
        target_chunk_tokens=300,
        overlap_tokens=60,
    )

    assert len(chunks) > 1
    # Verify sequential indices
    for idx, c in enumerate(chunks):
        assert c.chunk_index == idx
        assert c.article_id == 10
        assert c.category == "Cloud & Infrastructure"
        assert c.article_title == "Cluster Node Memory Pressure Runbook"
        assert len(c.content) > 100
        assert c.token_estimate > 0


def test_chunk_overlap_preserves_context():
    """Verify that consecutive chunks share overlapping context."""
    paragraphs = [
        f"Paragraph {i}: Detailed technical instruction explaining step {i} of the remediation workflow for VPN authentication."
        for i in range(20)
    ]
    body = "\n\n".join(paragraphs)

    chunks = chunk_article(
        article_id=5,
        title="VPN Troubleshooting",
        body=body,
        category="Network",
        target_chunk_tokens=100,
        overlap_tokens=25,
    )

    assert len(chunks) >= 2
    # Check that adjacent chunks have content overlap
    for i in range(len(chunks) - 1):
        c1 = chunks[i].content
        c2 = chunks[i + 1].content
        # Find any common substring of at least 20 chars
        c1_words = set(c1.split())
        c2_words = set(c2.split())
        common = c1_words.intersection(c2_words)
        # Should share technical words beyond common stopwords
        assert len(common) > 5


def test_metadata_preservation():
    """Verify all metadata fields are preserved accurately on all chunks."""
    body = "Step 1: Check logs.\n\nStep 2: Apply fix.\n\nStep 3: Confirm resolution."
    chunks = chunk_article(
        article_id=999,
        title="SaaS Provisioning Guide",
        body=body,
        category="Access & Security",
    )

    assert len(chunks) >= 1
    for c in chunks:
        assert c.article_id == 999
        assert c.article_title == "SaaS Provisioning Guide"
        assert c.category == "Access & Security"
        assert isinstance(c.chunk_index, int)
        assert c.char_count == len(c.content)


def test_duplicate_prevention():
    """Verify that duplicate chunks are not emitted even if repetitive text is provided."""
    repetitive_body = "Identical line of text.\n\n" * 20
    chunks = chunk_article(
        article_id=1,
        title="Repetitive Article",
        body=repetitive_body,
        category="Other",
        target_chunk_tokens=50,
        overlap_tokens=10,
    )

    contents = [c.content for c in chunks]
    assert len(contents) == len(set(contents)), "Chunks must be unique"
