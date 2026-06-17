"""Copy-trade bot engine — the heart of the paper-trading competition.

Two events drive everything, both fed by the Helius webhook:

  on_watched_buy(wallet, mint):
    For every user watching `wallet` who doesn't already hold an open
    position in `mint`, open a virtual position sized by their
    position_size_usd, entered at the current market price plus a small
    mcap offset (realism — you never get the watched wallet's exact fill).
    Cash leaves balance_usd into the position.

  on_watched_sell(wallet, mint):
    For every user holding an open position in `mint` that was copied
    from `wallet`, close it at the current price. Proceeds (token_amount ×
    current price) return to balance_usd; realised P&L is booked.

Equity = cash balance + mark-to-market value of open positions.
The leaderboard ranks by equity.

All prices come from the existing market-data service, which already
covers fresh bonding-curve tokens via on-chain trade derivation. If a
token has no price (untradeable), the bot skips it — we won't fabricate.
"""
import time
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.accounts import Position, User, WatchedWallet
from app.services.prices import get_token_market_data, get_prices_usd_batch


async def _current_price_and_mcap(mint: str) -> tuple[Optional[float], Optional[float]]:
    data = await get_token_market_data(mint)
    price = data.get("price_usd")
    mcap = data.get("market_cap_usd")
    if price is None or price <= 0:
        return None, None
    return float(price), (float(mcap) if mcap else None)


async def on_watched_buy(db: AsyncSession, wallet: str, mint: str) -> int:
    """Open virtual positions for everyone watching `wallet`. Returns # opened."""
    watchers = (
        await db.execute(select(WatchedWallet.user_id).where(WatchedWallet.wallet == wallet))
    ).scalars().all()
    if not watchers:
        return 0

    price, mcap = await _current_price_and_mcap(mint)
    if price is None:
        return 0  # untradeable / unpriced — skip honestly

    # Realism: enter as if mcap were a bit higher than the watched wallet's entry.
    entry_price = price
    if mcap and mcap > 0:
        bumped_mcap = mcap + settings.COPY_ENTRY_MCAP_OFFSET_USD
        entry_price = price * (bumped_mcap / mcap)

    now = int(time.time())
    opened = 0

    for user_id in watchers:
        user = (
            await db.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()
        if user is None:
            continue

        # one open position per (user, mint) — don't stack copies
        existing = (
            await db.execute(
                select(Position.id).where(
                    Position.user_id == user_id,
                    Position.mint == mint,
                    Position.status == "open",
                )
            )
        ).first()
        if existing is not None:
            continue

        size = user.position_size_usd
        if size > user.balance_usd:
            continue  # not enough demo cash; skip rather than go negative
        if size < settings.MIN_POSITION_SIZE_USD:
            continue

        token_amount = size / entry_price
        user.balance_usd -= size

        db.add(Position(
            user_id=user_id,
            mint=mint,
            source_wallet=wallet,
            status="open",
            invested_usd=size,
            entry_price_usd=entry_price,
            entry_mcap_usd=(mcap + settings.COPY_ENTRY_MCAP_OFFSET_USD) if mcap else None,
            token_amount=token_amount,
            opened_at=now,
        ))
        opened += 1

    await db.flush()
    return opened


async def on_watched_sell(db: AsyncSession, wallet: str, mint: str) -> int:
    """Close positions in `mint` copied from `wallet`. Returns # closed."""
    positions = (
        await db.execute(
            select(Position).where(
                Position.source_wallet == wallet,
                Position.mint == mint,
                Position.status == "open",
            )
        )
    ).scalars().all()
    if not positions:
        return 0

    price, _ = await _current_price_and_mcap(mint)
    if price is None:
        return 0  # can't price the exit — leave open, try again on next sell

    now = int(time.time())
    closed = 0

    for pos in positions:
        proceeds = pos.token_amount * price
        pnl = proceeds - pos.invested_usd

        pos.status = "closed"
        pos.exit_price_usd = price
        pos.proceeds_usd = round(proceeds, 4)
        pos.realized_pnl_usd = round(pnl, 4)
        pos.closed_at = now

        user = (
            await db.execute(select(User).where(User.id == pos.user_id))
        ).scalar_one_or_none()
        if user is not None:
            user.balance_usd += proceeds
            user.realized_pnl_usd += pnl
            user.closed_trades += 1
            if pnl > 0:
                user.winning_trades += 1
        closed += 1

    await db.flush()
    return closed


async def get_open_positions_value(db: AsyncSession, user_id: int) -> Dict[str, Any]:
    """Mark-to-market all open positions for a user."""
    positions = (
        await db.execute(
            select(Position).where(Position.user_id == user_id, Position.status == "open")
        )
    ).scalars().all()
    if not positions:
        return {"open_value_usd": 0.0, "positions": []}

    mints = list({p.mint for p in positions})
    prices = await get_prices_usd_batch(mints)

    total = 0.0
    rows = []
    for p in positions:
        price = prices.get(p.mint)
        if price is None:
            # fall back to single-token derivation for fresh tokens
            single, _ = await _current_price_and_mcap(p.mint)
            price = single
        cur_value = (p.token_amount * price) if price else p.invested_usd
        unreal = cur_value - p.invested_usd
        total += cur_value
        rows.append({
            "mint": p.mint,
            "source_wallet": p.source_wallet,
            "invested_usd": round(p.invested_usd, 2),
            "current_value_usd": round(cur_value, 2),
            "unrealized_pnl_usd": round(unreal, 2),
            "entry_price_usd": p.entry_price_usd,
            "current_price_usd": price,
            "opened_at": p.opened_at,
            "priced": price is not None,
        })

    return {"open_value_usd": round(total, 2), "positions": rows}


async def get_account_equity(db: AsyncSession, user: User) -> Dict[str, Any]:
    """Full account snapshot: cash + open positions marked to market."""
    open_data = await get_open_positions_value(db, user.id)
    equity = user.balance_usd + open_data["open_value_usd"]
    winrate = (user.winning_trades / user.closed_trades) if user.closed_trades else 0.0
    return {
        "nickname": user.nickname,
        "balance_usd": round(user.balance_usd, 2),
        "open_value_usd": open_data["open_value_usd"],
        "equity_usd": round(equity, 2),
        "starting_balance_usd": user.starting_balance_usd,
        "total_pnl_usd": round(equity - user.starting_balance_usd, 2),
        "total_pnl_pct": round((equity - user.starting_balance_usd) / user.starting_balance_usd * 100, 2),
        "realized_pnl_usd": round(user.realized_pnl_usd, 2),
        "position_size_usd": user.position_size_usd,
        "closed_trades": user.closed_trades,
        "winning_trades": user.winning_trades,
        "winrate": round(winrate, 4),
        "open_positions": open_data["positions"],
    }


async def reset_account(db: AsyncSession, user: User) -> None:
    """Wipe positions, restore starting balance and stats."""
    await db.execute(
        Position.__table__.delete().where(Position.user_id == user.id)
    )
    user.balance_usd = user.starting_balance_usd
    user.realized_pnl_usd = 0.0
    user.closed_trades = 0
    user.winning_trades = 0
    await db.flush()


async def get_leaderboard(db: AsyncSession, limit: int = 50) -> List[Dict[str, Any]]:
    """Rank accounts by equity (cash + open positions marked to market)."""
    users = (await db.execute(select(User))).scalars().all()
    if not users:
        return []

    # Gather every open mint once, batch-price them
    open_positions = (
        await db.execute(select(Position).where(Position.status == "open"))
    ).scalars().all()
    all_mints = list({p.mint for p in open_positions})
    prices = await get_prices_usd_batch(all_mints) if all_mints else {}

    by_user_open: Dict[int, float] = {}
    for p in open_positions:
        price = prices.get(p.mint)
        value = (p.token_amount * price) if price else p.invested_usd
        by_user_open[p.user_id] = by_user_open.get(p.user_id, 0.0) + value

    rows = []
    for u in users:
        open_val = by_user_open.get(u.id, 0.0)
        equity = u.balance_usd + open_val
        winrate = (u.winning_trades / u.closed_trades) if u.closed_trades else 0.0
        rows.append({
            "nickname": u.nickname,
            "equity_usd": round(equity, 2),
            "total_pnl_usd": round(equity - u.starting_balance_usd, 2),
            "total_pnl_pct": round((equity - u.starting_balance_usd) / u.starting_balance_usd * 100, 2),
            "realized_pnl_usd": round(u.realized_pnl_usd, 2),
            "closed_trades": u.closed_trades,
            "winrate": round(winrate, 4),
        })

    rows.sort(key=lambda r: r["equity_usd"], reverse=True)
    rows = rows[:limit]
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    return rows
