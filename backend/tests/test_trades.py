"""Buy/sell extraction for the copy-trade bot (no DB)."""
from app.services.trades import extract_buys, extract_sells, extract_trades

MINT = "MintAddr1111111111111111111111111111111111"


def _buy_tx(wallet, mint, sol, tokens):
    # SOL spent is read from swap.nativeInput or nativeTransfers (Helius format)
    return {
        "events": {"swap": {"nativeInput": {"account": wallet, "amount": str(int(sol * 1e9))}}},
        "tokenTransfers": [
            {"mint": mint, "toUserAccount": wallet, "fromUserAccount": "pool", "tokenAmount": tokens}
        ],
        "accountData": [{"account": wallet, "nativeBalanceChange": -int(sol * 1e9)}],
    }


def _sell_tx(wallet, mint, tokens):
    return {
        "events": {},
        "tokenTransfers": [
            {"mint": mint, "fromUserAccount": wallet, "toUserAccount": "pool", "tokenAmount": tokens}
        ],
        "accountData": [{"account": wallet, "nativeBalanceChange": 2_000_000_000}],  # got SOL
    }


def test_extract_buy():
    buys = extract_buys(_buy_tx("BUYER", MINT, 2.0, 1000))
    assert len(buys) == 1
    assert buys[0]["wallet"] == "BUYER"
    assert buys[0]["mint"] == MINT
    assert abs(buys[0]["sol_spent"] - 2.0) < 1e-6


def test_extract_sell():
    sells = extract_sells(_sell_tx("SELLER", MINT, 1000))
    assert sells == [{"mint": MINT, "wallet": "SELLER"}]


def test_buy_not_counted_as_sell_and_vice_versa():
    buy = _buy_tx("W", MINT, 1.0, 10)
    assert extract_sells(buy) == []
    assert len(extract_buys(buy)) == 1

    sell = _sell_tx("W", MINT, 10)
    assert extract_buys(sell) == []   # no SOL spent → not a buy
    assert len(extract_sells(sell)) == 1


def test_extract_trades_flattens_payload():
    payload = [_buy_tx("B", MINT, 1.0, 5), _sell_tx("S", MINT, 5)]
    out = extract_trades(payload)
    assert len(out["buys"]) == 1 and len(out["sells"]) == 1
    assert out["buys"][0]["wallet"] == "B"
    assert out["sells"][0]["wallet"] == "S"


def test_ignored_mints_skipped():
    # wSOL transfers must not register as buys
    wsol = "So11111111111111111111111111111111111111112"
    tx = _buy_tx("W", wsol, 1.0, 100)
    assert extract_buys(tx) == []
