"""models.yaml yükleyici."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from .settings import settings


@lru_cache(maxsize=1)
def load_models_config() -> dict[str, Any]:
    """models.yaml dosyasını okur ve dict döndürür."""
    path: Path = settings.models_yaml_path
    if not path.exists():
        raise FileNotFoundError(f"models.yaml bulunamadi: {path}")
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_agent_chain(agent_id: str) -> list[dict[str, str]]:
    cfg = load_models_config()
    agents = cfg.get("agents", {})
    if agent_id not in agents:
        raise KeyError(f"Ajan tanımı yok: {agent_id}")
    return agents[agent_id].get("chain", [])


def get_agent_meta(agent_id: str) -> dict[str, Any]:
    cfg = load_models_config()
    return cfg.get("agents", {}).get(agent_id, {})


def get_provider_config(provider: str) -> dict[str, Any]:
    cfg = load_models_config()
    providers = cfg.get("providers", {})
    if provider not in providers:
        raise KeyError(f"Sağlayıcı tanımı yok: {provider}")
    return providers[provider]
