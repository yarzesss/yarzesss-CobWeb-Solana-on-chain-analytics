"""Lifecycle stage heuristic tests."""
from app.services.lifecycle import compute_lifecycle_from_txs

MINT = "M1nt"


def _swap_tx(side, wallet, n):
    if side == "buy":
        return {
            "events": {"swap": {
                "nativeInput": {"account": wallet, "amount": "1000000000"},
                "tokenOutputs": [{"mint": MINT, "userAccount": wallet,
                                  "rawTokenAmount": {"tokenAmount": "1", "decimals": 0}}],
            }},
            "signature": f"b{n}",
        }
    return {
        "events": {"swap": {
            "nativeOutput": {"account": wallet, "amount": "1000000000"},
            "tokenInputs": [{"mint": MINT, "userAccount": wallet,
                             "rawTokenAmount": {"tokenAmount": "1", "decimals": 0}}],
        }},
        "signature": f"s{n}",
    }


def test_markup_when_buys_dominate():
    txs = [_swap_tx("buy", f"w{i}", i) for i in range(8)] + [_swap_tx("sell", "z", 1)]
    assert compute_lifecycle_from_txs(txs, MINT)["stage"] == "markup"


def test_dump_when_sells_dominate():
    txs = [_swap_tx("sell", f"w{i}", i) for i in range(8)] + [_swap_tx("buy", "z", 1)]
    assert compute_lifecycle_from_txs(txs, MINT)["stage"] == "dump"


def test_accumulation_balanced_more_buyers():
    txs = ([_swap_tx("buy", f"b{i}", i) for i in range(5)]
           + [_swap_tx("sell", "whale", i) for i in range(5)])  # 1 seller, 5 buyers
    r = compute_lifecycle_from_txs(txs, MINT)
    assert r["stage"] == "accumulation"
    assert r["unique_buyers"] == 5 and r["unique_sellers"] == 1


def test_distribution_balanced_more_sellers():
    txs = ([_swap_tx("buy", "whale", i) for i in range(5)]
           + [_swap_tx("sell", f"s{i}", i) for i in range(5)])
    assert compute_lifecycle_from_txs(txs, MINT)["stage"] == "distribution"


def test_unknown_on_thin_signal():
    txs = [_swap_tx("buy", "a", 1), _swap_tx("sell", "b", 2)]
    assert compute_lifecycle_from_txs(txs, MINT)["stage"] == "unknown"


def test_pumpfun_fallback_classification():
    tx = {
        "events": {},
        "tokenTransfers": [{"mint": MINT, "toUserAccount": "W", "tokenAmount": 10}],
        "accountData": [{"account": "W", "nativeBalanceChange": -2_000_000_000}],
    }
    r = compute_lifecycle_from_txs([tx] * 6, MINT)
    assert r["buy_count"] == 6 and r["stage"] == "markup"
