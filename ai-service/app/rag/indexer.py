"""
Knowledge Base Article Indexer for DigiPlus AI Service.

Reads articles from kb_articles table in PostgreSQL, chunks them using chunker,
generates dense 768-dim embeddings with Gemini, and stores them in kb_chunks with
vector embeddings and generated full-text tsvector search tokens.
"""

import logging
import time
from typing import Any, Dict, List, Optional
import psycopg2
from psycopg2.extras import execute_batch, RealDictCursor

from app.rag.chunker import chunk_article, KBChunk
from app.rag.embeddings import embed_texts, EMBED_DIM
from app.db.connection import get_db_connection

logger = logging.getLogger(__name__)


def index_article(
    article: Dict[str, Any],
    conn,
    gemini_client = None,
    batch_size: int = 10,
) -> int:
    """
    Chunks and indexes a single knowledge base article idempotently.

    Args:
        article: Dict containing 'id', 'title', 'body', 'category'.
        conn: Open psycopg2 connection to PostgreSQL.
        gemini_client: Optional pre-configured genai.Client.
        batch_size: Embedding batch size.

    Returns:
        Number of chunks indexed for this article.
    """
    article_id = article["id"]
    title = article["title"]
    body = article.get("body", "")
    category = article.get("category", "General")

    # 1. Chunk article
    chunks: List[KBChunk] = chunk_article(
        article_id=article_id,
        title=title,
        body=body,
        category=category,
    )
    if not chunks:
        logger.info("Article #%d has no indexable content.", article_id)
        return 0

    # 2. Generate embeddings
    contents = [c.content for c in chunks]
    embeddings = embed_texts(contents, client=gemini_client, batch_size=batch_size)

    # 3. Insert into PostgreSQL (idempotent: delete previous chunks first)
    with conn.cursor() as cur:
        cur.execute("DELETE FROM kb_chunks WHERE article_id = %s;", (article_id,))

        insert_sql = """
            INSERT INTO kb_chunks (article_id, chunk_index, content, embedding)
            VALUES (%s, %s, %s, %s::vector);
        """
        records = [
            (c.article_id, c.chunk_index, c.content, emb)
            for c, emb in zip(chunks, embeddings)
        ]
        execute_batch(cur, insert_sql, records)
        conn.commit()

    logger.info("Indexed %d chunks for article #%d ('%s')", len(chunks), article_id, title)
    return len(chunks)


def index_all_articles(
    conn = None,
    gemini_client = None,
    batch_size: int = 10,
) -> Dict[str, Any]:
    """
    Indexes all articles currently stored in kb_articles table into kb_chunks.

    Returns:
        Summary dict containing total articles, total chunks, and elapsed time.
    """
    start_time = time.time()
    db_conn = conn or get_db_connection()
    if db_conn is None:
        raise RuntimeError("Could not connect to PostgreSQL database for indexing.")

    try:
        with db_conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, title, body, category FROM kb_articles ORDER BY id ASC;")
            articles = cur.fetchall()

        logger.info("Found %d articles in kb_articles to index.", len(articles))
        total_chunks = 0

        for art in articles:
            chunks_count = index_article(
                article=dict(art),
                conn=db_conn,
                gemini_client=gemini_client,
                batch_size=batch_size,
            )
            total_chunks += chunks_count

        elapsed = round(time.time() - start_time, 2)
        logger.info("Indexing complete: %d articles, %d chunks in %.2fs", len(articles), total_chunks, elapsed)

        return {
            "status": "success",
            "articles_indexed": len(articles),
            "chunks_created": total_chunks,
            "embed_dim": EMBED_DIM,
            "duration_seconds": elapsed,
        }
    finally:
        if conn is None and db_conn:
            db_conn.close()
