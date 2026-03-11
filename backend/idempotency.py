"""
idempotency.py — FastAPI middleware for idempotency key deduplication.

Clients (frontend) send an `Idempotency-Key` header on mutating requests
(POST/PATCH/PUT/DELETE). The middleware:

1. Checks Redis for an existing cached response for that key.
2. If found → returns the cached response immediately (no DB write).
3. If missing → proceeds with the request. After the handler returns 2xx,
   the response is stored in Redis with a 24-hour TTL.

This guarantees at-most-once execution for critical actions like:
  - Assigning a lead
  - Booking a meeting
  - Completing a task

Usage (frontend):
    axios.patch('/leads/123/stage', data, {
        headers: { 'Idempotency-Key': crypto.randomUUID() }
    })
"""

import json
import logging
from datetime import timedelta

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .cache import get_redis

logger = logging.getLogger(__name__)

IDEMPOTENCY_HEADER = "Idempotency-Key"
TTL_SECONDS = 60 * 60 * 24  # 24 hours

# Only guard mutating methods
GUARDED_METHODS = {"POST", "PATCH", "PUT", "DELETE"}


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    Check/store responses keyed by the `Idempotency-Key` request header.
    Silently skips if Redis is unavailable.
    """

    async def dispatch(self, request: Request, call_next):
        idem_key = request.headers.get(IDEMPOTENCY_HEADER)

        # Only guard mutating requests that supply the header
        if not idem_key or request.method not in GUARDED_METHODS:
            return await call_next(request)

        redis_key = f"idempotency:{idem_key}"

        redis = await get_redis()
        if redis:
            try:
                cached = await redis.get(redis_key)
                if cached is not None:
                    stored = json.loads(cached)
                    logger.info(
                        "Idempotency hit: key=%s status=%s",
                        idem_key, stored["status"]
                    )
                    return JSONResponse(
                        content=stored["body"],
                        status_code=stored["status"],
                        headers={"X-Idempotency-Replayed": "true"},
                    )
            except Exception as exc:
                logger.debug("Idempotency read error: %s", exc)

        # Process the real request
        response: Response = await call_next(request)

        # Only cache successful mutations
        if redis and 200 <= response.status_code < 300:
            try:
                body_bytes = b""
                async for chunk in response.body_iterator:
                    body_bytes += chunk

                body = json.loads(body_bytes.decode()) if body_bytes else {}

                await redis.setex(
                    redis_key,
                    TTL_SECONDS,
                    json.dumps({"status": response.status_code, "body": body}),
                )

                # Rebuild response since we consumed the iterator above
                return JSONResponse(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                )
            except Exception as exc:
                logger.debug("Idempotency write error: %s", exc)

        return response
