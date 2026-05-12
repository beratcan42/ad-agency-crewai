"""Circuit breaker — provider bazlı hata sayacı.

Aşama 5: Redis key ile ardışık hata takibi.
Eşik aşılınca provider geçici olarak devre dışı bırakılır.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import redis.asyncio as aioredis

from ..config.settings import settings

log = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None

# Circuit breaker durumları
STATE_CLOSED = "closed"      # Normal çalışma
STATE_OPEN = "open"          # Devre açık — çağrı engellenir
STATE_HALF_OPEN = "half"     # Deneme çağrısına izin ver


def _key(provider: str, model: str) -> str:
    return f"cb:{provider}:{model}"


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD or None,
            socket_connect_timeout=3,
            socket_timeout=3,
            decode_responses=True,
        )
    return _redis


async def get_state(provider: str, model: str) -> tuple[str, dict[str, Any]]:
    """Circuit breaker durumunu döndürür.

    Returns:
        (state, info_dict)
    """
    try:
        r = await _get_redis()
        key = _key(provider, model)
        data = await r.hgetall(key)

        if not data:
            return STATE_CLOSED, {"failures": 0}

        failures = int(data.get("failures", 0))
        opened_at = float(data.get("opened_at", 0))
        threshold = settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD
        timeout = settings.CIRCUIT_BREAKER_TIMEOUT_SEC

        if failures < threshold:
            return STATE_CLOSED, {"failures": failures}

        # Devre açık — timeout geçti mi?
        elapsed = time.time() - opened_at
        if elapsed >= timeout:
            return STATE_HALF_OPEN, {"failures": failures, "elapsed": int(elapsed)}

        return STATE_OPEN, {"failures": failures, "remaining_sec": int(timeout - elapsed)}
    except Exception as e:
        log.warning("circuit_breaker.state.fail: %s", e)
        return STATE_CLOSED, {"failures": 0, "error": str(e)}


async def is_allowed(provider: str, model: str) -> tuple[bool, str]:
    """Bu provider/model'e çağrı yapılabilir mi?

    Returns:
        (allowed, reason)
    """
    state, info = await get_state(provider, model)
    if state == STATE_OPEN:
        return False, f"Circuit OPEN: {info.get('failures')} hata, {info.get('remaining_sec')}s kaldı"
    return True, state


async def record_success(provider: str, model: str) -> None:
    """Başarılı çağrı — sayacı sıfırla."""
    try:
        r = await _get_redis()
        key = _key(provider, model)
        await r.delete(key)
    except Exception as e:
        log.warning("circuit_breaker.success.fail: %s", e)


async def record_failure(provider: str, model: str) -> int:
    """Başarısız çağrı — sayacı artır, eşik aşılınca devre aç.

    Returns:
        Güncel hata sayısı
    """
    try:
        r = await _get_redis()
        key = _key(provider, model)
        pipe = r.pipeline()
        pipe.hincrby(key, "failures", 1)
        pipe.hget(key, "failures")
        results = await pipe.execute()
        failures = int(results[1] or 1)

        threshold = settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD
        if failures >= threshold:
            await r.hset(key, "opened_at", str(time.time()))
            log.warning(
                "circuit_breaker.OPEN: %s/%s — %d ardışık hata",
                provider, model, failures,
            )

        # Key'e TTL koy (timeout * 2) — stale key'leri temizle
        ttl = settings.CIRCUIT_BREAKER_TIMEOUT_SEC * 2
        await r.expire(key, ttl)

        return failures
    except Exception as e:
        log.warning("circuit_breaker.failure.fail: %s", e)
        return 0
