"""Token bütçesi guardrail — müşteri bazlı günlük/kampanya limiti.

Aşama 5: Postgres agency.token_budgets tablosu + Redis cache.
Bütçe aşılırsa LLM çağrısı engellenir (HTTP 429).
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

import asyncpg

from ..config.settings import settings

log = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def _get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database=settings.POSTGRES_DB,
            min_size=1,
            max_size=3,
            command_timeout=5,
        )
    return _pool


async def ensure_budget_row(client_id: str, period: str = "daily") -> None:
    """Müşteri için bütçe satırı yoksa oluşturur."""
    pool = await _get_pool()
    budget = (
        settings.TOKEN_BUDGET_DAILY_GLOBAL
        if period == "daily"
        else settings.TOKEN_BUDGET_PER_CAMPAIGN
    )
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO agency.token_budgets (client_id, period, budget_tokens, used_tokens, period_start)
            VALUES ($1, $2, $3, 0, NOW())
            ON CONFLICT (client_id, period) DO NOTHING
            """,
            client_id,
            period,
            budget,
        )


async def check_budget(
    client_id: str,
    estimated_tokens: int = 0,
    period: str = "daily",
) -> tuple[bool, int, int]:
    """Bütçe kontrolü.

    Returns:
        (allowed, remaining_tokens, budget_tokens)
    """
    try:
        await ensure_budget_row(client_id, period)
        pool = await _get_pool()
        async with pool.acquire() as conn:
            # Günlük periyot kontrolü — yeni gün başladıysa sıfırla
            row = await conn.fetchrow(
                """
                SELECT budget_tokens, used_tokens, period_start
                FROM agency.token_budgets
                WHERE client_id = $1 AND period = $2
                """,
                client_id,
                period,
            )
            if row is None:
                return True, settings.TOKEN_BUDGET_DAILY_GLOBAL, settings.TOKEN_BUDGET_DAILY_GLOBAL

            budget = row["budget_tokens"]
            used = row["used_tokens"]
            period_start = row["period_start"]

            # Günlük periyot: yeni gün başladıysa sıfırla
            if period == "daily":
                now_utc = datetime.now(timezone.utc)
                if period_start.date() < now_utc.date():
                    await conn.execute(
                        """
                        UPDATE agency.token_budgets
                        SET used_tokens = 0, period_start = NOW(), updated_at = NOW()
                        WHERE client_id = $1 AND period = $2
                        """,
                        client_id,
                        period,
                    )
                    used = 0

            remaining = max(0, budget - used)
            allowed = remaining >= estimated_tokens
            return allowed, remaining, budget
    except Exception as e:
        log.warning("token_budget.check.fail: %s", e)
        # Hata durumunda izin ver (fail-open)
        return True, settings.TOKEN_BUDGET_DAILY_GLOBAL, settings.TOKEN_BUDGET_DAILY_GLOBAL


async def record_usage(client_id: str, tokens_used: int, period: str = "daily") -> int:
    """Başarılı LLM çağrısı sonrası token kullanımını kaydeder.

    Returns:
        Güncel used_tokens değeri
    """
    try:
        pool = await _get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE agency.token_budgets
                SET used_tokens = used_tokens + $3, updated_at = NOW()
                WHERE client_id = $1 AND period = $2
                RETURNING used_tokens
                """,
                client_id,
                period,
                tokens_used,
            )
            return row["used_tokens"] if row else 0
    except Exception as e:
        log.warning("token_budget.record.fail: %s", e)
        return 0


async def get_budget_status(client_id: str) -> dict[str, Any]:
    """Müşterinin tüm periyotlardaki bütçe durumunu döndürür."""
    try:
        pool = await _get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT period, budget_tokens, used_tokens, period_start, updated_at
                FROM agency.token_budgets
                WHERE client_id = $1
                ORDER BY period
                """,
                client_id,
            )
            return {
                "client_id": client_id,
                "budgets": [dict(r) for r in rows],
            }
    except Exception as e:
        log.warning("token_budget.status.fail: %s", e)
        return {"client_id": client_id, "budgets": [], "error": str(e)}
