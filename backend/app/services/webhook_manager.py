"""Dynamic Helius webhook management.

The copy-trade bot must be told, in real time, which wallets to watch.
Helius delivers a webhook only for the addresses listed on that webhook.
So whenever any user's watchlist changes, we recompute the UNION of every
watched wallet across all users and push that list to our Helius webhook
via the Helius API.

Endpoint (Helius): PUT https://api.helius.xyz/v0/webhooks/{id}?api-key=KEY
Body must include the full webhook definition; accountAddresses is the
field we update. Helius replaces the list wholesale on each PUT.

Limits: a free-plan webhook accepts up to ~100 addresses. We cap the
union at MAX_WEBHOOK_ADDRESSES and log if we exceed it (oldest-followed
wallets drop off rather than silently corrupting the request).

This module is intentionally defensive: Helius being unreachable must
never break the user's watchlist write. We update the DB first, then
best-effort sync the webhook; failures are logged, and a periodic
reconciler (called on startup) can re-push the correct list.
"""
import logging
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.accounts import WatchedWallet

logger = logging.getLogger("cobweb.webhook_mgr")

HELIUS_WEBHOOK_API = "https://api.helius.xyz/v0/webhooks"
MAX_WEBHOOK_ADDRESSES = 100
# pump.fun program kept as a harmless anchor so the webhook is never empty
# (Helius rejects an empty address list). It produces traffic we simply
# ignore in the indexer-less setup, but guarantees a valid PUT body.
ANCHOR_ADDRESS = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"


def _configured() -> bool:
    return bool(settings.HELIUS_WEBHOOK_ID and settings.HELIUS_API_KEY)


async def get_all_watched_wallets(db: AsyncSession) -> List[str]:
    """Union of every wallet followed by any user, newest-first, capped."""
    rows = (
        await db.execute(
            select(WatchedWallet.wallet, func.max(WatchedWallet.id).label("rid"))
            .group_by(WatchedWallet.wallet)
            .order_by(func.max(WatchedWallet.id).desc())
        )
    ).all()
    wallets = [r.wallet for r in rows]
    if len(wallets) > MAX_WEBHOOK_ADDRESSES:
        logger.warning(
            "watched wallets (%d) exceed webhook cap (%d); keeping newest",
            len(wallets), MAX_WEBHOOK_ADDRESSES,
        )
        wallets = wallets[:MAX_WEBHOOK_ADDRESSES]
    return wallets


def _build_address_list(wallets: List[str]) -> List[str]:
    # Always include the anchor so the list is never empty.
    addrs = list(dict.fromkeys([*wallets, ANCHOR_ADDRESS]))
    return addrs[:MAX_WEBHOOK_ADDRESSES]


async def _get_webhook(client: httpx.AsyncClient) -> Optional[Dict[str, Any]]:
    url = f"{HELIUS_WEBHOOK_API}/{settings.HELIUS_WEBHOOK_ID}"
    resp = await client.get(url, params={"api-key": settings.HELIUS_API_KEY})
    if resp.status_code != 200:
        logger.warning("Helius GET webhook failed: %s %s", resp.status_code, resp.text[:200])
        return None
    return resp.json()


async def sync_webhook_addresses(db: AsyncSession) -> Dict[str, Any]:
    """Push the current union of watched wallets to the Helius webhook.

    Returns a small status dict. Never raises — failures are reported in
    the dict and logged, so callers (watchlist writes) stay unaffected.
    """
    if not _configured():
        return {"synced": False, "reason": "HELIUS_WEBHOOK_ID not configured"}

    wallets = await get_all_watched_wallets(db)
    addresses = _build_address_list(wallets)

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            current = await _get_webhook(client)
            if current is None:
                return {"synced": False, "reason": "could not fetch webhook"}

            # Preserve the webhook's existing config; only replace addresses.
            body = {
                "webhookURL": current.get("webhookURL"),
                "transactionTypes": current.get("transactionTypes", ["ANY"]),
                "accountAddresses": addresses,
                "webhookType": current.get("webhookType", "enhanced"),
            }
            auth = current.get("authHeader")
            if auth:
                body["authHeader"] = auth

            url = f"{HELIUS_WEBHOOK_API}/{settings.HELIUS_WEBHOOK_ID}"
            resp = await client.put(
                url, params={"api-key": settings.HELIUS_API_KEY}, json=body
            )
            if resp.status_code not in (200, 201):
                logger.warning("Helius PUT webhook failed: %s %s", resp.status_code, resp.text[:200])
                return {"synced": False, "reason": f"PUT {resp.status_code}"}

        logger.info("webhook synced: %d wallet(s) + anchor", len(wallets))
        return {"synced": True, "watched": len(wallets), "addresses": len(addresses)}
    except Exception as exc:  # network/parse — never propagate
        logger.warning("webhook sync error: %s", exc)
        return {"synced": False, "reason": str(exc)}
