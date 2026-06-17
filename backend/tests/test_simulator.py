"""Copy-trade simulator tests."""
import asyncio
import time
from unittest.mock import patch

import app.services.simulator as sim_mod

W = "Wallet111"
NOW = int(time.time())


def _buy(ts, mint, sol):
    return {
        "timestamp": ts, "type": "SWAP", "source": "PUMP_FUN", "events": {},
        "tokenTransfers": [{"mint": mint, "toUserAccount": W, "tokenAmount": 100}],
        "accountData": [{"account": W, "nativeBalanceChange": -int(sol * 1e9)}],
    }


def _sell(ts, mint, sol):
    return {
        "timestamp": ts, "type": "SWAP", "source": "PUMP_FUN", "events": {},
        "tokenTransfers": [{"mint": mint, "fromUserAccount": W, "tokenAmount": 100}],
        "accountData": [{"account": W, "nativeBalanceChange": int(sol * 1e9)}],
    }


def test_roi_window_and_old_trades_excluded():
    txs = [
        _buy(NOW - 40 * 86400, "OLD", 100.0),   # outside 30d window
        _buy(NOW - 5 * 86400, "AAA", 2.0),
        _sell(NOW - 4 * 86400, "AAA", 3.0),     # +1 SOL
        _buy(NOW - 3 * 86400, "BBB", 1.0),
        _sell(NOW - 2 * 86400, "BBB", 0.5),     # -0.5 SOL
    ]

    class FakeHelius:
        async def get_wallet_transactions(self, w, limit=500):
            return txs
        async def get_sol_price_usd(self):
            return 100.0

    async def no_get(k):
        return None

    async def no_set(k, v, ttl=None):
        pass

    with patch.object(sim_mod, "get_helius_client", lambda: FakeHelius()), \
         patch.object(sim_mod, "get_json", no_get), \
         patch.object(sim_mod, "set_json", no_set):
        r = asyncio.run(sim_mod.simulate_copy_trade(W, days=30))

    assert r["trades"] == 4
    assert r["tokens_traded"] == 2          # OLD excluded
    assert r["sol_invested"] == 3.0
    assert r["sol_returned"] == 3.5
    assert r["realized_sol_pnl"] == 0.5
    assert r["realized_usd_pnl"] == 50.0
    assert r["roi_pct"] == round(0.5 / 3.0 * 100, 2)
    assert r["closed_positions"] == 2 and r["win_positions"] == 1
    assert r["full_window_covered"] is True


def test_days_clamped():
    class FakeHelius:
        async def get_wallet_transactions(self, w, limit=500):
            return []
        async def get_sol_price_usd(self):
            return 100.0

    async def no_get(k):
        return None

    async def no_set(k, v, ttl=None):
        pass

    with patch.object(sim_mod, "get_helius_client", lambda: FakeHelius()), \
         patch.object(sim_mod, "get_json", no_get), \
         patch.object(sim_mod, "set_json", no_set):
        r = asyncio.run(sim_mod.simulate_copy_trade(W, days=500))
    assert r["days"] == 90
