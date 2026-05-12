"""Account Manager için Celery task — q_heavy queue."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from celery import shared_task

from ..crew.builder import run_account_manager

log = logging.getLogger(__name__)


@shared_task(
    name="src.workers.account_manager_worker.run",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
    max_retries=2,
    acks_late=True,
)
def run(
    self,
    *,
    client_id: str,
    brief_title: str,
    brief_content: str,
    sector: str | None = None,
    max_tokens: int = 400,
) -> dict[str, Any]:
    """Senkron Celery task — içeride async coroutine'i çalıştırır."""
    log.info("worker.account_manager.start", extra={"client_id": client_id, "title": brief_title})

    async def _run() -> Any:
        return await run_account_manager(
            client_id=client_id,
            brief_title=brief_title,
            brief_content=brief_content,
            sector=sector,
            max_tokens=max_tokens,
        )

    result = asyncio.run(_run())
    return {
        "client_id": client_id,
        "agent": "account_manager",
        "provider": result.provider,
        "model": result.model,
        "latency_ms": result.latency_ms,
        "content": result.content,
        "usage": result.usage,
    }
