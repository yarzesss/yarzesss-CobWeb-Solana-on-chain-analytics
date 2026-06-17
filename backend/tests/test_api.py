"""API smoke tests via FastAPI TestClient — no network, no Redis required."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_invalid_ca_rejected_before_any_upstream_call():
    resp = client.get("/token/not-a-real-mint")
    assert resp.status_code == 422
    assert "Invalid Solana" in resp.json()["detail"]


def test_invalid_wallet_rejected():
    resp = client.get("/wallet/0xdeadbeef")
    assert resp.status_code == 422


def test_webhook_rejects_wrong_secret(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "HELIUS_WEBHOOK_SECRET", "topsecret")
    resp = client.post("/webhooks/helius", json=[], headers={"Authorization": "wrong"})
    assert resp.status_code == 401


def test_leaderboard_degrades_gracefully_without_db():
    # No Postgres in tests → must return an honest empty board, not a 500
    resp = client.get("/leaderboard")
    assert resp.status_code == 200
    body = resp.json()
    assert body["entries"] == []
    assert body["active"] is False


def test_stats_endpoint():
    resp = client.get("/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert "alerts_enabled" in body and "leaderboard_refresh_enabled" in body


