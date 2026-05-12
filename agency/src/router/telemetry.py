"""Postgres'e LLM cagri telemetry'sini yazar.

Tablo: agency.usage_logs (bkz. scripts/sql/init/02-usage-logs.sql)

Fire-and-forget pattern: insert hatasi LLM cevabini bloklamaz.
Singleton asyncpg pool kullanir (hafif baglanti acma maliyeti yok).
"""

from __future__ import annotations

import json
import logging
from typing import Any

import asyncpg

from ..config.settings import settings

log = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database=settings.POSTGRES_DB,
            min_size=1,
            max_size=4,
            command_timeout=5,
        )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        try:
            await _pool.close()
        except Exception:
            pass
        _pool = None


async def log_usage(
    *,
    client_id: str,
    agent_id: str,
    provider: str,
    model: str,
    chain_idx: int,
    status: str,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
    latency_ms: int | None = None,
    error_class: str | None = None,
    error_msg: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Tek satir insert. Hata olursa log + sessiz devam (LLM cevabini bloklamaz)."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO agency.usage_logs (
                    client_id, agent_id, provider, model, chain_idx, status,
                    prompt_tokens, completion_tokens, total_tokens, latency_ms,
                    error_class, error_msg, extra
                ) VALUES (
                    $1, $2, $3, $4, $5, $6,
                    $7, $8, $9, $10,
                    $11, $12, $13::jsonb
                )
                """,
                client_id,
                agent_id,
                provider,
                model,
                int(chain_idx),
                status,
                int(prompt_tokens) if prompt_tokens else None,
                int(completion_tokens) if completion_tokens else None,
                int(total_tokens) if total_tokens else None,
                int(latency_ms) if latency_ms else None,
                error_class,
                (error_msg[:1000] if error_msg else None),
                json.dumps(extra) if extra else None,
            )
    except Exception as e:
        # Telemetry hatasi LLM yaniti hi bir zaman bloklamamali
        log.warning(
            "telemetry.insert.fail",
            extra={"agent_id": agent_id, "provider": provider, "model": model, "err": str(e)},
        )


async def get_usage_summary(
    *,
    hours: int = 24,
    client_id: str | None = None,
) -> dict[str, Any]:
    """Son N saat icindeki kullanim ozeti.

    Returns:
        {
          "total_calls": ..., "total_tokens": ...,
          "by_status": [{status, count}],
          "by_agent":  [{agent_id, calls, total_tokens, avg_latency_ms}],
          "by_model":  [{provider, model, calls, total_tokens}],
          "by_client": [{client_id, calls, total_tokens}],
          "errors_last_10": [...]
        }
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        params: list[Any] = [hours]
        client_filter = ""
        if client_id:
            client_filter = " AND client_id = $2 "
            params.append(client_id)

        totals = await conn.fetchrow(
            f"""
            SELECT
                COUNT(*) AS total_calls,
                COALESCE(SUM(total_tokens),0) AS total_tokens,
                COALESCE(AVG(latency_ms),0)::INT AS avg_latency_ms
            FROM agency.usage_logs
            WHERE ts >= NOW() - ($1::INT || ' hours')::INTERVAL
            {client_filter}
            """,
            *params,
        )

        by_status = await conn.fetch(
            f"""
            SELECT status, COUNT(*) AS count
            FROM agency.usage_logs
            WHERE ts >= NOW() - ($1::INT || ' hours')::INTERVAL
            {client_filter}
            GROUP BY status ORDER BY count DESC
            """,
            *params,
        )

        by_agent = await conn.fetch(
            f"""
            SELECT agent_id,
                   COUNT(*) AS calls,
                   COALESCE(SUM(total_tokens),0) AS total_tokens,
                   COALESCE(AVG(latency_ms),0)::INT AS avg_latency_ms
            FROM agency.usage_logs
            WHERE ts >= NOW() - ($1::INT || ' hours')::INTERVAL
            {client_filter}
            GROUP BY agent_id ORDER BY total_tokens DESC
            """,
            *params,
        )

        by_model = await conn.fetch(
            f"""
            SELECT provider, model,
                   COUNT(*) AS calls,
                   COALESCE(SUM(total_tokens),0) AS total_tokens
            FROM agency.usage_logs
            WHERE ts >= NOW() - ($1::INT || ' hours')::INTERVAL
              AND status IN ('success')
            {client_filter}
            GROUP BY provider, model ORDER BY calls DESC LIMIT 20
            """,
            *params,
        )

        by_client = await conn.fetch(
            f"""
            SELECT client_id,
                   COUNT(*) AS calls,
                   COALESCE(SUM(total_tokens),0) AS total_tokens
            FROM agency.usage_logs
            WHERE ts >= NOW() - ($1::INT || ' hours')::INTERVAL
            {client_filter}
            GROUP BY client_id ORDER BY total_tokens DESC LIMIT 20
            """,
            *params,
        )

        errors = await conn.fetch(
            f"""
            SELECT ts, client_id, agent_id, provider, model, error_class, error_msg
            FROM agency.usage_logs
            WHERE ts >= NOW() - ($1::INT || ' hours')::INTERVAL
              AND status = 'error'
            {client_filter}
            ORDER BY ts DESC LIMIT 10
            """,
            *params,
        )

    def _rows(rows):
        return [dict(r) for r in rows]

    return {
        "window_hours": hours,
        "client_filter": client_id,
        "totals": dict(totals) if totals else {},
        "by_status": _rows(by_status),
        "by_agent": _rows(by_agent),
        "by_model": _rows(by_model),
        "by_client": _rows(by_client),
        "errors_last_10": _rows(errors),
    }
