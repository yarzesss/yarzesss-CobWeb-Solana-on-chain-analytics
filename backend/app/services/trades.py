"""Extract buys & sells from a Helius enhanced-webhook payload.

Pure functions, no database. Used by the webhook receiver to drive the
copy-trade bot. (Previously this logic lived inside the pump.fun indexer,
which has been removed; the bot only needs buy/sell signals, not a full
token index.)
"""
from typing import Any, Dict, List, Set

from app.services.helius import HeliusClient

IGNORED_MINTS: Set[str] = {
    "So11111111111111111111111111111111111111112",   # wSOL
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
}


def extract_buys(tx: Dict[str, Any]) -> List[Dict[str, Any]]:
    """All (mint, wallet, sol_spent, token_amount) purchases inside one tx."""
    buys: List[Dict[str, Any]] = []
    seen: Set[tuple] = set()

    for transfer in tx.get("tokenTransfers") or []:
        mint = transfer.get("mint")
        buyer = transfer.get("toUserAccount")
        if not mint or not buyer or mint in IGNORED_MINTS or buyer == mint:
            continue
        if (mint, buyer) in seen:
            continue

        sol_spent = HeliusClient._sol_spent_by(buyer, tx)
        if sol_spent <= 0:
            continue

        try:
            token_amount = float(transfer.get("tokenAmount") or 0)
        except (TypeError, ValueError):
            token_amount = 0.0

        seen.add((mint, buyer))
        buys.append({
            "mint": mint,
            "wallet": buyer,
            "sol_spent": round(sol_spent, 6),
            "token_amount": token_amount,
        })

    return buys


def extract_sells(tx: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Wallets that SOLD a token in this tx (sent tokens, received SOL)."""
    sells: List[Dict[str, Any]] = []
    seen: Set[tuple] = set()
    balance_by_account = {
        acc.get("account"): acc.get("nativeBalanceChange") or 0
        for acc in tx.get("accountData") or []
    }
    for transfer in tx.get("tokenTransfers") or []:
        mint = transfer.get("mint")
        seller = transfer.get("fromUserAccount")
        if not mint or not seller or mint in IGNORED_MINTS:
            continue
        if (mint, seller) in seen:
            continue
        got_sol = balance_by_account.get(seller, 0) > 100_000
        swap = (tx.get("events") or {}).get("swap") or {}
        no = swap.get("nativeOutput") or {}
        if no.get("account") == seller:
            got_sol = True
        if not got_sol:
            continue
        seen.add((mint, seller))
        sells.append({"mint": mint, "wallet": seller})
    return sells


def extract_trades(payload: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Flatten a webhook delivery (list of txs) into buys + sells."""
    buys: List[Dict[str, Any]] = []
    sells: List[Dict[str, Any]] = []
    for tx in payload or []:
        buys.extend(extract_buys(tx))
        sells.extend(extract_sells(tx))
    return {"buys": buys, "sells": sells}
