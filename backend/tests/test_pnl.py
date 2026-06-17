"""Tests for the PnL parsers — including the pump.fun fallback path."""
import asyncio
from unittest.mock import patch

import app.services.pnl as pnl_mod
from app.services.pnl import _parse_raw_transfers, _parse_swap_event

W = "WalletAAAA"

PUMPFUN_BUY = {
    "type": "SWAP", "source": "PUMP_FUN", "timestamp": 100, "events": {},
    "tokenTransfers": [
        {"mint": "MintX", "toUserAccount": W, "fromUserAccount": "pool", "tokenAmount": 1_000_000}
    ],
    "accountData": [{"account": W, "nativeBalanceChange": -2_000_000_000}],
}

PUMPFUN_SELL = {
    "type": "SWAP", "source": "PUMP_FUN", "timestamp": 200, "events": {},
    "tokenTransfers": [
        {"mint": "MintX", "fromUserAccount": W, "toUserAccount": "pool", "tokenAmount": 1_000_000}
    ],
    "nativeTransfers": [
        {"fromUserAccount": "pool", "toUserAccount": W, "amount": 3_000_000_000}
    ],
}

JUPITER_BUY = {
    "timestamp": 300, "type": "SWAP", "source": "JUPITER",
    "events": {"swap": {
        "nativeInput": {"account": W, "amount": "1500000000"},
        "tokenOutputs": [{
            "userAccount": W, "mint": "MintY",
            "rawTokenAmount": {"tokenAmount": "5000000", "decimals": 6},
        }],
    }},
}


def test_fallback_parser_buy():
    assert _parse_raw_transfers(PUMPFUN_BUY, W) == ("buy", "MintX", 1_000_000.0, 2.0)


def test_fallback_parser_sell():
    assert _parse_raw_transfers(PUMPFUN_SELL, W) == ("sell", "MintX", 1_000_000.0, 3.0)


def test_swap_event_parser():
    assert _parse_swap_event(JUPITER_BUY, W) == ("buy", "MintY", 5.0, 1.5)


def test_fallback_ignores_plain_transfer():
    # Tokens received but no SOL movement → airdrop, not a buy
    tx = {
        "type": "TRANSFER", "events": {},
        "tokenTransfers": [{"mint": "M", "toUserAccount": W, "tokenAmount": 50}],
        "nativeTransfers": [],
    }
    assert _parse_raw_transfers(tx, W) is None


def test_full_pipeline_usd_conversion():
    class FakeHelius:
        async def get_wallet_transactions(self, w, limit=500):
            return [PUMPFUN_BUY, PUMPFUN_SELL, JUPITER_BUY]
        async def get_sol_price_usd(self):
            return 200.0

    async def no_get(k):
        return None

    async def no_set(k, v, ttl=None):
        pass

    with patch.object(pnl_mod, "get_helius_client", lambda: FakeHelius()), \
         patch.object(pnl_mod, "get_json", no_get), \
         patch.object(pnl_mod, "set_json", no_set):
        result = asyncio.run(pnl_mod.calculate_wallet_pnl(W))

    s = result["summary"]
    assert s["total_sol_pnl"] == -0.5          # MintX: +1.0, MintY: -1.5
    assert s["total_realized_usd"] == -100.0   # -0.5 SOL * $200
    assert s["total_trades"] == 3
    assert s["completed_trades"] == 1
    assert s["winrate"] == 1.0
    assert s["avg_position_size_usd"] == 350.0  # (2.0 + 1.5)/2 SOL * $200
    assert len(result["by_token"]) == 2
    assert result["wallet_address"] == W
