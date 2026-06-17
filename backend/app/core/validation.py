"""Request input validation helpers.

Every public endpoint takes a Solana address straight from the URL.
Without validation, garbage input ("/token/abrakadabra") still triggers
a full chain of Helius API calls — wasted quota and confusing errors.
Validate first, fail fast with 422.
"""
from __future__ import annotations

import base58
from fastapi import HTTPException, Path


def _is_valid_solana_address(value: str) -> bool:
    """A Solana address is a base58-encoded 32-byte ed25519 public key."""
    if not value or not (32 <= len(value) <= 44):
        return False
    try:
        raw = base58.b58decode(value)
    except Exception:
        return False
    return len(raw) == 32


def validate_ca(ca: str = Path(..., description="Token contract address (mint)")) -> str:
    if not _is_valid_solana_address(ca):
        raise HTTPException(
            status_code=422,
            detail="Invalid Solana contract address: must be a base58-encoded 32-byte public key",
        )
    return ca


def validate_wallet(address: str = Path(..., description="Wallet address")) -> str:
    if not _is_valid_solana_address(address):
        raise HTTPException(
            status_code=422,
            detail="Invalid Solana wallet address: must be a base58-encoded 32-byte public key",
        )
    return address
