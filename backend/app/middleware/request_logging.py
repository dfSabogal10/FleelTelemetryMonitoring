"""Logs method, path, status, duration — uses HTTP middleware (not BaseHTTPMiddleware) so exception handlers still run."""

from __future__ import annotations

import logging
import time

from collections.abc import Awaitable, Callable

from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.request")


def register_request_logging(app: FastAPI) -> None:
    """Register `@app.middleware("http")` logging — avoids BaseHTTPMiddleware breaking exception propagation."""

    @app.middleware("http")
    async def log_requests(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "request_error method=%s path=%s duration_ms=%.2f",
                request.method,
                request.url.path,
                elapsed_ms,
            )
            raise
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "request method=%s path=%s status=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response
