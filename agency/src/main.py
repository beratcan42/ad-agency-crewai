"""FastAPI giriş noktası — Aşama 2 minimal app."""

from __future__ import annotations

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
    # Aşama 3+ : Redis pool, DB pool, OpenTelemetry start, vault watcher subscribe
    yield
    log.info("agency.shutdown")


# --- App -----------------------------------------------------------


app = FastAPI(
    title="Ad Agency API",
    version=__version__,
    description="CrewAI Multi-Agent Reklam Ajansı - Orchestrator API",
    lifespan=lifespan,
)

# Middleware
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
