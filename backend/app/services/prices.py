"""Current market data: price, market cap, liquidity, trading venue.

Resolution chain — ordered so FRESH tokens are covered, not just listed ones:

1. DexScreener (free, no key) — tokens with a real DEX pair
   (migrated pump.fun, Raydium/Orca/Meteora listings). Gives price,
   liquidity, FDV, volume.
2. On-chain trade derivation — for everything DexScreener doesn't know,
   which is exactly the brand-new bonding-curve launches this product
   lives on. We take the token's most recent transactions, extract real
   executed swaps (SOL in vs tokens out), and compute a volume-weighted
   price. price × supply × SOL/USD = market cap. No liquidity figure on
   a bonding curve — returned as null, honestly.
3. Nothing trades → all-null with source="none". Never fabricate.

Batch helper for unrealized PnL: DexScreener accepts up to 30 mints per
request; unpriced mints are reported as unpriced, not as zero.
"""
import statistics
from typing import Any, Dict, List, Optional, Tuple

from app.core.cache import get_json, set_json
from app.services.helius import get_helius_client

DEXSCREENER_TOKENS_URL = "https://api.dexscreener.com/latest/dex/tokens/"
MARKET_CACHE_TTL = 90  # prices move fast
MIN_TRADES_FOR_DERIVED_PRICE = 3


def _best_pair(pairs: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Most liquid Solana pair from a DexScreener response."""
    sol_pairs = [p for p in pairs or [] if p.get("chainId") == "solana"]
    if not sol_pairs:
        return None
    return max(sol_pairs, key=lambda p: (p.get("liquidity") or {}).get("usd") or 0)


def _extract_trade_prices(txs: List[Dict[str, Any]], mint: str) -> List[Tuple[float, float]]:
    """[(sol_per_token, sol_volume)] from real executed swaps in recent txs."""
    samples: List[Tuple[float, float]] = []

    for tx in txs or []:
        swap = (tx.get("events") or {}).get("swap") or {}

        # Swap-event path
        if swap:
            ni = swap.get("nativeInput") or {}
            no = swap.get("nativeOutput") or {}
            for out in swap.get("tokenOutputs") or []:
                if out.get("mint") != mint:
                    continue
                raw = out.get("rawTokenAmount") or {}
                try:
                    tokens = float(raw.get("tokenAmount") or 0) / (10 ** int(raw.get("decimals") or 0))
                    sol = int(ni.get("amount") or 0) / 1e9
                except (TypeError, ValueError):
                    continue
                if tokens > 0 and sol > 0:
                    samples.append((sol / tokens, sol))
            for inp in swap.get("tokenInputs") or []:
                if inp.get("mint") != mint:
                    continue
                raw = inp.get("rawTokenAmount") or {}
                try:
                    tokens = float(raw.get("tokenAmount") or 0) / (10 ** int(raw.get("decimals") or 0))
                    sol = int(no.get("amount") or 0) / 1e9
                except (TypeError, ValueError):
                    continue
                if tokens > 0 and sol > 0:
                    samples.append((sol / tokens, sol))
            continue

        # pump.fun fallback path: token transfer + counterparty SOL movement
        balance_by_account = {
            acc.get("account"): acc.get("nativeBalanceChange") or 0
            for acc in tx.get("accountData") or []
        }
        for transfer in tx.get("tokenTransfers") or []:
            if transfer.get("mint") != mint:
                continue
            try:
                tokens = float(transfer.get("tokenAmount") or 0)
            except (TypeError, ValueError):
                continue
            if tokens <= 0:
                continue
            recipient = transfer.get("toUserAccount")
            sender = transfer.get("fromUserAccount")
            recipient_change = balance_by_account.get(recipient, 0)
            sender_change = balance_by_account.get(sender, 0)
            if recipient and recipient_change < -100_000:          # buy
                samples.append((abs(recipient_change) / 1e9 / tokens, abs(recipient_change) / 1e9))
            elif sender and sender_change > 100_000:               # sell
                samples.append((sender_change / 1e9 / tokens, sender_change / 1e9))

    return samples


def derive_price_sol_from_trades(txs: List[Dict[str, Any]], mint: str) -> Optional[float]:
    """Volume-weighted recent price in SOL/token, outlier-trimmed. Pure & testable."""
    samples = _extract_trade_prices(txs, mint)
    if len(samples) < MIN_TRADES_FOR_DERIVED_PRICE:
        return None

    # Trim outliers (MEV / dust): keep samples within 4x of the median price
    median_price = statistics.median(p for p, _ in samples)
    if median_price <= 0:
        return None
    kept = [(p, v) for p, v in samples if median_price / 4 <= p <= median_price * 4]
    if not kept:
        return None

    total_volume = sum(v for _, v in kept)
    if total_volume <= 0:
        return None
    return sum(p * v for p, v in kept) / total_volume


async def get_token_market_data(ca: str) -> Dict[str, Any]:
    cache_key = f"token:{ca}:market"
    cached = await get_json(cache_key)
    if cached is not None:
        return cached

    helius = get_helius_client()
    result: Dict[str, Any] = {
        "price_usd": None,
        "market_cap_usd": None,
        "liquidity_usd": None,
        "volume_24h_usd": None,
        "dex": None,
        "venue": "unknown",   # "amm" | "bonding_curve" | "unknown"
        "source": "none",     # "dexscreener" | "onchain_trades" | "none"
    }

    # ── 1. DexScreener ───────────────────────────────────────────────────────
    data = await helius._get(f"{DEXSCREENER_TOKENS_URL}{ca}")
    if isinstance(data, dict) and not data.get("error"):
        pair = _best_pair(data.get("pairs") or [])
        if pair:
            try:
                price = float(pair.get("priceUsd") or 0)
            except (TypeError, ValueError):
                price = 0.0
            if price > 0:
                result.update({
                    "price_usd": price,
                    "market_cap_usd": pair.get("fdv") or pair.get("marketCap"),
                    "liquidity_usd": (pair.get("liquidity") or {}).get("usd"),
                    "volume_24h_usd": (pair.get("volume") or {}).get("h24"),
                    "dex": pair.get("dexId"),
                    "venue": "amm",
                    "source": "dexscreener",
                })
                await set_json(cache_key, result, ttl=MARKET_CACHE_TTL)
                return result

    # ── 2. Derive from recent on-chain trades (fresh launches live here) ────
    try:
        txs = await helius._fetch_all_transactions(ca, limit=100)
    except Exception:
        txs = []

    price_sol = derive_price_sol_from_trades(txs, ca)
    if price_sol is not None:
        supply = await helius.get_token_supply(ca)
        sol_usd = await helius.get_sol_price_usd()
        price_usd = price_sol * sol_usd
        is_pumpfun = any((t.get("source") == "PUMP_FUN") for t in txs[:25])
        result.update({
            "price_usd": price_usd,
            "market_cap_usd": round(price_usd * supply, 2) if supply > 0 else None,
            "liquidity_usd": None,  # no pool on a bonding curve — honest null
            "volume_24h_usd": None,
            "dex": "pump.fun" if is_pumpfun else None,
            "venue": "bonding_curve" if is_pumpfun else "unknown",
            "source": "onchain_trades",
        })

    await set_json(cache_key, result, ttl=MARKET_CACHE_TTL)
    return result


async def get_prices_usd_batch(mints: List[str]) -> Dict[str, Optional[float]]:
    """USD price per mint for unrealized PnL. DexScreener batches of 30;
    misses stay None — the caller reports them as unpriced, never as zero."""
    unique = list(dict.fromkeys(m for m in mints if m))
    prices: Dict[str, Optional[float]] = {m: None for m in unique}
    if not unique:
        return prices

    helius = get_helius_client()
    for i in range(0, len(unique), 30):
        chunk = unique[i:i + 30]
        data = await helius._get(DEXSCREENER_TOKENS_URL + ",".join(chunk))
        if not isinstance(data, dict) or data.get("error"):
            continue
        by_mint: Dict[str, List[Dict[str, Any]]] = {}
        for pair in data.get("pairs") or []:
            base = (pair.get("baseToken") or {}).get("address")
            if base in prices:
                by_mint.setdefault(base, []).append(pair)
        for mint, pairs in by_mint.items():
            pair = _best_pair(pairs)
            if pair:
                try:
                    p = float(pair.get("priceUsd") or 0)
                    if p > 0:
                        prices[mint] = p
                except (TypeError, ValueError):
                    pass
    return prices
