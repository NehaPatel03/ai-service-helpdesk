"""
Gemini Embedding Generation Module for DigiPlus AI Service.

Generates dense 768-dimensional vector embeddings using Gemini (gemini-embedding-001)
with output_dimensionality=768 matching pgvector table schemas.
Includes batching, dimension validation, retry with exponential backoff, and rate limit handling.
"""

import logging
import time
from typing import List, Optional
from app.config import settings

logger = logging.getLogger(__name__)

# Pinned constant matching PostgreSQL schema
EMBED_DIM: int = 768


def get_gemini_client():
    """Initializes and returns the official Gemini client if API key is present."""
    if not settings.GEMINI_API_KEY:
        return None
    try:
        from google import genai
        return genai.Client(api_key=settings.GEMINI_API_KEY)
    except Exception as e:
        logger.warning("Could not initialize Gemini client for embeddings: %s", e)
        return None


def embed_text(
    text: str,
    client = None,
    model: Optional[str] = None,
    max_retries: int = 3,
    initial_delay: float = 1.0,
) -> List[float]:
    """
    Generates a single 768-dimensional embedding vector for input text with retry logic.

    Args:
        text: Query or content string to embed.
        client: Optional pre-configured genai.Client.
        model: Model name override (defaults to settings.EMBED_MODEL).
        max_retries: Number of retry attempts on rate limit or transient errors.
        initial_delay: Initial backoff delay in seconds.

    Returns:
        List of 768 float values.
    """
    clean_text = (text or "").strip()
    if not clean_text:
        raise ValueError("Cannot generate embedding for empty text.")

    results = embed_texts(
        texts=[clean_text],
        client=client,
        model=model,
        batch_size=1,
        max_retries=max_retries,
        initial_delay=initial_delay,
    )
    if not results or len(results[0]) != EMBED_DIM:
        raise RuntimeError(f"Embedding generation failed to return a valid {EMBED_DIM}-dim vector.")
    return results[0]


def embed_texts(
    texts: List[str],
    client = None,
    model: Optional[str] = None,
    batch_size: int = 10,
    max_retries: int = 3,
    initial_delay: float = 1.0,
) -> List[List[float]]:
    """
    Generates 768-dimensional embeddings for a batch of texts with retry and exponential backoff.

    Args:
        texts: List of strings to embed.
        client: Optional genai.Client.
        model: Embedding model name (defaults to settings.EMBED_MODEL).
        batch_size: Number of texts per batch request.
        max_retries: Max retry attempts per batch.
        initial_delay: Starting delay in seconds for exponential backoff.

    Returns:
        List of 768-dim float vectors corresponding 1-to-1 with input texts.
    """
    if not texts:
        return []

    target_model = model or settings.EMBED_MODEL
    gemini_client = client or get_gemini_client()
    if gemini_client is None:
        raise RuntimeError("GEMINI_API_KEY is not configured or Gemini client unavailable.")

    from google.genai import types

    all_embeddings: List[List[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = [t.strip() if t and t.strip() else " " for t in texts[i : i + batch_size]]
        delay = initial_delay
        success = False

        for attempt in range(1, max_retries + 1):
            try:
                response = gemini_client.models.embed_content(
                    model=target_model,
                    contents=batch if len(batch) > 1 else batch[0],
                    config=types.EmbedContentConfig(
                        output_dimensionality=EMBED_DIM
                    ),
                )

                # Extract embedding vectors from response
                batch_vectors: List[List[float]] = []
                if hasattr(response, "embeddings") and response.embeddings:
                    batch_vectors = [list(e.values) for e in response.embeddings]
                elif hasattr(response, "embedding") and response.embedding:
                    batch_vectors = [list(response.embedding.values)]
                else:
                    raise ValueError(f"Unexpected response format from {target_model}: {response}")

                # Validate dimensions
                for v in batch_vectors:
                    if len(v) != EMBED_DIM:
                        raise ValueError(f"Expected embedding dimension {EMBED_DIM}, got {len(v)}")

                all_embeddings.extend(batch_vectors)
                success = True
                break

            except Exception as e:
                logger.warning(
                    "Embedding attempt %d/%d for batch [%d:%d] failed: %s",
                    attempt,
                    max_retries,
                    i,
                    i + len(batch),
                    e,
                )
                if attempt == max_retries:
                    raise RuntimeError(
                        f"Failed to generate embeddings after {max_retries} attempts: {e}"
                    )
                time.sleep(delay)
                delay *= 2.0

        if not success:
            raise RuntimeError(f"Embedding failed for batch starting at index {i}")

    return all_embeddings
