"""Singleflight: concurrent identical requests must compute once."""
import asyncio
from unittest.mock import patch

import app.core.jobs as jobs
from tests.conftest_fakes import FakeRedis


def test_concurrent_callers_compute_once():
    fake = FakeRedis()
    store = {}
    calls = {"n": 0}

    async def fake_get_redis():
        return fake

    async def fake_get_json(key):
        return store.get(key)

    async def fake_set_json(key, value, ttl=None):
        store[key] = value

    async def compute():
        calls["n"] += 1
        await asyncio.sleep(0.05)
        return {"answer": 42}

    async def scenario():
        results = await asyncio.gather(*[
            jobs.singleflight("k1", compute, result_ttl=60) for _ in range(5)
        ])
        return results

    with patch.object(jobs, "get_redis", fake_get_redis), \
         patch.object(jobs, "get_json", fake_get_json), \
         patch.object(jobs, "set_json", fake_set_json), \
         patch.object(jobs, "POLL_INTERVAL", 0.02):
        results = asyncio.run(scenario())

    assert calls["n"] == 1, f"computed {calls['n']} times, expected 1"
    payloads = [r[0] for r in results if r[0] is not None]
    assert len(payloads) == 5
    assert all(p == {"answer": 42} for p in payloads)
    fresh_flags = [r[1] for r in results]
    assert sum(fresh_flags) == 1  # exactly one caller actually computed


def test_cached_result_short_circuits():
    store = {"sf:result:k2": {"cached": True}}
    calls = {"n": 0}

    async def fake_get_json(key):
        return store.get(key)

    async def compute():
        calls["n"] += 1
        return {}

    with patch.object(jobs, "get_json", fake_get_json):
        result, fresh = asyncio.run(jobs.singleflight("k2", compute, result_ttl=60))

    assert result == {"cached": True} and fresh is False and calls["n"] == 0
