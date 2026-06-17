"""Singleflight: deduplicate identical expensive computations across requests.

The deep token analysis takes 30-60s cold and fans out into dozens of
Helius calls. Ten users opening the same trending token must trigger ONE
computation, not ten. The async server handles concurrent connections
fine (it's all awaited I/O) — the scarce resource is the Helius quota,
and this is what protects it.

Pattern: Redis SET NX lock per key. The winner computes and writes the
result to cache; everyone else polls the cache and picks the result up
the moment it lands.
"""
import asyncio
import uuid
from typing import Any, Awaitable, Callable, Optional, Tuple

from app.core.cache import get_redis, get_json, set_json

LOCK_TTL = 120          # seconds — must exceed worst-case compute time
POLL_INTERVAL = 1.5
WAIT_BUDGET = 25.0      # how long a follower waits before giving up


async def _try_lock(key: str) -> Optional[str]:
    try:
        r = await get_redis()
        token = uuid.uuid4().hex
        ok = await r.set(f"sf:lock:{key}", token, nx=True, ex=LOCK_TTL)
        return token if ok else None
    except Exception:
        # Redis down → behave as if we won the lock (degrade to no dedup)
        return "no-redis"


async def _release(key: str, token: str) -> None:
    if token == "no-redis":
        return
    try:
        r = await get_redis()
        current = await r.get(f"sf:lock:{key}")
        if current is not None and (
            current == token or current == token.encode()
        ):
            await r.delete(f"sf:lock:{key}")
    except Exception:
        pass


async def singleflight(
    key: str,
    compute: Callable[[], Awaitable[Any]],
    result_ttl: int,
) -> Tuple[Any, bool]:
    """Returns (result, fresh). fresh=False if served from cache / a peer.

    result may be None if a peer holds the lock and didn't finish within
    the wait budget — the caller decides what to show meanwhile.
    """
    cache_key = f"sf:result:{key}"

    cached = await get_json(cache_key)
    if cached is not None:
        return cached, False

    token = await _try_lock(key)
    if token is not None:
        try:
            result = await compute()
            await set_json(cache_key, result, ttl=result_ttl)
            return result, True
        finally:
            await _release(key, token)

    # Someone else is computing — wait for their result to land
    waited = 0.0
    while waited < WAIT_BUDGET:
        await asyncio.sleep(POLL_INTERVAL)
        waited += POLL_INTERVAL
        cached = await get_json(cache_key)
        if cached is not None:
            return cached, False

    return None, False
