"""FastAPI giriş noktası — Aşama 2+5 app."""

from __future__ import annotations

import asyncio
import logging
import logging.config
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from . import __version__
from .api import api_router
from .config.settings import settings
from .middleware.client_context import ClientContextMiddleware
from .middleware.token_budget import TokenBudgetMiddleware

# --- Logging -------------------------------------------------------

LOG_FORMAT = "%(asctime)s %(levelname)-7s [%(name)s] %(message)s"
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format=LOG_FORMAT,
    stream=sys.stdout,
)
log = logging.getLogger("agency")


# --- Lifespan ------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    log.info("agency.startup version=%s env=%s", __version__, settings.ENV)

    # Langfuse callback init (Asama 5)
    try:
        from .observability.langfuse_integration import init_langfuse_callbacks
        init_langfuse_callbacks()
    except Exception as e:
        log.warning("langfuse.init.skip: %s", e)

    poller_task: asyncio.Task | None = None
    if settings.VAULT_WATCHER_ENABLED:
        from .vault.poller import vault_poller_loop

        poller_task = asyncio.create_task(vault_poller_loop(), name="vault-poller")
    yield
    if poller_task is not None:
        poller_task.cancel()
        try:
            await poller_task
        except asyncio.CancelledError:
            pass
    log.info("agency.shutdown")


# --- App -----------------------------------------------------------


app = FastAPI(
    title="Ad Agency API",
    version=__version__,
    description="CrewAI Multi-Agent Reklam Ajansı - Orchestrator API",
    lifespan=lifespan,
)

# Middleware (sira onemli: once client context, sonra budget)
app.add_middleware(TokenBudgetMiddleware)
app.add_middleware(ClientContextMiddleware)

# Routes
app.include_router(api_router)


@app.get("/", tags=["root"], include_in_schema=False)
async def root() -> JSONResponse:
    return JSONResponse(
        {
            "name": "ad-agency",
            "version": __version__,
            "docs": "/docs",
            "health": "/healthz",
        }
    )
