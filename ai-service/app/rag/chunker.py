"""
Knowledge Base Article Chunker for DigiPlus AI Service.

Splits technical runbooks and documentation into overlapping chunks of
approximately 300-500 tokens (1200-2000 characters) while preserving markdown
structure, sentence boundaries, and article metadata.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class KBChunk(BaseModel):
    """Structured representation of an indexed knowledge base chunk."""
    article_id: int
    article_title: str
    category: str
    chunk_index: int
    content: str = Field(..., min_length=1)
    char_count: int = 0
    token_estimate: int = 0


def estimate_tokens(text: str) -> int:
    """Estimates token count using standard ~4 chars/token heuristic."""
    return max(1, len(text.strip()) // 4)


def chunk_article(
    article_id: int,
    title: str,
    body: str,
    category: str = "General",
    target_chunk_tokens: int = 400,
    overlap_tokens: int = 80,
) -> List[KBChunk]:
    """
    Splits an article into overlapping chunks preserving context and metadata.

    Args:
        article_id: Unique identifier of the parent article.
        title: Title of the article (prepended to chunk context).
        body: Markdown body of the article.
        category: Article technical category.
        target_chunk_tokens: Target token count per chunk (~300-500 tokens).
        overlap_tokens: Overlap token count between successive chunks (~50-100 tokens).

    Returns:
        List of KBChunk instances with sequential chunk_index.
    """
    clean_body = (body or "").strip()
    if not clean_body:
        return []

    target_chars = target_chunk_tokens * 4
    overlap_chars = overlap_tokens * 4

    # Context header included in every chunk to ground embeddings
    header = f"[{category}] {title}\n\n"

    # Handle short articles: if body comfortably fits in one chunk, do not split
    if len(clean_body) <= target_chars:
        full_content = f"{header}{clean_body}".strip()
        return [
            KBChunk(
                article_id=article_id,
                article_title=title,
                category=category,
                chunk_index=0,
                content=full_content,
                char_count=len(full_content),
                token_estimate=estimate_tokens(full_content),
            )
        ]

    # Split into structural blocks (paragraphs, markdown sections)
    paragraphs = [p.strip() for p in clean_body.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [clean_body]

    raw_chunks: List[str] = []
    current_chunk: List[str] = []
    current_length = 0

    for para in paragraphs:
        para_len = len(para)

        # If a single paragraph is longer than target_chars, split by lines/sentences
        if para_len > target_chars:
            sentences = [s.strip() for s in para.replace("\n", " ").split(". ") if s.strip()]
            for s in sentences:
                s_with_period = f"{s}." if not s.endswith(".") else s
                if current_length + len(s_with_period) > target_chars and current_chunk:
                    chunk_text = " ".join(current_chunk).strip()
                    if chunk_text:
                        raw_chunks.append(chunk_text)
                    # Compute overlap from end of current chunk
                    overlap_text = chunk_text[-overlap_chars:] if len(chunk_text) > overlap_chars else ""
                    current_chunk = [overlap_text, s_with_period] if overlap_text else [s_with_period]
                    current_length = sum(len(x) for x in current_chunk) + len(current_chunk)
                else:
                    current_chunk.append(s_with_period)
                    current_length += len(s_with_period) + 1
        elif current_length + para_len > target_chars and current_chunk:
            chunk_text = "\n\n".join(current_chunk).strip()
            if chunk_text:
                raw_chunks.append(chunk_text)
            # Retain overlap from previous chunk
            overlap_text = chunk_text[-overlap_chars:] if len(chunk_text) > overlap_chars else ""
            current_chunk = [overlap_text, para] if overlap_text else [para]
            current_length = sum(len(x) for x in current_chunk) + len(current_chunk)
        else:
            current_chunk.append(para)
            current_length += para_len + 2

    if current_chunk:
        chunk_text = "\n\n".join(current_chunk).strip()
        if chunk_text:
            raw_chunks.append(chunk_text)

    # Deduplicate and build final KBChunk objects
    chunks: List[KBChunk] = []
    seen_contents = set()
    idx = 0

    for raw in raw_chunks:
        clean_chunk = raw.strip()
        if not clean_chunk or clean_chunk in seen_contents:
            continue
        seen_contents.add(clean_chunk)

        full_content = f"{header}{clean_chunk}".strip()
        chunks.append(
            KBChunk(
                article_id=article_id,
                article_title=title,
                category=category,
                chunk_index=idx,
                content=full_content,
                char_count=len(full_content),
                token_estimate=estimate_tokens(full_content),
            )
        )
        idx += 1

    return chunks
