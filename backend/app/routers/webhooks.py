"""Helius webhook receiver — drives the copy-trade bot.

The webhook's watched-address list is managed dynamically: whenever a user
follows/unfollows a wallet, the backend pushes the new union of watched
wallets to this webhook via the Helius API (see services/webhook_manager).

So every delivery here is (mostly) a trade by a wallet someone is copying.
We extract buys/sells and let the bot open/close virtual positions.

Setup recap (Helius dashboard):
- Type: Enhanced · Transaction types: ANY · Network: mainnet
- URL: https://<your-domain>/webhooks/helius
- The address list is maintained automatically; you only seed one anchor.
"""
import asyncio
from typing import Any, Dict, List

from fastapi import APIRouter, Header, HTTPException

from app.config import settings
from app.database import AsyncSessionLocal
from app.services.trades import extract_trades
from app.services.copytrade import on_watched_buy, on_watched_sell

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def _normalize_secret(value: str | None) -> str:
    """Tolerant secret comparison — accepts the secret regardless of how the
    provider formats the header ('Authorization: X', 'Bearer X', '"X"', ' X ')."""
    if not value:
        return ""
    v = value.strip().strip('"').strip("'").strip()
    low = v.lower()
    for prefix in ("authorization:", "bearer ", "basic "):
        if low.startswith(prefix):
            v = v[len(prefix):].strip()
            low = v.lower()
    return v


def _secret_matches(incoming: str | None, expected: str) -> bool:
    return _normalize_secret(incoming) == _normalize_secret(expected)


async def _run_copytrade(buys: List[Dict[str, Any]], sells: List[Dict[str, Any]]) -> None:
    """Drive the paper-trading bot from observed buys/sells. Own DB session."""
    try:
        async with AsyncSessionLocal() as db:
            for buy in buys:
                await on_watched_buy(db, buy["wallet"], buy["mint"])
            for sell in sells:
                await on_watched_sell(db, sell["wallet"], sell["mint"])
            await db.commit()
    except Exception:
        pass  # bot errors must never break webhook ingestion


@router.post("/helius", summary="Ingest Helius enhanced-webhook deliveries")
async def helius_webhook(
    payload: List[Dict[str, Any]],
    authorization: str | None = Header(default=None),
) -> Dict[str, Any]:
    if settings.HELIUS_WEBHOOK_SECRET:
        if not _secret_matches(authorization, settings.HELIUS_WEBHOOK_SECRET):
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

    trades = extract_trades(payload)
    buys, sells = trades["buys"], trades["sells"]

    # Fire-and-forget so the webhook ACK isn't delayed by bot work
    if buys or sells:
        asyncio.create_task(_run_copytrade(buys, sells))

    return {"ok": True, "buys": len(buys), "sells": len(sells)}
