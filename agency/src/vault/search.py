"""Vault uzerinde lexical + vektor hibrit arama."""

from __future__ import annotations

import logging
from typing import Any

from ..config.settings import settings
from ..router.telemetry import get_pool
from .embedder import embed_batch, vector_literal

log = logging.getLogger(__name__)


async def hybrid_search(
    client_id: str,
    query: str,
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Lexical (ILIKE + similarity) + embedding cosinus; basit birlestirme."""
    q = (query or "").strip()
    if len(q) < 2:
        return []

    pool = await get_pool()
    lim_lex = min(limit, 12)
    lim_vec = min(limit, 12)
    safe = "".join(c for c in q if c not in "%_\\")
    pat = f"%{safe}%"

    async with pool.acquire() as conn:
        lex_rows = await conn.fetch(
            """
            SELECT rel_path, chunk_index, body,
                   similarity(lower(body), lower($2::text)) AS sim
            FROM agency.note_embeddings
            WHERE client_id = $1
              AND body ILIKE $3
            ORDER BY sim DESC NULLS LAST
            LIMIT $4
            """,
            client_id,
            q,
            pat,
            lim_lex,
        )

        vec_rows: list[Any] = []
        embs = await embed_batch([q])
        qemb = embs[0] if embs else None
        if qemb is not None:
            lit = vector_literal(qemb)
            try:
                vec_rows = await conn.fetch(
                    """
                    SELECT rel_path, chunk_index, body,
                           (embedding <=> $2::vector) AS dist
                    FROM agency.note_embeddings
                    WHERE client_id = $1
                      AND embedding IS NOT NULL
                    ORDER BY embedding <=> $2::vector
                    LIMIT $3
                    """,
                    client_id,
                    lit,
                    lim_vec,
                )
            except Exception as e:
                log.debug("vault.search.vector_skip", extra={"err": str(e)[:120]})

    scored: dict[tuple[str, int], dict[str, Any]] = {}

    for r in lex_rows:
        key = (r["rel_path"], int(r["chunk_index"]))
        sim = float(r["sim"] or 0.0)
        scored[key] = {
            "rel_path": r["rel_path"],
            "chunk_index": int(r["chunk_index"]),
            "body": r["body"][:2000],
            "lexical_score": round(sim, 4),
            "vector_distance": None,
            "rrf_score": 1.0 / (60 + sim),
        }

    rank = 1
    for r in vec_rows:
        key = (r["rel_path"], int(r["chunk_index"]))
        dist = float(r["dist"])
        cos_sim = max(0.0, 1.0 - dist)
        bonus = 1.0 / (50 + rank)
        rank += 1
        if key in scored:
            scored[key]["vector_distance"] = round(dist, 6)
            scored[key]["rrf_score"] += bonus
            scored[key]["cos_sim"] = round(cos_sim, 4)
        else:
            scored[key] = {
                "rel_path": r["rel_path"],
                "chunk_index": int(r["chunk_index"]),
                "body": r["body"][:2000],
                "lexical_score": None,
                "vector_distance": round(dist, 6),
                "cos_sim": round(cos_sim, 4),
                "rrf_score": bonus,
            }

    out = sorted(scored.values(), key=lambda x: x["rrf_score"], reverse=True)
    return out[:limit]
