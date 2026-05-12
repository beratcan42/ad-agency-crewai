"""X-Client-Id middleware — multi-tenant isolasyon için.

Aşağıdaki path'ler X-Client-Id gerektirmez:
- /healthz, /readyz, /version
- /docs, /redoc, /openapi.json
- /admin/* (sadece admin token ile)
"""

from __future__ import annotations

import re
from contextvars import ContextVar
from typing import Awaitable, Callable

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

# Request boyunca client_id'yi taşıyan context var
_current_client_id: ContextVar[str | None] = ContextVar("current_client_id", default=None)

# X-Client-Id zorunluluğundan muaf path'ler
_EXEMPT_PATTERNS = [
    re.compile(r"^/healthz/?$"),
    re.compile(r"^/readyz/?$"),
    re.compile(r"^/version/?$"),
    re.compile(r"^/docs/?$"),
    re.compile(r"^/redoc/?$"),
    re.compile(r"^/openapi\.json$"),
    re.compile(r"^/admin/.*"),
    re.compile(r"^/static/.*"),
]

# X-Client-Id geçerli format: [a-z0-9_-]{2,64}
_CLIENT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")


class ClientContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        path = request.url.path
        is_exempt = any(p.match(path) for p in _EXEMPT_PATTERNS)

        client_id = request.headers.get("X-Client-Id", "").strip().lower()

        # BaseHTTPMiddleware'de raise HTTPException Starlette exception handler'ina
        # ulasmiyor; bu yuzden dogrudan JSONResponse donduruyoruz.
        if not is_exempt:
            if not client_id:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "X-Client-Id header is required"},
                )
            if not _CLIENT_ID_RE.match(client_id):
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "detail": (
                            "Invalid X-Client-Id: küçük harf, rakam, '-' veya '_' "
                            "olmalı; 2-64 karakter."
                        )
                    },
                )

        token = _current_client_id.set(client_id or None)
        try:
            response = await call_next(request)
            if client_id:
                response.headers["X-Client-Id"] = client_id
            return response
        finally:
            _current_client_id.reset(token)


def get_client_id() -> str | None:
    """Aktif request için client_id'yi döndür (yoksa None)."""
    return _current_client_id.get()


def require_client_id() -> str:
    """FastAPI dependency: client_id zorunlu."""
    cid = _current_client_id.get()
    if not cid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Client-Id header missing",
        )
    return cid
