"""Crew builder — Aşama 2 minimal versiyon.

Aşama 3'te CrewAI Crew + Flow + @persist eklenecek.
Şimdilik: ModelRouter aracılığıyla Account Manager'a tek seferlik istek atar.
"""

from __future__ import annotations

import logging
from typing import Any

from ..router.model_router import CallResult, ModelRouter
from .agents.account_manager import AGENT_ID as AM_ID, get_system_prompt

log = logging.getLogger(__name__)


async def run_account_manager(
    *,
    client_id: str,
    brief_title: str,
    brief_content: str,
    sector: str | None = None,
    max_tokens: int = 400,
) -> CallResult:
    """Account Manager ajanına tek bir brief gönderir.

    Returns:
        CallResult — provider, model, content, usage, latency_ms
    """
    router = ModelRouter(AM_ID)

    user_msg = (
        f"# Brief\n## Başlık\n{brief_title}\n\n"
        f"## Sektör\n{sector or 'Belirtilmemiş'}\n\n"
        f"## İçerik\n{brief_content}\n\n"
        f"## Müşteri ID\n{client_id}\n"
    )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": get_system_prompt()},
        {"role": "user", "content": user_msg},
    ]

    log.info("crew.account_manager.start", extra={"client_id": client_id})
    result = await router.acompletion(
        messages=messages,
        temperature=0.4,
        max_tokens=max_tokens,
    )
    log.info(
        "crew.account_manager.done",
        extra={
            "client_id": client_id,
            "provider": result.provider,
            "model": result.model,
            "latency_ms": result.latency_ms,
            "tokens": result.usage.get("total_tokens"),
        },
    )
    return result
