"""Auth + account API smoke tests via TestClient (no DB → expect graceful errors).

Full DB-backed flows are covered in test_copytrade.py; here we check
validation, auth gating, and that protected routes reject anonymous calls.
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_register_validates_nickname():
    r = client.post("/auth/register", json={"nickname": "ab", "password": "secret123"})
    assert r.status_code == 422  # too short


def test_register_validates_password():
    r = client.post("/auth/register", json={"nickname": "validnick", "password": "123"})
    assert r.status_code == 422  # too short


def test_account_requires_auth():
    assert client.get("/account").status_code == 401


def test_watchlist_requires_auth():
    assert client.get("/account/watchlist").status_code == 401
    assert client.post("/account/watchlist", json={"wallet": "x"}).status_code == 401


def test_position_size_requires_auth():
    assert client.put("/account/position-size", json={"position_size_usd": 50}).status_code == 401


def test_reset_requires_auth():
    assert client.post("/account/reset").status_code == 401


def test_me_requires_auth():
    assert client.get("/auth/me").status_code == 401


def test_invalid_token_rejected():
    r = client.get("/account", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


def test_leaderboard_public():
    # Leaderboard is public; with no DB it returns graceful empty, not 500
    r = client.get("/leaderboard")
    assert r.status_code == 200
    assert "entries" in r.json()
