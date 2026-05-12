"""Crew builder — generic run_agent + geriye donuk run_account_manager.

Asama 3'te 12 ajan icin tek bir dispatcher kullanilir. CrewAI Crew/Flow
entegrasyonu Asama 4'te eklenecek (tools + Obsidian + Postiz).
"""

from __future__ import annotations

import logging
from typing import Any

from ..router.model_router import CallResult, ModelRouter
from .agents.registry import build_system_prompt, get_all_agent_ids

log = logging.getLogger(__name__)


def _build_user_message(
    *,
    client_id: str,
    brief_title: str,
    brief_content: str,
    sector: str | None = None,
    extra_context: str | None = None,
) -> str:
    msg = (
        f"# Brief\n## Baslik\n{brief_title}\n\n"
        f"## Sektor\n{sector or 'Belirtilmemis'}\n\n"
        f"## Icerik\n{brief_content}\n\n"
        f"## Musteri ID\n{client_id}\n"
    )
    if extra_context:
        msg += f"\n## Ek Baglam\n{extra_context}\n"
    return msg


async def run_agent(
    *,
    agent_id: str,
    client_id: str,
    brief_title: str,
    brief_content: str,
    sector: str | None = None,
    extra_context: str | None = None,
    temperature: float = 0.4,
    max_tokens: int = 800,
) -> CallResult:
    """Verilen ajani tek bir brief uzerinde calistir (4-katmanli fallback ile)."""
    if agent_id not in get_all_agent_ids():
        raise ValueError(f"Bilinmeyen ajan: {agent_id}")

    router = ModelRouter(agent_id)
    messages: list[dict[str, str]] = [
        {"role": "system", "content": build_system_prompt(agent_id)},
        {
            "role": "user",
            "content": _build_user_message(
                client_id=client_id,
                brief_title=brief_title,
                brief_content=brief_content,
                sector=sector,
                extra_context=extra_context,
            ),
        },
    ]

    log.info("crew.agent.start", extra={"agent_id": agent_id, "client_id": client_id})
    result = await router.acompletion(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    log.info(
        "crew.agent.done",
        extra={
            "agent_id": agent_id,
            "client_id": client_id,
            "provider": result.provider,
            "model": result.model,
            "latency_ms": result.latency_ms,
            "tokens": result.usage.get("total_tokens") if result.usage else None,
        },
    )
    return result


async def run_account_manager(
    *,
    client_id: str,
    brief_title: str,
    brief_content: str,
    sector: str | None = None,
    max_tokens: int = 400,
) -> CallResult:
    """Geriye donuk: eski API endpoint'i bunu cagiriyor."""
    return await run_agent(
        agent_id="account_manager",
        client_id=client_id,
        brief_title=brief_title,
        brief_content=brief_content,
        sector=sector,
        max_tokens=max_tokens,
    )
