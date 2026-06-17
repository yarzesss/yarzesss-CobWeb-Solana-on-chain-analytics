"""Market data tests — the on-chain price derivation is the critical path
for fresh bonding-curve tokens that DexScreener doesn't know yet."""
import asyncio
from unittest.mock import patch

from app.services.prices import (
    derive_price_sol_from_trades,
    _best_pair,
    get_prices_usd_batch,
)

MINT = "FreshMint11111111111111111111111111111111111"


def _pumpfun_buy(wallet, sol, tokens):
    return {
        "source": "PUMP_FUN", "events": {},
        "tokenTransfers": [{"mint": MINT, "toUserAccount": wallet, "tokenAmount": tokens}],
        "accountData": [{"account": wallet, "nativeBalanceChange": -int(sol * 1e9)}],
    }


def _swap_buy(wallet, sol, tokens):
    return {
        "events": {"swap": {
            "nativeInput": {"account": wallet, "amount": str(int(sol * 1e9))},
            "tokenOutputs": [{"mint": MINT, "userAccount": wallet,
                              "rawTokenAmount": {"tokenAmount": str(int(tokens)), "decimals": 0}}],
        }},
    }


def test_derived_price_volume_weighted():
    txs = [
        _pumpfun_buy("a", 1.0, 1_000_000),   # 1e-6 SOL/token
        _pumpfun_buy("b", 2.0, 2_000_000),   # 1e-6
        _swap_buy("c", 3.0, 3_000_000),      # 1e-6
    ]
    price = derive_price_sol_from_trades(txs, MINT)
    assert price is not None
    assert abs(price - 1e-6) < 1e-12


def test_derived_price_trims_outliers():
    txs = [
        _pumpfun_buy("a", 1.0, 1_000_000),
        _pumpfun_buy("b", 1.0, 1_000_000),
        _pumpfun_buy("c", 1.0, 1_000_000),
        _pumpfun_buy("mev", 100.0, 1_000),   # 0.1 SOL/token — 100,000x outlier
    ]
    price = derive_price_sol_from_trades(txs, MINT)
    assert price is not None
    assert abs(price - 1e-6) < 1e-12   # outlier excluded from the weighting


def test_derived_price_needs_min_trades():
    assert derive_price_sol_from_trades([_pumpfun_buy("a", 1.0, 1000)], MINT) is None
    assert derive_price_sol_from_trades([], MINT) is None


def test_best_pair_picks_most_liquid_solana():
    pairs = [
        {"chainId": "solana", "liquidity": {"usd": 1000}, "dexId": "small"},
        {"chainId": "ethereum", "liquidity": {"usd": 999999}, "dexId": "eth"},
        {"chainId": "solana", "liquidity": {"usd": 50000}, "dexId": "raydium"},
    ]
    assert _best_pair(pairs)["dexId"] == "raydium"
    assert _best_pair([]) is None


def test_batch_prices_misses_stay_none():
    class FakeHelius:
        async def _get(self, url, params=None):
            return {"pairs": [{
                "chainId": "solana",
                "baseToken": {"address": "PricedMint"},
                "priceUsd": "0.5",
                "liquidity": {"usd": 10000},
            }]}

    with patch("app.services.prices.get_helius_client", lambda: FakeHelius()):
        prices = asyncio.run(get_prices_usd_batch(["PricedMint", "FreshUnlisted"]))
    assert prices["PricedMint"] == 0.5
    assert prices["FreshUnlisted"] is None   # honest miss, not zero
