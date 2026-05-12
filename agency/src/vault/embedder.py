"""Metin chunk + Gemini embedding (LiteLLM)."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import litellm

from ..config.settings import settings

log = logging.getLogger(__name__)


def chunk_text(text: str) -> list[str]:
    """Basit karakter penceresi overlap ile chunklar."""
    text = (text or "").strip()
    if not text:
        return []
    size = max(200, settings.VAULT_CHUNK_CHARS)
    overlap = max(0, min(settings.VAULT_CHUNK_OVERLAP, size // 2))
    chunks: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        piece = text[i : i + size]
        chunks.append(piece)
        if i + size >= n:
            break
        i += max(1, size - overlap)
    return chunks


def normalize_embedding(vec: list[float], dim: int) -> list[float]:
    if len(vec) == dim:
        return vec
    if len(vec) > dim:
        return vec[:dim]
    return vec + [0.0] * (dim - len(vec))


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


async def embed_batch(texts: list[str]) -> list[list[float] | None]:
    """Batch embedding; API key yoksa veya hata olursa None satirlari."""
    if not texts:
        return []
    if not settings.GOOGLE_GEMINI_API_KEY.strip():
        log.warning("vault.embed.skip_no_gemini_key")
        return [None] * len(texts)
    try:
        resp: dict[str, Any] = await litellm.aembedding(
            model=settings.EMBEDDING_MODEL,
            input=texts,
            api_key=settings.GOOGLE_GEMINI_API_KEY,
            timeout=60,
        )
        data = resp.get("data") or []
        out: list[list[float] | None] = []
        dim = settings.EMBEDDING_DIM
        for item in data:
            emb = item.get("embedding")
            if isinstance(emb, list):
                out.append(normalize_embedding([float(x) for x in emb], dim))
            else:
                out.append(None)
        while len(out) < len(texts):
            out.append(None)
        return out[: len(texts)]
    except Exception as e:
        log.warning("vault.embed.fail", extra={"err": str(e)[:200]})
        return [None] * len(texts)


def vector_literal(vec: list[float]) -> str:
    """Postgres vector parametresi icin string."""
    return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"
