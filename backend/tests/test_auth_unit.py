"""Password hashing + JWT round-trip."""
from app.core.auth import hash_password, verify_password, create_access_token
from jose import jwt
from app.config import settings


def test_password_hash_roundtrip():
    h = hash_password("mySecret123")
    assert h != "mySecret123"  # never plaintext
    assert verify_password("mySecret123", h)
    assert not verify_password("wrongpass", h)


def test_jwt_contains_user_id():
    token = create_access_token(42, "tester")
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    assert payload["sub"] == "42"
    assert payload["nick"] == "tester"
