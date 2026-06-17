"""Token analysis endpoints."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from app.services.helius import get_helius_client, HeliusUpstreamError
from app.services.cabal import analyze_cabal
from app.services.classifier import compute_dev_risk, classify_dev_risk
from app.core.validation import validate_ca
from app.core.ratelimit import heavy_limiter
from app.core.jobs import singleflight

# At most this many deep analyses computed concurrently per process —
# protects the Helius quota under a burst of different tokens.
_DEEP_SEMAPHORE = asyncio.Semaphore(3)
DEEP_RESULT_TTL = 120
from app.services.lifecycle import compute_lifecycle
from app.services.prices import get_token_market_data
from app.database import AsyncSessionLocal


async def _early_buyers_db_first(ca: str, helius) -> tuple:
    """(buyers, source) — reconstructed from Helius transaction history.
    (Live pump.fun indexing was removed; analysis is fully on-demand now.)"""
    return await helius.get_early_buyers(ca), "history"


router = APIRouter(
    prefix="/token",
    tags=["Token"],
    dependencies=[Depends(heavy_limiter)],
)

# A buyer with smart_money_score >= this is shown in the Smart Money tab
SMART_MONEY_THRESHOLD = 55


async def _get_dev_risk(dev_wallet: str | None) -> Dict[str, Any]:
    if not dev_wallet:
        return {"score": 0, "level": "LOW", "dev_wallet": None}

    helius = get_helius_client()
    txs = await helius.get_wallet_transactions(dev_wallet, limit=200)
    seen_tokens: set[str] = set()
    quick_sells = 0
    sorted_txs = sorted(txs, key=lambda t: t.get("timestamp") or 0)

    for tx in sorted_txs:
        for transfer in tx.get("tokenTransfers") or []:
            mint = transfer.get("mint")
            if mint:
                seen_tokens.add(mint)

    dev_prev_tokens = len(seen_tokens)
    for tx in sorted_txs[:20]:
        for transfer in tx.get("tokenTransfers") or []:
            if transfer.get("fromUserAccount") == dev_wallet:
                quick_sells += 1

    dev_sells_within_hours = 1.0 if quick_sells > 3 else None
    score = compute_dev_risk(
        dev_rug_count=0,
        dev_sells_within_hours=dev_sells_within_hours,
        dev_prev_tokens=dev_prev_tokens,
        connected_to_known_scammers=False,
    )
    return {
        "score": score,
        "level": classify_dev_risk(score),
        "dev_wallet": dev_wallet,
        "dev_prev_tokens": dev_prev_tokens,
        "quick_sell_signal": quick_sells > 3,
    }


def _enrich_buyers(
    early_buyers: List[Dict[str, Any]],
    cabal: Dict[str, Any],
    token_supply: float = 0.0,
    sol_price_usd: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    Enrich early buyers with computed data:
    - entry_price_sol / entry_market_cap_usd: derived from sol_spent / tokens bought
    - amount_usd: position size in USD at entry
    - bot_score: based on how many blocks after launch they bought
    - archetype + category: bot / cluster / smart_money / regular
    - cluster membership
    """
    if not early_buyers:
        return []

    # Find launch slot = the very first buyer's slot
    valid_slots = [b.get("slot") for b in early_buyers if b.get("slot")]
    launch_slot = min(valid_slots) if valid_slots else 0

    # Build cluster lookup
    cluster_wallet_map: Dict[str, Dict[str, Any]] = {}
    for i, cluster in enumerate(cabal.get("clusters") or []):
        for w in cluster.get("wallets") or []:
            cluster_wallet_map[w] = {
                "cluster_id": i,
                "suspicion_score": cluster.get("suspicion_score"),
                "cluster_type": cluster.get("cluster_type", "unknown"),
            }

    # Median position size — conviction reference point
    sol_sizes = sorted(b.get("sol_spent") or 0 for b in early_buyers)
    median_sol = sol_sizes[len(sol_sizes) // 2] if sol_sizes else 0.0

    enriched = []
    for buyer in early_buyers:
        wallet = buyer.get("wallet")
        slot = buyer.get("slot") or 0
        blocks_after = max(0, slot - launch_slot) if launch_slot else 0
        in_cluster = wallet in cluster_wallet_map
        cluster_info = cluster_wallet_map.get(wallet, {})
        suspicious_cluster = in_cluster and (cluster_info.get("suspicion_score") or 0) >= 70

        sol_spent = float(buyer.get("sol_spent") or 0)
        token_amount = float(buyer.get("amount") or 0)

        # ── Entry price & market cap ─────────────────────────────────────────
        entry_price_sol = sol_spent / token_amount if token_amount > 0 else None
        entry_market_cap_usd = None
        if entry_price_sol is not None and token_supply > 0 and sol_price_usd > 0:
            entry_market_cap_usd = round(entry_price_sol * token_supply * sol_price_usd, 2)
        amount_usd = round(sol_spent * sol_price_usd, 2) if sol_price_usd > 0 else None

        # ── Bot score: the earlier relative to launch, the more bot-like ────
        if blocks_after < 3:
            bot_score = 85
        elif blocks_after < 10:
            bot_score = 65
        elif blocks_after < 30:
            bot_score = 35
        else:
            bot_score = 12

        # ── Smart money score: conviction + organic timing + independence ───
        if bot_score >= 60:
            smart_money_score = 0
        elif suspicious_cluster:
            smart_money_score = 15  # coordinated, not independently "smart"
        else:
            smart_money_score = 20
            if blocks_after >= 30:
                smart_money_score += 15  # organic timing, not sniping
            if median_sol > 0 and sol_spent >= median_sol * 2:
                smart_money_score += 30  # strong conviction vs peers
            elif median_sol > 0 and sol_spent >= median_sol:
                smart_money_score += 10
            if not in_cluster:
                smart_money_score += 10
            smart_money_score = min(smart_money_score, 100)

        # ── Archetype ────────────────────────────────────────────────────────
        if bot_score >= 60:
            archetype = "bot"
        elif blocks_after < 5:
            archetype = "sniper"
        elif suspicious_cluster:
            archetype = "insider"
        elif in_cluster:
            archetype = "swing_trader"
        elif smart_money_score >= SMART_MONEY_THRESHOLD:
            archetype = "accumulator"
        else:
            archetype = "unknown"

        # ── Category: ONE bucket per wallet — tabs never overlap ────────────
        if bot_score >= 60:
            category = "bot"
        elif suspicious_cluster:
            category = "cluster"
        elif smart_money_score >= SMART_MONEY_THRESHOLD:
            category = "smart_money"
        else:
            category = "regular"

        enriched.append({
            **buyer,
            "amount_tokens": token_amount,
            "amount_usd": amount_usd,
            "sol_spent": sol_spent,
            "entry_price_sol": entry_price_sol,
            "entry_market_cap_usd": entry_market_cap_usd,
            "market_cap_usd": entry_market_cap_usd,  # frontend compat alias
            "blocks_after_launch": blocks_after,
            "bot_score": bot_score,
            "archetype": archetype,
            "category": category,
            "smart_money_score": smart_money_score,
            "cluster_id": cluster_info.get("cluster_id"),
            "suspicion_score": cluster_info.get("suspicion_score"),
            "cluster_type": cluster_info.get("cluster_type"),
            "in_cluster": in_cluster,
        })

    # Sort: cluster members first, then by blocks_after_launch ascending
    enriched.sort(key=lambda b: (
        0 if b.get("in_cluster") else 1,
        b.get("blocks_after_launch", 9999),
    ))

    return enriched


@router.get("/{ca}", summary="Full token analysis")
async def token_analysis(
    ca: str = Depends(validate_ca),
    deep: bool = True,
) -> Dict[str, Any]:
    """
    Token analysis.

    `deep=false` → fast pass: metadata + early buyers + entry mcap,
    WITHOUT the cabal scan (which fans out into ~50 wallet histories and
    can take 30–60s cold). The frontend renders this immediately and
    fetches the deep version in the background.

    Deep computations are deduplicated across concurrent requests
    (singleflight): N users opening the same token trigger ONE scan.
    """
    if deep:
        async def _compute() -> Dict[str, Any]:
            async with _DEEP_SEMAPHORE:
                return await _token_analysis_impl(ca, deep=True)

        result, _fresh = await singleflight(
            f"token-deep:{ca}", _compute, result_ttl=DEEP_RESULT_TTL
        )
        if result is not None:
            return result
        # A peer is still computing — serve the fast pass so the user
        # sees data immediately; the client polls until analysis_complete.
        return await _token_analysis_impl(ca, deep=False)

    return await _token_analysis_impl(ca, deep=False)


async def _token_analysis_impl(ca: str, deep: bool) -> Dict[str, Any]:
    helius = get_helius_client()

    try:
        meta, (early_buyers, buyers_source), supply, sol_price = await asyncio.gather(
            helius.get_token_metadata(ca),
            _early_buyers_db_first(ca, helius),
            helius.get_token_supply(ca),
            helius.get_sol_price_usd(),
        )
    except HeliusUpstreamError as exc:
        raise HTTPException(status_code=503, detail=f"Data provider unavailable: {exc}")

    dev_wallet = None
    if isinstance(meta, dict):
        on_chain = meta.get("onChainMetadata") or {}
        dev_wallet = (
            on_chain.get("updateAuthority")
            or meta.get("owner")
            or meta.get("developer")
        )

    if deep:
        try:
            cabal, dev_risk, lifecycle, market, holders = await asyncio.gather(
                analyze_cabal(ca, early_buyers),
                _get_dev_risk(dev_wallet),
                compute_lifecycle(ca),
                get_token_market_data(ca),
                helius.get_top_holders(ca),
            )
        except HeliusUpstreamError as exc:
            raise HTTPException(status_code=503, detail=f"Data provider unavailable: {exc}")
    else:
        cabal = {"clusters": [], "independent_wallets": []}
        dev_risk = {"score": 0, "level": "LOW", "dev_wallet": dev_wallet, "pending": True}
        lifecycle = {"stage": "unknown", "pending": True}
        market = {"pending": True}
        holders = {"top10_pct": None, "top_holders": []}

    enriched = _enrich_buyers(early_buyers, cabal, token_supply=supply, sol_price_usd=sol_price)

    counts = {
        "smart_money": sum(1 for b in enriched if b["category"] == "smart_money"),
        "bots": sum(1 for b in enriched if b["category"] == "bot"),
        "cluster_members": sum(1 for b in enriched if b["category"] == "cluster"),
        "regular": sum(1 for b in enriched if b["category"] == "regular"),
    }

    on_chain_meta = (meta.get("onChainMetadata") or {}) if isinstance(meta, dict) else {}
    # Helius token-metadata nests name/symbol under metadata.data on some plans
    nested = (on_chain_meta.get("metadata") or {}).get("data") or {}

    return {
        "ca": ca,
        "name": on_chain_meta.get("name") or nested.get("name"),
        "symbol": on_chain_meta.get("symbol") or nested.get("symbol"),
        "token_supply": supply,
        "sol_price_usd": round(sol_price, 2),
        "early_buyers_count": len(early_buyers),
        "buyer_counts": counts,
        "early_buyers": enriched[:50],
        "cabal": cabal,
        "dev_risk": dev_risk,
        "lifecycle": lifecycle,
        "market": market,
        "holders": holders,
        "buyers_source": buyers_source,
        "analysis_complete": deep,
    }


@router.get("/{ca}/early-buyers", summary="Paginated early buyers list")
async def token_early_buyers(
    ca: str = Depends(validate_ca), limit: int = 100, offset: int = 0
) -> Dict[str, Any]:
    helius = get_helius_client()
    try:
        (early_buyers, _src), supply, sol_price = await asyncio.gather(
            _early_buyers_db_first(ca, helius),
            helius.get_token_supply(ca),
            helius.get_sol_price_usd(),
        )
        cabal = await analyze_cabal(ca, early_buyers)
    except HeliusUpstreamError as exc:
        raise HTTPException(status_code=503, detail=f"Data provider unavailable: {exc}")
    enriched = _enrich_buyers(early_buyers, cabal, token_supply=supply, sol_price_usd=sol_price)
    page = enriched[offset: offset + limit]
    return {
        "ca": ca,
        "total": len(early_buyers),
        "limit": limit,
        "offset": offset,
        "buyers": page,
    }


@router.get("/{ca}/cabal", summary="Cabal cluster analysis")
async def token_cabal(ca: str = Depends(validate_ca)) -> Dict[str, Any]:
    helius = get_helius_client()
    try:
        early_buyers = await helius.get_early_buyers(ca)
        return await analyze_cabal(ca, early_buyers)
    except HeliusUpstreamError as exc:
        raise HTTPException(status_code=503, detail=f"Data provider unavailable: {exc}")


@router.get("/{ca}/dev-risk", summary="Dev wallet risk score")
async def token_dev_risk(ca: str = Depends(validate_ca)) -> Dict[str, Any]:
    helius = get_helius_client()
    try:
        meta = await helius.get_token_metadata(ca)
        dev_wallet = None
        if isinstance(meta, dict):
            on_chain = meta.get("onChainMetadata") or {}
            dev_wallet = on_chain.get("updateAuthority") or meta.get("owner")
        return await _get_dev_risk(dev_wallet)
    except HeliusUpstreamError as exc:
        raise HTTPException(status_code=503, detail=f"Data provider unavailable: {exc}")