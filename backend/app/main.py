"""Cobweb FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core import cache
from app.services.helius import get_helius_client
import asyncio
import logging

from app.database import init_db, AsyncSessionLocal
from app.routers import auth as auth_router
from app.routers import account as account_router
from app.routers import leaderboard as leaderboard_router
from app.routers import webhooks as webhooks_router

# Optional Sentry — activates only when SENTRY_DSN is set
if settings.SENTRY_DSN:
    try:
        import sentry_sdk
        sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.1)
    except Exception:
        logging.getLogger("cobweb").warning("Sentry init failed; continuing without it")
from app.routers import tokens as tokens_router
from app.routers import wallets as wallets_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    await cache.get_redis()
    if settings.DB_AUTO_CREATE:
        try:
            await init_db()
        except Exception as exc:  # DB down must not block the API — index features degrade
            logging.getLogger("cobweb").warning("init_db skipped: %s", exc)

    # Reconcile the Helius webhook address list with the DB on startup,
    # so a restart re-pushes the correct watched-wallet set.
    if settings.HELIUS_WEBHOOK_ID:
        try:
            from app.services.webhook_manager import sync_webhook_addresses
            async with AsyncSessionLocal() as _db:
                await sync_webhook_addresses(_db)
        except Exception as exc:
            logging.getLogger("cobweb").warning("webhook reconcile skipped: %s", exc)

    background_tasks = []

    yield

    for task in background_tasks:
        task.cancel()
    # ── Shutdown ──
    await cache.close()
    await get_helius_client().aclose()


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENVIRONMENT == "development" else [settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tokens_router.router)
app.include_router(wallets_router.router)
app.include_router(auth_router.router)
app.include_router(account_router.router)
app.include_router(webhooks_router.router)
app.include_router(leaderboard_router.router)


@app.get("/stats", tags=["Health"])
async def stats():
    """Operational counters: today's Helius API usage etc."""
    import datetime as _dt
    counters = {}
    try:
        r = await cache.get_redis()
        for delta, label in ((0, "today"), (1, "yesterday")):
            day = (_dt.datetime.utcnow() - _dt.timedelta(days=delta)).strftime("%Y-%m-%d")
            v = await r.get(f"quota:helius:{day}")
            counters[f"helius_calls_{label}"] = int(v) if v else 0
    except Exception:
        counters = {"helius_calls_today": None, "helius_calls_yesterday": None}
    return {
        "alerts_enabled": bool(settings.TELEGRAM_BOT_TOKEN) and settings.ALERTS_ENABLED,
        "leaderboard_refresh_enabled": settings.LEADERBOARD_REFRESH_ENABLED,
        **counters,
    }


@app.get("/healthz", tags=["Health"])
async def healthz() -> dict:
    return {"status": "ok", "app": settings.APP_NAME}