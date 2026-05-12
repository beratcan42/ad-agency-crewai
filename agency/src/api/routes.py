"""API rotaları — Aşama 2 minimal: /healthz, /version, /brief (placeholder)."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..config.settings import settings
from ..middleware.client_context import require_client_id

log = logging.getLogger(__name__)
router = APIRouter()


# --- Schemas -----------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    version: str
    checks: dict[str, dict[str, Any]]


class VersionResponse(BaseModel):
    name: str
    version: str
    env: str


class BriefRequest(BaseModel):
    title: str = Field(..., max_length=200)
    content: str = Field(..., max_length=20_000)
    sector: str | None = None
    budget: float | None = None
    max_tokens: int = Field(default=400, ge=10, le=2000)


class BriefResponse(BaseModel):
    client_id: str
    agent: str
    provider: str
    model: str
    latency_ms: int
    content: str
    usage: dict[str, Any]


# --- Helpers ------------------------------------------------------


async def _ping_db() -> dict[str, Any]:
    """Postgres ping (async)."""
    import asyncpg

    t0 = time.perf_counter()
    try:
        # docker compose içinde DATABASE_URL hostname=postgres
        conn = await asyncio.wait_for(
            asyncpg.connect(
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                database=settings.POSTGRES_DB,
                timeout=3,
            ),
            timeout=4,
        )
        try:
            row = await conn.fetchval("SELECT 1")
            ext = await conn.fetchval(
                "SELECT extversion FROM pg_extension WHERE extname='vector'"
            )
            latency = int((time.perf_counter() - t0) * 1000)
            return {
                "ok": row == 1,
                "latency_ms": latency,
                "pgvector": ext,
            }
        finally:
            await conn.close()
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def _ping_redis() -> dict[str, Any]:
    import redis.asyncio as aioredis

    t0 = time.perf_counter()
    try:
        client = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD or None,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        pong = await client.ping()
        await client.aclose()
        return {"ok": bool(pong), "latency_ms": int((time.perf_counter() - t0) * 1000)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# --- Endpoints ----------------------------------------------------


@router.get("/healthz", response_model=HealthResponse, tags=["health"])
async def healthz() -> HealthResponse:
    """Sağlık kontrolü: DB + Redis ping. Auth + X-Client-Id GEREKSİZ."""
    from .. import __version__

    db = await _ping_db()
    rd = await _ping_redis()
    all_ok = db.get("ok") and rd.get("ok")
    return HealthResponse(
        status="ok" if all_ok else "degraded",
        version=__version__,
        checks={"postgres": db, "redis": rd},
    )


@router.get("/readyz", tags=["health"])
async def readyz() -> dict[str, str]:
    """Kubernetes-style readiness: 200 OK eğer tüm hard dependencies sağlıklıysa."""
    db = await _ping_db()
    rd = await _ping_redis()
    if not (db.get("ok") and rd.get("ok")):
        raise HTTPException(status_code=503, detail="not ready")
    return {"status": "ready"}


@router.get("/version", response_model=VersionResponse, tags=["health"])
async def version() -> VersionResponse:
    from .. import __version__

    return VersionResponse(name=settings.PROJECT_NAME, version=__version__, env=settings.ENV)


@router.post("/brief", response_model=BriefResponse, tags=["agency"])
async def submit_brief(
    body: BriefRequest,
    client_id: str = Depends(require_client_id),
) -> BriefResponse:
    """Test endpoint — Account Manager ajanına brief gönderir.

    Şimdilik tek ajan (Account Manager) doğrudan çağrılır.
    Aşama 3'te tam CrewAI Flow tetiklenecek + Celery'e devredilir.
    """
    from ..crew.builder import run_account_manager

    try:
        result = await run_account_manager(
            client_id=client_id,
            brief_title=body.title,
            brief_content=body.content,
            sector=body.sector,
            max_tokens=body.max_tokens,
        )
    except Exception as e:
        log.exception("brief.failed")
        raise HTTPException(status_code=500, detail=f"Ajan çağrısı başarısız: {e}")

    return BriefResponse(
        client_id=client_id,
        agent="account_manager",
        provider=result.provider,
        model=result.model,
        latency_ms=result.latency_ms,
        content=result.content,
        usage=result.usage,
    )
