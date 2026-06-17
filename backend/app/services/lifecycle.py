"""Token Lifecycle Stage — Wyckoff-style phase from recent trade flow.

Heuristic over the latest ~100 transactions of the token:
classify each as a buy (someone paid SOL for tokens) or a sell
(someone received SOL for tokens), then look at the buy ratio and
the balance of unique buyers vs sellers.

    buy_ratio >= 0.62                → MARKUP        (demand dominates)
    buy_ratio <= 0.38                → DUMP          (exit dominates)
    in between, more buyers active   → ACCUMULATION  (quiet absorption)
    in between, more sellers active  → DISTRIBUTION  (quiet unloading)
    fewer than 5 classified trades   → UNKNOWN       (not enough signal)

This is intentionally simple and explainable — the UI shows the raw
counts next to the verdict so the user can judge for themselves.
"""
from typing import Any, Dict, List, Optional, Set, Tuple

from app.config import settings
from app.core.cache import get_json, set_json
from app.services.helius import get_helius_client

MIN_TRADES_FOR_SIGNAL = 5


def _classify_tx(tx: Dict[str, Any], mint: str) -> Optional[Tuple[str, str]]:
    """('buy'|'sell', actor_wallet) for this tx relative to `mint`, or None."""
    swap = (tx.get("events") or {}).get("swap") or {}

    # Fast path: explicit swap event
    if swap:
        ni = swap.get("nativeInput") or {}
        no = swap.get("nativeOutput") or {}
        for out in swap.get("tokenOutputs") or []:
            if out.get("mint") == mint and ni.get("account"):
                return ("buy", ni["account"])
        for inp in swap.get("tokenInputs") or []:
            if inp.get("mint") == mint and no.get("account"):
                return ("sell", no["account"])

    # Fallback: token transfer + that wallet's net SOL change (pump.fun path)
    balance_by_account = {
        acc.get("account"): acc.get("nativeBalanceChange") or 0
        for acc in tx.get("accountData") or []
    }
    for transfer in tx.get("tokenTransfers") or []:
        if transfer.get("mint") != mint:
            continue
        recipient = transfer.get("toUserAccount")
        sender = transfer.get("fromUserAccount")
        if recipient and balance_by_account.get(recipient, 0) < -100_000:  # spent >0.0001 SOL
            return ("buy", recipient)
        if sender and balance_by_account.get(sender, 0) > 100_000:
            return ("sell", sender)

    return None


def compute_lifecycle_from_txs(txs: List[Dict[str, Any]], mint: str) -> Dict[str, Any]:
    """Pure function — unit-testable without network."""
    buys = 0
    sells = 0
    buyers: Set[str] = set()
    sellers: Set[str] = set()

    for tx in txs or []:
        side = _classify_tx(tx, mint)
        if side is None:
            continue
        action, wallet = side
        if action == "buy":
            buys += 1
            buyers.add(wallet)
        else:
            sells += 1
            sellers.add(wallet)

    total = buys + sells
    if total < MIN_TRADES_FOR_SIGNAL:
        stage = "unknown"
    else:
        ratio = buys / total
        if ratio >= 0.62:
            stage = "markup"
        elif ratio <= 0.38:
            stage = "dump"
        elif len(buyers) >= len(sellers):
            stage = "accumulation"
        else:
            stage = "distribution"

    return {
        "stage": stage,
        "buy_count": buys,
        "sell_count": sells,
        "unique_buyers": len(buyers),
        "unique_sellers": len(sellers),
        "window_trades": total,
    }


async def compute_lifecycle(mint: str) -> Dict[str, Any]:
    """Lifecycle from the most recent page of the token's transactions."""
    cache_key = f"token:{mint}:lifecycle"
    cached = await get_json(cache_key)
    if cached is not None:
        return cached

    helius = get_helius_client()
    # One API call: newest 100 txs (Helius returns newest-first)
    txs = await helius._fetch_all_transactions(mint, limit=100)
    result = compute_lifecycle_from_txs(txs, mint)

    await set_json(cache_key, result, ttl=120)  # short TTL — stages move fast
    return result
