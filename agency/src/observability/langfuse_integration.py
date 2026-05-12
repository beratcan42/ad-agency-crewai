"""Langfuse entegrasyonu — LiteLLM OTEL callback tabanlı.

Aşama 5: Her LLM çağrısını Langfuse'a trace olarak gönderir.
LiteLLM'in `langfuse_otel` callback'ini kullanır (native callback yerine).
Bu yöntem Langfuse SDK v4.x + LiteLLM arasındaki uyumsuzluğu önler.

Langfuse self-hosted ayakta değilse sessizce devre dışı kalır.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from ..config.settings import settings

log = logging.getLogger(__name__)

_initialized: bool = False


def _langfuse_available() -> bool:
    """Langfuse bağlantı bilgileri dolu mu?"""
    return bool(
        settings.LANGFUSE_ENABLED
        and settings.LANGFUSE_HOST
        and settings.LANGFUSE_PUBLIC_KEY
        and settings.LANGFUSE_SECRET_KEY
    )


def init_langfuse_callbacks() -> bool:
    """LiteLLM callback listesine Langfuse OTEL'i ekler.

    Returns:
        True: callback eklendi
        False: Langfuse devre dışı veya key yok
    """
    global _initialized
    if _initialized:
        return True

    if not _langfuse_available():
        log.info("langfuse.skip: LANGFUSE_HOST / key tanımsız, trace gönderilmeyecek")
        return False

    try:
        import litellm

        # OTEL callback için env vars ayarla
        os.environ["LANGFUSE_PUBLIC_KEY"] = settings.LANGFUSE_PUBLIC_KEY
        os.environ["LANGFUSE_SECRET_KEY"] = settings.LANGFUSE_SECRET_KEY
        # OTEL host — self-hosted Langfuse endpoint
        os.environ["LANGFUSE_OTEL_HOST"] = settings.LANGFUSE_HOST

        # langfuse_otel callback kullan (SDK versiyon uyumsuzluğunu önler)
        if "langfuse_otel" not in litellm.callbacks:
            litellm.callbacks.append("langfuse_otel")

        _initialized = True
        log.info(
            "langfuse.init: OTEL callback aktif, host=%s", settings.LANGFUSE_HOST
        )
        return True
    except Exception as e:
        log.warning("langfuse.init.fail: %s", e)
        return False


def build_langfuse_metadata(
    *,
    agent_id: str,
    client_id: str,
    provider: str,
    model: str,
    chain_idx: int,
) -> dict[str, Any]:
    """LiteLLM acompletion metadata dict'i — Langfuse trace alanları.

    OTEL callback metadata field'ları:
      - trace_name, trace_user_id, tags, trace_metadata
    """
    if not _initialized:
        return {}

    return {
        "trace_name": f"agent.{agent_id}",
        "trace_user_id": client_id,
        "trace_metadata": {
            "agent_id": agent_id,
            "provider": provider,
            "model": model,
            "chain_idx": chain_idx,
        },
        "tags": [agent_id, provider],
    }
