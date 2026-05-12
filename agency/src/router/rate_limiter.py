"""Redis rolling-window rate limiter (RPM + RPD).

Her provider+model icin iki sayac:
  rate:rpm:{provider}:{model}    -> 60 sn rolling window (sorted set)
  rate:rpd:{provider}:{model}    -> 24 saat rolling window (sorted set)

Proactive fallback: limit dolmadan kullanim oranina gore karar verir.
  - check_capacity(provider, model, rpm, daily) -> (allowed, reason, usage_pct)
  - allowed=False olursa router siradakine gecer (skip_ratelimit log'lar).

Kullanim:
    async with RateLimiter.from_settings() as rl:
        allowed, reason, pct = await rl.check_capacity("openrouter", "owl/owl-alpha", 20, 200)
        if allowed:
            await rl.record_call("openrouter", "owl/owl-alpha")
"""

from __future__ import annotations

import logging
import time
from typing import Any

import redis.asyncio as aioredis

from ..config.settings import settings

log = logging.getLogger(__name__)

# Proactive fallback threshold (limit'in yuzde kaci dolunca atla)
_RPM_SOFT_LIMIT_PCT = 0.85    # %85 olunca atla
_RPD_SOFT_LIMIT_PCT = 0.90    # gunluk icin biraz daha cesur

_RPM_WINDOW = 60               # saniye
_RPD_WINDOW = 86400            # saniye


class RateLimiter:
    """Hafif Redis tabanli rolling-window sayac.

    Lifecycle:
        rl = RateLimiter()
        await rl.connect()
        ...
        await rl.aclose()
    """

    def __init__(self) -> None:
        self._client: aioredis.Redis | None = None

    @classmethod
    def from_settings(cls) -> "RateLimiter":
        return cls()

    async def __aenter__(self) -> "RateLimiter":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def connect(self) -> None:
        if self._client is None:
            self._client = aioredis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD or None,
                socket_connect_timeout=3,
                socket_timeout=3,
                decode_responses=True,
            )

    async def aclose(self) -> None:
        if self._client is not None:
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None

    @staticmethod
    def _rpm_key(provider: str, model: str) -> str:
        return f"rate:rpm:{provider}:{model}"

    @staticmethod
    def _rpd_key(provider: str, model: str) -> str:
        return f"rate:rpd:{provider}:{model}"

    async def _window_count(self, key: str, window_sec: int) -> int:
        """Sorted set'ten son N saniye icindeki giris sayisini doner."""
        if self._client is None:
            return 0
        now_ms = time.time() * 1000
        cutoff_ms = now_ms - (window_sec * 1000)
        try:
            await self._client.zremrangebyscore(key, 0, cutoff_ms)
            return await self._client.zcard(key)
        except Exception as e:
            log.warning("ratelimit.count.fail", extra={"key": key, "err": str(e)})
            return 0

    async def check_capacity(
        self,
        provider: str,
        model: str,
        rpm_limit: int,
        daily_limit: int,
    ) -> tuple[bool, str, dict[str, Any]]:
        """Bir cagri yapilabilir mi?

        Returns:
            (allowed, reason, usage_dict)
            usage_dict: {"rpm_used", "rpm_pct", "rpd_used", "rpd_pct"}
        """
        if self._client is None:
            await self.connect()
        if rpm_limit <= 0 and daily_limit <= 0:
            return True, "no-limit", {"rpm_used": 0, "rpm_pct": 0.0, "rpd_used": 0, "rpd_pct": 0.0}

        rpm_used = await self._window_count(self._rpm_key(provider, model), _RPM_WINDOW)
        rpd_used = await self._window_count(self._rpd_key(provider, model), _RPD_WINDOW)

        rpm_pct = (rpm_used / rpm_limit) if rpm_limit > 0 else 0.0
        rpd_pct = (rpd_used / daily_limit) if daily_limit > 0 else 0.0
        usage = {
            "rpm_used": rpm_used, "rpm_limit": rpm_limit, "rpm_pct": round(rpm_pct, 3),
            "rpd_used": rpd_used, "rpd_limit": daily_limit, "rpd_pct": round(rpd_pct, 3),
        }

        if rpm_limit > 0 and rpm_pct >= _RPM_SOFT_LIMIT_PCT:
            return False, f"rpm_soft_limit ({rpm_pct:.0%} >= {_RPM_SOFT_LIMIT_PCT:.0%})", usage
        if daily_limit > 0 and rpd_pct >= _RPD_SOFT_LIMIT_PCT:
            return False, f"rpd_soft_limit ({rpd_pct:.0%} >= {_RPD_SOFT_LIMIT_PCT:.0%})", usage

        return True, "ok", usage

    async def record_call(self, provider: str, model: str) -> None:
        """Basarili cagri sayilirini her iki window'a yazar (idempotent)."""
        if self._client is None:
            await self.connect()
        now_ms = time.time() * 1000
        member = f"{now_ms:.0f}:{provider}:{model}"
        try:
            pipe = self._client.pipeline()
            for key, window in [
                (self._rpm_key(provider, model), _RPM_WINDOW),
                (self._rpd_key(provider, model), _RPD_WINDOW),
            ]:
                pipe.zadd(key, {member: now_ms})
                pipe.expire(key, window + 60)
            await pipe.execute()
        except Exception as e:
            log.warning("ratelimit.record.fail", extra={"err": str(e)})

    async def snapshot(self, providers_models: list[tuple[str, str, int, int]]) -> list[dict[str, Any]]:
        """Birden cok provider/model icin anlik sayac fotograflari."""
        out: list[dict[str, Any]] = []
        for provider, model, rpm_limit, daily_limit in providers_models:
            rpm_used = await self._window_count(self._rpm_key(provider, model), _RPM_WINDOW)
            rpd_used = await self._window_count(self._rpd_key(provider, model), _RPD_WINDOW)
            out.append({
                "provider": provider, "model": model,
                "rpm_used": rpm_used, "rpm_limit": rpm_limit,
                "rpm_pct": round(rpm_used / rpm_limit, 3) if rpm_limit > 0 else 0.0,
                "rpd_used": rpd_used, "rpd_limit": daily_limit,
                "rpd_pct": round(rpd_used / daily_limit, 3) if daily_limit > 0 else 0.0,
            })
        return out


# Modul seviyesi singleton (FastAPI ve Celery icin)
_singleton: RateLimiter | None = None


async def get_rate_limiter() -> RateLimiter:
    global _singleton
    if _singleton is None:
        _singleton = RateLimiter()
        await _singleton.connect()
    return _singleton
