from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str | None = Depends(api_key_header)) -> None:
    if not settings.api_key:
        return

    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.requests: dict[str, Deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        limit = settings.rate_limit_requests
        window = settings.rate_limit_window_seconds

        if limit <= 0 or window <= 0:
            return await call_next(request)

        now = time.monotonic()
        client = request.client.host if request.client else "unknown"
        bucket = self.requests[client]

        while bucket and now - bucket[0] > window:
            bucket.popleft()

        if len(bucket) >= limit:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests"},
            )

        bucket.append(now)
        return await call_next(request)
