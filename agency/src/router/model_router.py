"""Hibrit model router — 4 katmanli fallback + Redis rate limit + Postgres telemetry.

Asama 3.D:
  - Redis rolling-window rate limiter (RPM/RPD) ile proactive fallback
  - Postgres agency.usage_logs tablosuna fire-and-forget insert (her cagri)
  - Hata tiplerini ayrik isaretle: success | fallback | error | skip_ratelimit
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import litellm
from litellm.exceptions import APIConnectionError, RateLimitError, Timeout

from ..config.loader import get_agent_chain, get_provider_config
from ..config.settings import settings
from .rate_limiter import get_rate_limiter
from .telemetry import log_usage

log = logging.getLogger(__name__)

litellm.set_verbose = False
litellm.drop_params = True


class AllProvidersFailedError(Exception):
    """Tum fallback zincirinin basarisiz oldugunu belirtir."""


@dataclass
class CallResult:
    provider: str
    model: str
    content: str
    usage: dict[str, Any]
    latency_ms: int


class ModelRouter:
    """Tek bir ajanin cagrilarini yoneten yonlendirici.

    Kullanim:
        router = ModelRouter("account_manager")
        result = await router.acompletion([{"role":"user","content":"..."}], client_id="acme")
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.chain = get_agent_chain(agent_id)
        if not self.chain:
            raise ValueError(f"Ajan icin chain bos: {agent_id}")

    def _build_litellm_params(self, provider: str, model: str) -> dict[str, str]:
        """LiteLLM icin provider'a gore model adi + endpoint.

        Native prefix'ler tercih edilir (gemini/, ollama_chat/) cunku
        OpenAI-compat shim'i bazen tool_calling/streaming'i bozuyor.
        """
        prov_cfg = get_provider_config(provider)
        params: dict[str, Any] = {}

        if provider == "openrouter":
            params["model"] = f"openrouter/{model}"
            params["api_key"] = settings.OPENROUTER_API_KEY
            params["api_base"] = prov_cfg["base_url"]
        elif provider in ("gemini", "google"):
            # LiteLLM native Gemini provider — kendi endpoint'ini yonetir
            params["model"] = f"gemini/{model}"
            params["api_key"] = settings.GOOGLE_GEMINI_API_KEY
        elif provider == "ollama":
            # ollama_chat/ native: streaming + tool_calls native destekli
            params["model"] = f"ollama_chat/{model}"
            params["api_base"] = settings.OLLAMA_URL.rstrip("/")
        else:
            raise ValueError(f"Bilinmeyen saglayici: {provider}")

        params["timeout"] = float(prov_cfg.get("timeout", 30))
        return params

    async def acompletion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.4,
        max_tokens: int | None = None,
        client_id: str = "unknown",
    ) -> CallResult:
        """Zincirde sirayla dene, ilk basarili sonucu dondur.

        Her adimda:
          1) Rate limiter check (proactive fallback)
          2) LiteLLM cagri
          3) Telemetry insert (status: success | fallback | error | skip_ratelimit)
          4) Basariliysa Redis sayaclari artir
        """
        last_error: Exception | None = None
        rl = await get_rate_limiter()

        for idx, entry in enumerate(self.chain):
            provider = entry["provider"]
            model = entry["model"]
            params = self._build_litellm_params(provider, model)

            if provider != "ollama" and not params.get("api_key"):
                log.warning(
                    "router.skip_no_key",
                    extra={"agent": self.agent_id, "provider": provider, "model": model},
                )
                await log_usage(
                    client_id=client_id, agent_id=self.agent_id, provider=provider, model=model,
                    chain_idx=idx, status="skip_ratelimit", error_class="MissingApiKey",
                    error_msg="api_key bos veya tanimsiz",
                )
                continue

            # 1) Proactive rate limit check
            prov_cfg = get_provider_config(provider)
            rpm_limit = int(prov_cfg.get("rpm", 0))
            rpd_limit = int(prov_cfg.get("daily", 0))
            allowed, reason, usage_snap = await rl.check_capacity(
                provider, model, rpm_limit, rpd_limit
            )
            if not allowed:
                log.warning(
                    "router.skip_ratelimit",
                    extra={"agent": self.agent_id, "provider": provider, "model": model, "reason": reason, **usage_snap},
                )
                await log_usage(
                    client_id=client_id, agent_id=self.agent_id, provider=provider, model=model,
                    chain_idx=idx, status="skip_ratelimit", error_class="ProactiveLimit",
                    error_msg=reason, extra=usage_snap,
                )
                continue

            # 2) LiteLLM cagri
            t0 = time.perf_counter()
            try:
                response = await litellm.acompletion(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **params,
                )
                latency_ms = int((time.perf_counter() - t0) * 1000)
                content = response["choices"][0]["message"]["content"]
                usage_raw = response.get("usage") or {}
                if hasattr(usage_raw, "model_dump"):
                    usage = usage_raw.model_dump()
                elif hasattr(usage_raw, "dict"):
                    usage = usage_raw.dict()
                else:
                    try:
                        usage = dict(usage_raw)
                        for k, v in list(usage.items()):
                            if hasattr(v, "model_dump"):
                                usage[k] = v.model_dump()
                            elif hasattr(v, "dict"):
                                usage[k] = v.dict()
                    except Exception:
                        usage = {}

                # 3+4) Telemetry + sayac artir
                await log_usage(
                    client_id=client_id, agent_id=self.agent_id, provider=provider, model=model,
                    chain_idx=idx, status="success",
                    prompt_tokens=usage.get("prompt_tokens"),
                    completion_tokens=usage.get("completion_tokens"),
                    total_tokens=usage.get("total_tokens"),
                    latency_ms=latency_ms,
                )
                await rl.record_call(provider, model)

                log.info(
                    "router.success",
                    extra={
                        "agent": self.agent_id, "provider": provider, "model": model,
                        "chain_idx": idx, "latency_ms": latency_ms,
                        "tokens": usage.get("total_tokens"),
                    },
                )
                return CallResult(
                    provider=provider, model=model, content=content,
                    usage=usage, latency_ms=latency_ms,
                )

            except (RateLimitError, Timeout, APIConnectionError) as e:
                latency_ms = int((time.perf_counter() - t0) * 1000)
                log.warning(
                    "router.fallback",
                    extra={"agent": self.agent_id, "provider": provider, "model": model, "err": str(e)[:200]},
                )
                await log_usage(
                    client_id=client_id, agent_id=self.agent_id, provider=provider, model=model,
                    chain_idx=idx, status="fallback", latency_ms=latency_ms,
                    error_class=type(e).__name__, error_msg=str(e)[:500],
                )
                last_error = e
                continue
            except Exception as e:
                latency_ms = int((time.perf_counter() - t0) * 1000)
                log.error(
                    "router.error",
                    extra={"agent": self.agent_id, "provider": provider, "model": model, "err": str(e)[:200]},
                )
                await log_usage(
                    client_id=client_id, agent_id=self.agent_id, provider=provider, model=model,
                    chain_idx=idx, status="fallback", latency_ms=latency_ms,
                    error_class=type(e).__name__, error_msg=str(e)[:500],
                )
                last_error = e
                continue

        # Tum zincir tukendi
        await log_usage(
            client_id=client_id, agent_id=self.agent_id,
            provider="(none)", model="(none)", chain_idx=len(self.chain),
            status="error", error_class="AllProvidersFailed",
            error_msg=str(last_error)[:500] if last_error else "no_chain_attempt",
        )
        raise AllProvidersFailedError(
            f"Tum saglayicilar basarisiz: agent={self.agent_id}, son hata: {last_error}"
        )

    def get_litellm_model_string(self, idx: int = 0) -> tuple[str, dict[str, Any]]:
        """CrewAI Agent.llm parametresine vermek için (model_string, extra_kwargs).

        İlk sağlayıcı seçilir; CrewAI ile entegrasyon Aşama 3'te dinamikleşecek.
        """
        entry = self.chain[idx]
        params = self._build_litellm_params(entry["provider"], entry["model"])
        model_string = params.pop("model")
        return model_string, params
