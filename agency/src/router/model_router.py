"""Hibrit model router — 4 katmanlı fallback (timeout + 429 + ağ hatası handle).

Aşama 2'de minimal versiyon. Aşama 3'te Redis rolling window + telemetry eklenecek.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

import litellm
from litellm.exceptions import APIConnectionError, RateLimitError, Timeout

from ..config.loader import get_agent_chain, get_provider_config
from ..config.settings import settings

log = logging.getLogger(__name__)

# LiteLLM globalleri
litellm.set_verbose = False
litellm.drop_params = True


class AllProvidersFailedError(Exception):
    """Tüm fallback zincirinin başarısız olduğunu belirtir."""


@dataclass
class CallResult:
    provider: str
    model: str
    content: str
    usage: dict[str, Any]
    latency_ms: int


class ModelRouter:
    """Tek bir ajanın çağrılarını yöneten yönlendirici.

    Kullanım:
        router = ModelRouter("account_manager")
        result = await router.acompletion([{"role":"user","content":"..."}])
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
    ) -> CallResult:
        """Zincirde sırayla dene, ilk başarılı sonucu döndür."""
        last_error: Exception | None = None

        for entry in self.chain:
            provider = entry["provider"]
            model = entry["model"]
            params = self._build_litellm_params(provider, model)

            if provider != "ollama":
                if not params.get("api_key"):
                    log.warning(
                        "router.skip_no_key",
                        extra={"agent": self.agent_id, "provider": provider, "model": model},
                    )
                    continue

            import time

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
                # LiteLLM usage pydantic obje olabilir, JSON-serializable dict'e cevir
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
                log.info(
                    "router.success",
                    extra={
                        "agent": self.agent_id,
                        "provider": provider,
                        "model": model,
                        "latency_ms": latency_ms,
                        "tokens": usage.get("total_tokens"),
                    },
                )
                return CallResult(
                    provider=provider,
                    model=model,
                    content=content,
                    usage=usage,
                    latency_ms=latency_ms,
                )
            except (RateLimitError, Timeout, APIConnectionError) as e:
                log.warning(
                    "router.fallback",
                    extra={"agent": self.agent_id, "provider": provider, "model": model, "err": str(e)},
                )
                last_error = e
                continue
            except Exception as e:  # diğer hataları da fallback'le (graceful)
                log.error(
                    "router.error",
                    extra={"agent": self.agent_id, "provider": provider, "model": model, "err": str(e)},
                )
                last_error = e
                continue

        raise AllProvidersFailedError(
            f"Tüm sağlayıcılar başarısız: agent={self.agent_id}, son hata: {last_error}"
        )

    def get_litellm_model_string(self, idx: int = 0) -> tuple[str, dict[str, Any]]:
        """CrewAI Agent.llm parametresine vermek için (model_string, extra_kwargs).

        İlk sağlayıcı seçilir; CrewAI ile entegrasyon Aşama 3'te dinamikleşecek.
        """
        entry = self.chain[idx]
        params = self._build_litellm_params(entry["provider"], entry["model"])
        model_string = params.pop("model")
        return model_string, params
