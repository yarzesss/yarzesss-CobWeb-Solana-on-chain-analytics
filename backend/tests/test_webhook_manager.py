"""Dynamic webhook address management."""
import asyncio
from unittest.mock import patch, AsyncMock

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.database import Base
from app.models.accounts import User, WatchedWallet
import app.services.webhook_manager as wm


async def _make_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


def test_union_of_watched_wallets_dedups():
    async def scenario():
        engine, Session = await _make_db()
        async with Session() as db:
            u1 = User(nickname="a", nickname_lower="a", password_hash="x")
            u2 = User(nickname="b", nickname_lower="b", password_hash="x")
            db.add_all([u1, u2]); await db.flush()
            # both follow the same wallet W1; u2 also follows W2
            db.add_all([
                WatchedWallet(user_id=u1.id, wallet="W1"),
                WatchedWallet(user_id=u2.id, wallet="W1"),
                WatchedWallet(user_id=u2.id, wallet="W2"),
            ])
            await db.commit()
            wallets = await wm.get_all_watched_wallets(db)
        await engine.dispose()
        return wallets

    wallets = asyncio.run(scenario())
    assert set(wallets) == {"W1", "W2"}      # deduped union
    assert len(wallets) == 2


def test_address_list_always_includes_anchor_and_caps():
    addrs = wm._build_address_list(["A", "B"])
    assert wm.ANCHOR_ADDRESS in addrs
    assert "A" in addrs and "B" in addrs
    # cap
    many = [f"w{i}" for i in range(200)]
    capped = wm._build_address_list(many)
    assert len(capped) <= wm.MAX_WEBHOOK_ADDRESSES


def test_sync_noop_when_not_configured():
    async def scenario():
        engine, Session = await _make_db()
        async with Session() as db:
            # no HELIUS_WEBHOOK_ID in test settings → graceful no-op
            res = await wm.sync_webhook_addresses(db)
        await engine.dispose()
        return res

    res = asyncio.run(scenario())
    assert res["synced"] is False
    assert "not configured" in res["reason"]


def test_sync_pushes_addresses_when_configured():
    async def scenario():
        engine, Session = await _make_db()
        async with Session() as db:
            u = User(nickname="a", nickname_lower="a", password_hash="x")
            db.add(u); await db.flush()
            db.add(WatchedWallet(user_id=u.id, wallet="WHALE"))
            await db.commit()

            captured = {}

            class FakeResp:
                status_code = 200
                text = ""
                def json(self):
                    return {
                        "webhookURL": "https://x/webhooks/helius",
                        "transactionTypes": ["ANY"],
                        "webhookType": "enhanced",
                        "accountAddresses": ["old"],
                    }

            class FakeClient:
                async def __aenter__(self): return self
                async def __aexit__(self, *a): return False
                async def get(self, url, params=None): return FakeResp()
                async def put(self, url, params=None, json=None):
                    captured["addresses"] = json["accountAddresses"]
                    return FakeResp()

            with patch.object(wm.settings, "HELIUS_WEBHOOK_ID", "wh_123"), \
                 patch.object(wm.settings, "HELIUS_API_KEY", "key_123"), \
                 patch.object(wm.httpx, "AsyncClient", lambda *a, **k: FakeClient()):
                res = await wm.sync_webhook_addresses(db)
        await engine.dispose()
        return res, captured

    res, captured = asyncio.run(scenario())
    assert res["synced"] is True
    assert "WHALE" in captured["addresses"]
    assert wm.ANCHOR_ADDRESS in captured["addresses"]
