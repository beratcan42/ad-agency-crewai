"""Token bütçesi middleware — LLM endpoint'lerine bütçe kontrolü uygular.

Aşama 5: POST /agents/*/run ve /agents/*/dispatch endpoint'leri
için müşteri bazlı token bütçesini kontrol eder.
Bütçe aşılırsa HTTP 429 döndürür.
"""

from __future__ import annotations

import logging
import re
from typing import Awaitable, Callable

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from ..guardrails.token_budget import check_budget

log = logging.getLogger(__name__)

# Token bütçesi kontrolü gerektiren path pattern'leri
_BUDGET_CHECK_PATTERNS = [
    re.compile(r"^/agents/[a-z0-9_-]+/run$"),
    re.compile(r"^/agents/[a-z0-9_-]+/dispatch$"),
]


class TokenBudgetMiddleware(BaseHTTPMiddleware):
    """POST /agents/*/run|dispatch isteklerinde token bütçesini kontrol eder."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        path = request.url.path
        method = request.method.upper()

        # Sadece POST istekleri ve ajan çağrı endpoint'leri
        needs_check = (
            method == "POST"
            and any(p.match(path) for p in _BUDGET_CHECK_PATTERNS)
        )

        if not needs_check:
            return await call_next(request)

        # Client ID al
        client_id = request.headers.get("X-Client-Id", "").strip().lower()
        if not client_id:
            # ClientContextMiddleware zaten yakalayacak
            return await call_next(request)

        # Bütçe kontrolü
        try:
            allowed, remaining, budget = await check_budget(
                client_id, estimated_tokens=0, period="daily"
            )
        except Exception as e:
            log.warning("budget_middleware.check.fail: %s", e)
            # Fail-open: hata durumunda izin ver
            allowed, remaining, budget = True, 0, 0

        if not allowed:
            log.warning(
                "budget_middleware.blocked: client=%s remaining=%d budget=%d",
                client_id, remaining, budget,
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Token bütçesi aşıldı",
                    "client_id": client_id,
                    "remaining_tokens": remaining,
                    "budget_tokens": budget,
                },
                headers={"X-Token-Budget-Remaining": str(remaining)},
            )

        response = await call_next(request)

        # Yanıta kalan bütçe header'ı ekle
        if remaining > 0:
            response.headers["X-Token-Budget-Remaining"] = str(remaining)

        return response
