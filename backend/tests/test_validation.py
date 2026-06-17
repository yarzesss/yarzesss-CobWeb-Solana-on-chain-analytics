"""Tests for Solana address validation."""
import pytest
from fastapi import HTTPException

from app.core.validation import _is_valid_solana_address, validate_ca, validate_wallet

VALID = "So11111111111111111111111111111111111111112"  # wSOL mint


def test_valid_address():
    assert _is_valid_solana_address(VALID)


@pytest.mark.parametrize("bad", [
    "", "abrakadabra", "0x1234567890abcdef1234567890abcdef12345678",  # EVM address
    "So1111", "I" * 44,  # 'I' is not in the base58 alphabet
])
def test_invalid_addresses(bad):
    assert not _is_valid_solana_address(bad)


def test_validate_ca_raises_422():
    with pytest.raises(HTTPException) as exc:
        validate_ca("not-a-mint")
    assert exc.value.status_code == 422


def test_validate_wallet_passes_valid():
    assert validate_wallet(VALID) == VALID
