"""CEX whitelist must prevent false-positive funding clusters."""
from app.services.known_wallets import cex_label, is_known_infrastructure

BINANCE = "5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9"


def test_label_lookup():
    assert cex_label(BINANCE) == "Binance"
    assert cex_label("RandomWallet111") is None
    assert cex_label(None) is None
    assert is_known_infrastructure(BINANCE)
