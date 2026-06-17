"""Copy-trade Simulator: "what if you had copied this wallet for N days?"

Replays the wallet's actual swaps within the window using the same two
parsers as the PnL engine (swap events + pump.fun fallback) and reports
realized ROI on the SOL actually deployed.

Honest limitations, surfaced in the response:
- realized-only (open positions are not marked to market),
- assumes identical fills (no slippage modelling),
- window limited by the last 500 transactions.
"""
import time
from collections import defaultdict
from typing import Any, Dict

from app.config import settings
from app.core.cache import get_json, set_json
from app.services.helius import get_helius_client
from app.services.pnl import _parse_raw_transfers, _parse_swap_event


async def simulate_copy_trade(wallet_address: str, days: int = 30) -> Dict[str, Any]:
    days = max(1, min(days, 90))
    cache_key = f"wallet:{wallet_address}:simulate:{days}"
    cached = await get_json(cache_key)
    if cached is not None:
        return cached

    helius = get_helius_client()
    txs = await helius.get_wallet_transactions(wallet_address, limit=500)
    sol_price = await helius.get_sol_price_usd()

    if not isinstance(txs, list):
        txs = []

    cutoff = int(time.time()) - days * 86400

    per_token: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {"spent": 0.0, "received": 0.0}
    )
    trades = 0
    window_reached = False  # did history actually cover the whole window?

    for tx in sorted(txs, key=lambda t: t.get("timestamp") or 0):
        ts = tx.get("timestamp") or 0
        if ts < cutoff:
            window_reached = True  # we saw txs older than the window start
            continue

        parsed = _parse_swap_event(tx, wallet_address) or _parse_raw_transfers(tx, wallet_address)
        if not parsed:
            continue
        side, mint, token_amt, sol_amt = parsed
        if token_amt <= 0 or sol_amt <= 0:
            continue

        trades += 1
        if side == "buy":
            per_token[mint]["spent"] += sol_amt
        else:
            per_token[mint]["received"] += sol_amt

    total_spent = sum(t["spent"] for t in per_token.values())
    total_received = sum(t["received"] for t in per_token.values())
    realized_sol = total_received - total_spent

    wins = 0
    closed = 0
    best: Dict[str, Any] = {}
    worst: Dict[str, Any] = {}
    for mint, t in per_token.items():
        if t["received"] <= 0:
            continue
        closed += 1
        pnl = t["received"] - t["spent"]
        if pnl > 0:
            wins += 1
        if not best or pnl > best["sol_pnl"]:
            best = {"mint": mint, "sol_pnl": round(pnl, 4)}
        if not worst or pnl < worst["sol_pnl"]:
            worst = {"mint": mint, "sol_pnl": round(pnl, 4)}

    roi_pct = (realized_sol / total_spent * 100) if total_spent > 0 else 0.0

    result = {
        "wallet_address": wallet_address,
        "days": days,
        "trades": trades,
        "tokens_traded": len(per_token),
        "closed_positions": closed,
        "win_positions": wins,
        "sol_invested": round(total_spent, 4),
        "sol_returned": round(total_received, 4),
        "realized_sol_pnl": round(realized_sol, 4),
        "realized_usd_pnl": round(realized_sol * sol_price, 2),
        "roi_pct": round(roi_pct, 2),
        "sol_price_usd": round(sol_price, 2),
        # transparency flags
        "full_window_covered": window_reached or len(txs) < 500,
        "notes": "Realized PnL only; open positions excluded; no slippage model.",
    }

    await set_json(cache_key, result, ttl=settings.CACHE_TTL_WALLET)
    return result
