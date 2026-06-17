"""Directory of known exchange / bridge / infrastructure wallets on Solana.

Why this exists: cabal detection groups wallets by "common funder".
But two wallets that both withdrew from Binance share a funder without
sharing an owner — flagging them as a coordinated cluster is a false
positive that erodes trust in the whole graph. Funders in this list
produce a "funded via CEX" note instead of a cluster.

Addresses are well-known public hot wallets (visible on any explorer,
labelled by Solscan/SolanaFM). Extend freely.
"""
from typing import Optional, Set

KNOWN_CEX_WALLETS: dict[str, str] = {
    # Binance
    "5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9": "Binance",
    "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM": "Binance",
    "2ojv9BAiHUrvsm9gxDe7fJSzbNZSJcxZvf8dqmWGHG8S": "Binance",
    "AC5RDfQFmDS1deWZos921JfqscXdByf8BKHs5ACWjtW2": "Binance",
    # Bybit
    "AC9JuhpzWS5dpnHsBGzF8ZmkBLnobcFw7pf9JM8GuQVB": "Bybit",
    "42brAgAVNzMBP7aaktPvAmBSPEkehnFQejiZc53EpJFd": "Bybit",
    # OKX
    "5VCwKtCXgCJ6kit5FybXjvriW3xELsFDhYrPSqtJNmcD": "OKX",
    "9un5wqE3q4oCjyrDkwsdD48KteCJitQX5978Vh7KKxHo": "OKX",
    # Coinbase
    "H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61LGFJ8N4dK3WjS": "Coinbase",
    "2AQdpHJ2JpcEgPiATUXjQxA8QmafFegfQwSLWSprPicm": "Coinbase",
    "GJRs4FwHtemZ5ZE9x3FNvJ8TMwitKTh21yxdRPqn7npE": "Coinbase",
    # Kraken
    "FWznbcNXWQuHTawe9RxvQ2LdCENssh12dsznf4RiouN5": "Kraken",
    # KuCoin
    "BmFdpraQhkiDQE6SnfG5omcA1VwzqfXrwtNYBwWTymy6": "KuCoin",
    "57vSaRTqN9iXaemgh4AoDsZ63mcaoshfMK8NP3Z5QNbs": "KuCoin",
    # Gate.io
    "u6PJ8DtQuPFnfmwHbGFULQ4u4EgjDiyYKjVEsynXq2w": "Gate.io",
    # MEXC
    "ASTyfSima4LLAdDgoFGkgqoKowG1LZFDr9fAQrg7iaJZ": "MEXC",
    # Crypto.com
    "AobVSwdW9BbpMdJvTqeCN4hPAmh4rHm7vwLnQ5ATSyrS": "Crypto.com",
    # Wormhole bridge
    "3u8hJUVTA4jH1wYAyUur7FFZVQ8H635K3tSHHF4ssjQ5": "Wormhole",
}


def cex_label(address: Optional[str]) -> Optional[str]:
    """Exchange name if the address is a known CEX/bridge hot wallet."""
    if not address:
        return None
    return KNOWN_CEX_WALLETS.get(address)


def is_known_infrastructure(address: Optional[str]) -> bool:
    return cex_label(address) is not None


# Convenience set for fast membership checks
KNOWN_INFRA_SET: Set[str] = set(KNOWN_CEX_WALLETS)
