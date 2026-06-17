"""Copy-trade engine tests against a real (SQLite) database.

Covers the full lifecycle: follow → buy opens position → sell closes it →
balance/PnL update → equity (mark-to-market) → leaderboard ranking → reset.
"""
import asyncio
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.database import Base
from app.models.accounts import User, WatchedWallet, Position
import app.services.copytrade as ct


async def _make_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


def _user(nick, balance=1000.0, pos=50.0):
    return User(
        nickname=nick, nickname_lower=nick.lower(), password_hash="x",
        balance_usd=balance, starting_balance_usd=balance, position_size_usd=pos,
    )


# Fixed market data: token "MINT" trades at $0.001, mcap $50k
async def _fake_market(mint):
    prices = {
        "MINT": {"price_usd": 0.001, "market_cap_usd": 50_000.0},
        "MINT2": {"price_usd": 0.002, "market_cap_usd": 80_000.0},
        "DEAD": {"price_usd": None, "market_cap_usd": None},
    }
    return prices.get(mint, {"price_usd": None, "market_cap_usd": None})


async def _fake_batch(mints):
    out = {}
    for m in mints:
        d = await _fake_market(m)
        out[m] = d["price_usd"]
    return out


def test_full_buy_sell_lifecycle():
    async def scenario():
        engine, Session = await _make_db()
        async with Session() as db:
            alice = _user("alice")
            db.add(alice)
            await db.flush()
            db.add(WatchedWallet(user_id=alice.id, wallet="WhaleW"))
            await db.commit()
            alice_id = alice.id

        with patch.object(ct, "get_token_market_data", _fake_market), \
             patch.object(ct, "get_prices_usd_batch", _fake_batch):
            # Whale buys MINT → Alice opens a $50 position
            async with Session() as db:
                opened = await ct.on_watched_buy(db, "WhaleW", "MINT")
                await db.commit()
            assert opened == 1

            async with Session() as db:
                user = (await db.execute(select(User).where(User.id == alice_id))).scalar_one()
                assert round(user.balance_usd, 2) == 950.0  # 1000 - 50
                pos = (await db.execute(select(Position).where(Position.user_id == alice_id))).scalar_one()
                assert pos.status == "open"
                assert pos.invested_usd == 50.0
                # entry price bumped above $0.001 due to mcap offset
                assert pos.entry_price_usd > 0.001
                # token_amount = 50 / entry_price
                assert abs(pos.token_amount - 50.0 / pos.entry_price_usd) < 1e-6

            # Whale sells MINT → Alice's position closes at $0.001
            async with Session() as db:
                closed = await ct.on_watched_sell(db, "WhaleW", "MINT")
                await db.commit()
            assert closed == 1

            async with Session() as db:
                user = (await db.execute(select(User).where(User.id == alice_id))).scalar_one()
                pos = (await db.execute(select(Position).where(Position.user_id == alice_id))).scalar_one()
                assert pos.status == "closed"
                # entered above $0.001, exited at $0.001 → small loss (realism offset)
                assert pos.realized_pnl_usd < 0
                assert user.closed_trades == 1
                assert user.winning_trades == 0
                # balance restored to ~950 + proceeds
                assert round(user.balance_usd, 2) == round(950.0 + pos.proceeds_usd, 2)

        await engine.dispose()
    asyncio.run(scenario())


def test_profit_when_price_rises():
    async def scenario():
        engine, Session = await _make_db()
        async with Session() as db:
            bob = _user("bob")
            db.add(bob)
            await db.flush()
            db.add(WatchedWallet(user_id=bob.id, wallet="W"))
            await db.commit()
            bob_id = bob.id

        # buy at $0.001, then sell at 10x
        async def market_low(mint):
            return {"price_usd": 0.001, "market_cap_usd": 50_000.0}
        async def market_high(mint):
            return {"price_usd": 0.01, "market_cap_usd": 500_000.0}

        with patch.object(ct, "get_token_market_data", market_low):
            async with Session() as db:
                await ct.on_watched_buy(db, "W", "MINT")
                await db.commit()
        with patch.object(ct, "get_token_market_data", market_high):
            async with Session() as db:
                await ct.on_watched_sell(db, "W", "MINT")
                await db.commit()

        async with Session() as db:
            user = (await db.execute(select(User).where(User.id == bob_id))).scalar_one()
            assert user.winning_trades == 1
            assert user.realized_pnl_usd > 0
            assert user.balance_usd > 1000  # net profit on demo balance
        await engine.dispose()
    asyncio.run(scenario())


def test_untradeable_token_skipped():
    async def scenario():
        engine, Session = await _make_db()
        async with Session() as db:
            u = _user("carol")
            db.add(u)
            await db.flush()
            db.add(WatchedWallet(user_id=u.id, wallet="W"))
            await db.commit()
            uid = u.id

        with patch.object(ct, "get_token_market_data", _fake_market):
            async with Session() as db:
                opened = await ct.on_watched_buy(db, "W", "DEAD")  # no price
                await db.commit()
            assert opened == 0
            async with Session() as db:
                user = (await db.execute(select(User).where(User.id == uid))).scalar_one()
                assert user.balance_usd == 1000.0  # nothing spent
        await engine.dispose()
    asyncio.run(scenario())


def test_no_double_position_same_mint():
    async def scenario():
        engine, Session = await _make_db()
        async with Session() as db:
            u = _user("dave")
            db.add(u)
            await db.flush()
            db.add(WatchedWallet(user_id=u.id, wallet="W"))
            await db.commit()

        with patch.object(ct, "get_token_market_data", _fake_market):
            async with Session() as db:
                await ct.on_watched_buy(db, "W", "MINT")
                await db.commit()
            async with Session() as db:
                opened2 = await ct.on_watched_buy(db, "W", "MINT")  # already holding
                await db.commit()
            assert opened2 == 0
        await engine.dispose()
    asyncio.run(scenario())


def test_insufficient_balance_skips():
    async def scenario():
        engine, Session = await _make_db()
        async with Session() as db:
            u = _user("poor", balance=10.0, pos=50.0)  # can't afford $50
            db.add(u)
            await db.flush()
            db.add(WatchedWallet(user_id=u.id, wallet="W"))
            await db.commit()

        with patch.object(ct, "get_token_market_data", _fake_market):
            async with Session() as db:
                opened = await ct.on_watched_buy(db, "W", "MINT")
                await db.commit()
            assert opened == 0
        await engine.dispose()
    asyncio.run(scenario())


def test_equity_and_leaderboard():
    async def scenario():
        engine, Session = await _make_db()
        async with Session() as db:
            a = _user("winner")
            b = _user("holder")
            db.add_all([a, b])
            await db.flush()
            db.add_all([
                WatchedWallet(user_id=a.id, wallet="W"),
                WatchedWallet(user_id=b.id, wallet="W"),
            ])
            await db.commit()
            a_id, b_id = a.id, b.id

        async def market_low(mint):
            return {"price_usd": 0.001, "market_cap_usd": 50_000.0}

        with patch.object(ct, "get_token_market_data", market_low), \
             patch.object(ct, "get_prices_usd_batch", _fake_batch):
            # both open a position in MINT
            async with Session() as db:
                await ct.on_watched_buy(db, "W", "MINT")
                await db.commit()

            # winner sells at 10x → realised profit; holder keeps it open
            async def market_high(mint):
                return {"price_usd": 0.01, "market_cap_usd": 500_000.0}
            with patch.object(ct, "get_token_market_data", market_high):
                async with Session() as db:
                    # close only winner's via targeted source/mint? both share source "W".
                    # Simulate: only winner's wallet sold — but both copied same source.
                    # For the test, close winner's position directly.
                    pos = (await db.execute(
                        select(Position).where(Position.user_id == a_id, Position.status == "open")
                    )).scalar_one()
                    pos.status = "closed"
                    pos.exit_price_usd = 0.01
                    pos.proceeds_usd = pos.token_amount * 0.01
                    pos.realized_pnl_usd = pos.proceeds_usd - pos.invested_usd
                    user_a = (await db.execute(select(User).where(User.id == a_id))).scalar_one()
                    user_a.balance_usd += pos.proceeds_usd
                    user_a.realized_pnl_usd += pos.realized_pnl_usd
                    user_a.closed_trades += 1
                    user_a.winning_trades += 1
                    await db.commit()

            # leaderboard: winner (realised profit) should outrank holder
            async with Session() as db:
                board = await ct.get_leaderboard(db, limit=10)
            assert board[0]["nickname"] == "winner"
            assert board[0]["rank"] == 1
            assert board[0]["total_pnl_usd"] > board[1]["total_pnl_usd"]

            # equity snapshot for holder includes open position marked to market
            async with Session() as db:
                holder = (await db.execute(select(User).where(User.id == b_id))).scalar_one()
                eq = await ct.get_account_equity(db, holder)
                assert eq["open_value_usd"] > 0
                assert eq["equity_usd"] == round(holder.balance_usd + eq["open_value_usd"], 2)
        await engine.dispose()
    asyncio.run(scenario())


def test_reset_account():
    async def scenario():
        engine, Session = await _make_db()
        async with Session() as db:
            u = _user("resetme")
            db.add(u)
            await db.flush()
            db.add(WatchedWallet(user_id=u.id, wallet="W"))
            await db.commit()
            uid = u.id

        with patch.object(ct, "get_token_market_data", _fake_market):
            async with Session() as db:
                await ct.on_watched_buy(db, "W", "MINT")
                await db.commit()
            async with Session() as db:
                user = (await db.execute(select(User).where(User.id == uid))).scalar_one()
                assert user.balance_usd < 1000
                await ct.reset_account(db, user)
                await db.commit()
            async with Session() as db:
                user = (await db.execute(select(User).where(User.id == uid))).scalar_one()
                assert user.balance_usd == 1000.0
                assert user.closed_trades == 0
                remaining = (await db.execute(
                    select(Position).where(Position.user_id == uid)
                )).scalars().all()
                assert remaining == []
        await engine.dispose()
    asyncio.run(scenario())
