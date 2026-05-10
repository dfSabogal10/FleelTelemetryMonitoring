"""Consistent JSON errors and safe 500 responses.

FastAPI routes handlers registered for ``Exception`` to ``ServerErrorMiddleware`` only;
subclasses such as ``DomainError`` are handled by ``ExceptionMiddleware`` first.
"""

from __future__ import annotations

import logging

from starlette.requests import Request
from starlette.responses import JSONResponse

from app.exceptions import DomainError

logger = logging.getLogger(__name__)


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    """Stable JSON for business/domain failures."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


async def internal_server_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Used by Starlette ServerErrorMiddleware for uncaught errors."""
    logger.exception(
        "internal_server_error method=%s path=%s",
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_server_error",
                "message": "Unexpected server error",
            }
        },
    )
