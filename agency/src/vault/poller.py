"""Arka plan Vault tarayici — asyncio sleep ile polling."""

from __future__ import annotations

import asyncio
import logging

from ..config.settings import settings
from .sync_db import poll_vault_once

log = logging.getLogger(__name__)

_state: dict[str, tuple[int, str]] = {}


async def vault_poller_loop() -> None:
    """Uvicorn lifespan icinden create_task ile baslatilir."""
    if not settings.VAULT_WATCHER_ENABLED:
        log.info("vault.poller.disabled")
        return
    log.info("vault.poller.start interval_sec=%s", settings.WATCHER_POLLING_INTERVAL)
    try:
        while True:
            try:
                await poll_vault_once(_state)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("vault.poller.tick_error")
            await asyncio.sleep(max(1.0, float(settings.WATCHER_POLLING_INTERVAL)))
    except asyncio.CancelledError:
        log.info("vault.poller.cancelled")
        raise
