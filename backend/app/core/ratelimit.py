"""Per-IP rate limiting backed by Redis.

Why this exists: a single cold-cache request to /token/{ca} fans out into
up to ~80 Helius API calls (50 wallets × SOL transfer history + metadata +
dev risk). Without a limiter, anyone looping over random CAs can burn the
entire Helius quota in under an hour.

Design:
- Fixed window counter: INCR + EXPIRE on `rl:{scope}:{ip}:{window}`.
- Fail-open: if Redis is unavailable, requests pass (availability over
  strictness — Redis being down already degrades caching anyway).
- Trusts X-Forwarded-For only for the first hop (set by your reverse proxy).

NOTE: no `from __future__ import annotations` here on purpose — pydantic 2.9
cannot resolve stringified `Request` annotations on a class-based dependency's
__call__ method (PydanticUndefinedAnnotation at startup).
"""
import time

from fastapi import HTTPException, Request

from app.config import settings
from app.core.cache import get_redis


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimiter:
    """FastAPI dependency: `Depends(RateLimiter("token", times=10, seconds=60))`."""

    def __init__(self, scope: str, times: int, seconds: int = 60) -> None:
        self.scope = scope
        self.times = times
        self.seconds = seconds

    async def __call__(self, request: Request) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return

        ip = _client_ip(request)
        window = int(time.time()) // self.seconds
        key = f"rl:{self.scope}:{ip}:{window}"

        try:
            r = await get_redis()
            current = await r.incr(key)
            if current == 1:
                await r.expire(key, self.seconds)
        except Exception:
            # Fail-open: never take the API down because Redis hiccuped
            return

        if current > self.times:
            retry_after = self.seconds - (int(time.time()) % self.seconds)
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Slow down and try again shortly.",
                headers={"Retry-After": str(retry_after)},
            )


# Heavy endpoints fan out into many Helius calls — keep these tight
heavy_limiter = RateLimiter("heavy", times=settings.RATE_LIMIT_HEAVY_PER_MINUTE)
# Light endpoints (auth, watchlist, paginated reads from cache)
light_limiter = RateLimiter("light", times=settings.RATE_LIMIT_LIGHT_PER_MINUTE)
