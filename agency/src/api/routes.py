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


# --- Asama 3.E: Tek-ajan + async dispatch endpoint'leri ----------


class AgentRunRequest(BaseModel):
    title: str = Field(..., max_length=200)
    content: str = Field(..., max_length=20_000)
    sector: str | None = None
    extra_context: str | None = Field(default=None, max_length=10_000)
    temperature: float = Field(default=0.4, ge=0.0, le=2.0)
    max_tokens: int = Field(default=800, ge=10, le=4000)


class AgentRunResponse(BaseModel):
    client_id: str
    agent_id: str
    provider: str
    model: str
    latency_ms: int
    content: str
    usage: dict[str, Any]


class AgentDispatchResponse(BaseModel):
    task_id: str
    agent_id: str
    client_id: str
    queue: str
    status: str = "queued"


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    ready: bool
    result: dict[str, Any] | None = None
    error: str | None = None


class AgentInfo(BaseModel):
    id: str
    role: str
    goal: str
    queue: str
    chain: list[dict[str, str]]


class AgentsListResponse(BaseModel):
    count: int
    agents: list[AgentInfo]


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


# --- Asama 3.E: Agent runner & dispatch --------------------------


@router.get("/agents", response_model=AgentsListResponse, tags=["agents"])
async def list_agents() -> AgentsListResponse:
    """12 ajanin metadata + zincir bilgisini dondurur (X-Client-Id gerekmez)."""
    from ..config.loader import get_agent_meta, load_models_config
    from ..crew.agents.registry import get_all_agent_ids

    cfg = load_models_config()
    agents_block = cfg.get("agents", {})
    items: list[AgentInfo] = []
    for agent_id in get_all_agent_ids():
        meta = agents_block.get(agent_id, {})
        items.append(
            AgentInfo(
                id=agent_id,
                role=str(meta.get("role", "")),
                goal=str(meta.get("goal", "")),
                queue=str(meta.get("queue", "q_heavy")),
                chain=[
                    {"provider": str(c.get("provider")), "model": str(c.get("model"))}
                    for c in meta.get("chain", [])
                ],
            )
        )
    return AgentsListResponse(count=len(items), agents=items)


@router.post("/agents/{agent_id}/run", response_model=AgentRunResponse, tags=["agents"])
async def run_agent_sync(
    agent_id: str,
    body: AgentRunRequest,
    client_id: str = Depends(require_client_id),
) -> AgentRunResponse:
    """Bir ajani senkron calistirir (LLM'i bekler, sonucu dondurur).

    Test/demo icin uygun. Uretimde uzun-surecek ajanlar icin
    /agents/{agent_id}/dispatch kullanin (Celery'e gonderir).
    """
    from ..crew.agents.registry import get_all_agent_ids
    from ..crew.builder import run_agent as _run_agent

    if agent_id not in get_all_agent_ids():
        raise HTTPException(status_code=404, detail=f"Bilinmeyen ajan: {agent_id}")

    try:
        result = await _run_agent(
            agent_id=agent_id,
            client_id=client_id,
            brief_title=body.title,
            brief_content=body.content,
            sector=body.sector,
            extra_context=body.extra_context,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
        )
    except Exception as e:
        log.exception("agent_run.failed", extra={"agent_id": agent_id, "client_id": client_id})
        raise HTTPException(status_code=502, detail=f"Ajan cagrisi basarisiz: {e}")

    return AgentRunResponse(
        client_id=client_id,
        agent_id=agent_id,
        provider=result.provider,
        model=result.model,
        latency_ms=result.latency_ms,
        content=result.content,
        usage=result.usage,
    )


@router.post(
    "/agents/{agent_id}/dispatch",
    response_model=AgentDispatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["agents"],
)
async def dispatch_agent(
    agent_id: str,
    body: AgentRunRequest,
    client_id: str = Depends(require_client_id),
) -> AgentDispatchResponse:
    """Bir ajani async olarak Celery'e gonderir, task_id dondurur."""
    from ..config.loader import get_agent_meta
    from ..crew.agents.registry import get_all_agent_ids
    from ..workers.agent_tasks import get_task_for

    if agent_id not in get_all_agent_ids():
        raise HTTPException(status_code=404, detail=f"Bilinmeyen ajan: {agent_id}")

    task = get_task_for(agent_id)
    queue = get_agent_meta(agent_id).get("queue", "q_heavy")

    async_result = task.apply_async(
        kwargs={
            "client_id": client_id,
            "brief_title": body.title,
            "brief_content": body.content,
            "sector": body.sector,
            "extra_context": body.extra_context,
            "max_tokens": body.max_tokens,
            "temperature": body.temperature,
        }
    )
    return AgentDispatchResponse(
        task_id=async_result.id,
        agent_id=agent_id,
        client_id=client_id,
        queue=queue,
    )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse, tags=["agents"])
async def task_status(task_id: str) -> TaskStatusResponse:
    """Celery task'in durumunu dondurur (PENDING/STARTED/SUCCESS/FAILURE)."""
    from ..workers.celery_app import celery_app

    res = celery_app.AsyncResult(task_id)
    if res.successful():
        return TaskStatusResponse(
            task_id=task_id, status=res.status, ready=True, result=res.result
        )
    if res.failed():
        return TaskStatusResponse(
            task_id=task_id, status=res.status, ready=True, error=str(res.info)
        )
    return TaskStatusResponse(task_id=task_id, status=res.status, ready=res.ready())


# --- Asama 3.D: Telemetry & rate-limit endpoint'leri --------------


@router.get("/stats/usage", tags=["stats"])
async def stats_usage(
    hours: int = 24,
    client: str | None = None,
) -> dict[str, Any]:
    """Postgres agency.usage_logs uzerinden son N saatin kullanim ozeti.

    Query params:
      - hours: 1..720 (default 24)
      - client: opsiyonel filtreleme (client_id)
    X-Client-Id GEREKMEZ (genel sistem metrigi).
    """
    from ..router.telemetry import get_usage_summary

    hours = max(1, min(720, int(hours)))
    return await get_usage_summary(hours=hours, client_id=client)


@router.get("/stats/limits", tags=["stats"])
async def stats_limits() -> dict[str, Any]:
    """Redis rolling window'lari raporlar: her provider/model icin RPM/RPD durumu."""
    from ..config.loader import load_models_config
    from ..router.rate_limiter import get_rate_limiter

    cfg = load_models_config()
    providers_cfg = cfg.get("providers", {})

    # Tum zincirlerden tekil provider+model setini cikar
    seen: set[tuple[str, str]] = set()
    pairs: list[tuple[str, str, int, int]] = []
    for agent_id, agent_cfg in cfg.get("agents", {}).items():
        for entry in agent_cfg.get("chain", []):
            p = entry.get("provider", "")
            m = entry.get("model", "")
            if not p or not m or (p, m) in seen:
                continue
            seen.add((p, m))
            pcfg = providers_cfg.get(p, {})
            pairs.append((p, m, int(pcfg.get("rpm", 0)), int(pcfg.get("daily", 0))))

    rl = await get_rate_limiter()
    snapshot = await rl.snapshot(pairs)
    return {
        "count": len(snapshot),
        "soft_limits": {"rpm_pct_trigger": 0.85, "rpd_pct_trigger": 0.90},
        "items": snapshot,
    }


# --- Asama 5: Budget + Langfuse endpoints -----------------------


@router.get("/stats/budget", tags=["stats"])
async def stats_budget(
    client_id: str = Depends(require_client_id),
) -> dict[str, Any]:
    """Müşterinin token bütçesi durumunu döndürür."""
    from ..guardrails.token_budget import get_budget_status

    return await get_budget_status(client_id)


@router.get("/stats/langfuse", tags=["stats"])
async def stats_langfuse() -> dict[str, Any]:
    """Langfuse bağlantı durumunu döndürür (X-Client-Id gerekmez)."""
    from ..config.settings import settings
    from ..observability.langfuse_integration import _initialized, _langfuse_available

    return {
        "enabled": settings.LANGFUSE_ENABLED,
        "host": settings.LANGFUSE_HOST or "(tanımsız)",
        "available": _langfuse_available(),
        "callback_active": _initialized,
    }

@router.post("/flows/campaign", tags=["Flows"])
async def run_campaign_flow(
    body: BriefRequest,
    client_id: str = Depends(require_client_id),
):
    """
    Asama 6: CrewAI Flows kullanarak E2E kampanya pipeline'ini tetikler.
    (Account Manager -> Strategist -> Copywriter -> Social Media -> Postiz)
    """
    try:
        from ..crew.flows.campaign_flow import CampaignFlow
        flow = CampaignFlow(
            client_id=client_id,
            brief_title=body.title,
            brief_content=body.content,
            sector=body.sector or "Belirtilmemiş"
        )
        flow.kickoff()
        return {"status": "success", "state": flow.state.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
