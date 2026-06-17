"""Tests for early-buyer enrichment — categories must never overlap."""
from app.routers.tokens import _enrich_buyers, SMART_MONEY_THRESHOLD

BUYERS = [
    {"wallet": "sniperbot", "slot": 1000, "timestamp": 10, "amount": 10_000_000, "sol_spent": 0.5},
    {"wallet": "clusterguy", "slot": 1040, "timestamp": 50, "amount": 5_000_000, "sol_spent": 0.4},
    {"wallet": "whale", "slot": 1100, "timestamp": 99, "amount": 20_000_000, "sol_spent": 5.0},
    {"wallet": "smalljoe", "slot": 1120, "timestamp": 120, "amount": 1_000_000, "sol_spent": 0.1},
]
CABAL = {"clusters": [{"wallets": ["clusterguy"], "suspicion_score": 80, "cluster_type": "funding"}]}


def _enrich():
    return {b["wallet"]: b for b in _enrich_buyers(BUYERS, CABAL, 1_000_000_000, 200.0)}


def test_categories_are_distinct():
    e = _enrich()
    assert e["sniperbot"]["category"] == "bot"
    assert e["clusterguy"]["category"] == "cluster"
    assert e["whale"]["category"] == "smart_money"
    assert e["smalljoe"]["category"] == "regular"


def test_one_category_per_wallet():
    enriched = _enrich_buyers(BUYERS, CABAL, 1_000_000_000, 200.0)
    for b in enriched:
        assert b["category"] in ("bot", "cluster", "smart_money", "regular")
    # Smart Money tab must be a strict subset, never identical to All
    smart = [b for b in enriched if b["category"] == "smart_money"]
    assert 0 < len(smart) < len(enriched)


def test_entry_mcap_math():
    e = _enrich()
    # price = 5 SOL / 20M tokens; mcap = price * 1B supply * $200 = $50,000
    assert e["whale"]["entry_market_cap_usd"] == 50_000.0
    assert e["whale"]["amount_usd"] == 1_000.0  # 5 SOL * $200


def test_missing_fields_do_not_crash():
    edge = _enrich_buyers([{"wallet": "x", "slot": None, "timestamp": None}], {"clusters": []}, 0, 0)
    assert edge[0]["entry_market_cap_usd"] is None
    assert edge[0]["amount_usd"] is None
    assert _enrich_buyers([], {"clusters": []}, 1, 1) == []


def test_smart_money_requires_conviction():
    # Everyone tiny and late → nobody should be "smart" just for existing
    buyers = [
        {"wallet": f"w{i}", "slot": 2000 + i * 50, "timestamp": i * 100, "amount": 1000, "sol_spent": 0.1}
        for i in range(5)
    ]
    enriched = _enrich_buyers(buyers, {"clusters": []}, 1_000_000_000, 200.0)
    smart = [b for b in enriched if b["category"] == "smart_money"]
    assert len(smart) < len(enriched)
