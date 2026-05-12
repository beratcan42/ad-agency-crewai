"""12 ajan icin Celery task factory.

Her ajan icin ayri `@shared_task` uretilir; queue ve routing_key
models.yaml'daki `queue` alanindan turetilir. Tum task'lar
generic `run_agent` builder'ini cagirir.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from celery import shared_task

from ..config.loader import get_agent_meta
from ..crew.agents.registry import get_all_agent_ids
from ..crew.builder import run_agent

log = logging.getLogger(__name__)


def _make_task(agent_id: str) -> Callable[..., dict[str, Any]]:
    meta = get_agent_meta(agent_id)
    queue = meta.get("queue", "q_heavy")
    routing_key = f"{queue.replace('q_', '')}.{agent_id}"
    task_name = f"src.workers.agent_tasks.{agent_id}"

    @shared_task(
        name=task_name,
        bind=True,
        autoretry_for=(Exception,),
        retry_backoff=True,
        retry_backoff_max=120,
        retry_jitter=True,
        max_retries=2,
        acks_late=True,
        queue=queue,
        routing_key=routing_key,
    )
    def _task(
        self,
        *,
        client_id: str,
        brief_title: str,
        brief_content: str,
        sector: str | None = None,
        extra_context: str | None = None,
        max_tokens: int = 800,
        temperature: float = 0.4,
    ) -> dict[str, Any]:
        log.info(
            "worker.start",
            extra={"agent_id": agent_id, "client_id": client_id, "queue": queue},
        )

        async def _run() -> Any:
            return await run_agent(
                agent_id=agent_id,
                client_id=client_id,
                brief_title=brief_title,
                brief_content=brief_content,
                sector=sector,
                extra_context=extra_context,
                max_tokens=max_tokens,
                temperature=temperature,
            )

        result = asyncio.run(_run())
        log.info(
            "worker.done",
            extra={
                "agent_id": agent_id,
                "client_id": client_id,
                "provider": result.provider,
                "model": result.model,
                "latency_ms": result.latency_ms,
            },
        )
        return {
            "agent_id": agent_id,
            "client_id": client_id,
            "provider": result.provider,
            "model": result.model,
            "latency_ms": result.latency_ms,
            "content": result.content,
            "usage": result.usage,
        }

    return _task


_AGENT_TASKS: dict[str, Callable[..., dict[str, Any]]] = {
    agent_id: _make_task(agent_id) for agent_id in get_all_agent_ids()
}


def get_task_for(agent_id: str):
    """Bir agent_id icin Celery task callable'ini dondurur (apply_async icin)."""
    if agent_id not in _AGENT_TASKS:
        raise KeyError(f"Bilinmeyen ajan: {agent_id}")
    return _AGENT_TASKS[agent_id]


def get_task_routes() -> dict[str, dict[str, str]]:
    """celery_app.conf.task_routes'a beslemek icin route haritasi."""
    routes: dict[str, dict[str, str]] = {}
    for agent_id in get_all_agent_ids():
        meta = get_agent_meta(agent_id)
        queue = meta.get("queue", "q_heavy")
        routing_key = f"{queue.replace('q_', '')}.{agent_id}"
        routes[f"src.workers.agent_tasks.{agent_id}"] = {
            "queue": queue,
            "routing_key": routing_key,
        }
    return routes
