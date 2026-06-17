"""Account: balance, settings, watchlist, positions, reset."""
import re
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.config import settings
from app.core.auth import get_current_user, TokenData
from app.core.ratelimit import light_limiter
from app.core.validation import _is_valid_solana_address
from app.database import AsyncSessionLocal
from app.models.accounts import User, WatchedWallet
from app.services.copytrade import get_account_equity, reset_account
from app.services.webhook_manager import sync_webhook_addresses

router = APIRouter(prefix="/account", tags=["Account"], dependencies=[Depends(light_limiter)])

MAX_WATCHED = 50


async def _load_user(db, user_id: int) -> User:
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return user


class PositionSizeUpdate(BaseModel):
    position_size_usd: float = Field(..., gt=0)


class AddWalletRequest(BaseModel):
    wallet: str
    label: str | None = Field(default=None, max_length=64)


@router.get("", summary="Account snapshot (balance, equity, open positions)")
async def account_snapshot(current: TokenData = Depends(get_current_user)) -> Dict[str, Any]:
    async with AsyncSessionLocal() as db:
        user = await _load_user(db, current.user_id)
        return await get_account_equity(db, user)


@router.put("/position-size", summary="Set copy position size (USD)")
async def set_position_size(
    payload: PositionSizeUpdate, current: TokenData = Depends(get_current_user)
) -> Dict[str, Any]:
    size = max(settings.MIN_POSITION_SIZE_USD, min(payload.position_size_usd, settings.MAX_POSITION_SIZE_USD))
    async with AsyncSessionLocal() as db:
        user = await _load_user(db, current.user_id)
        user.position_size_usd = size
        await db.commit()
        return {"position_size_usd": size}


@router.post("/reset", summary="Reset demo balance and wipe positions")
async def reset(current: TokenData = Depends(get_current_user)) -> Dict[str, Any]:
    async with AsyncSessionLocal() as db:
        user = await _load_user(db, current.user_id)
        await reset_account(db, user)
        await db.commit()
        return {"balance_usd": user.balance_usd, "reset": True}


# ── Watchlist (server-side, drives the bot) ─────────────────────────────────

@router.get("/watchlist", summary="Wallets this account copy-follows")
async def get_watchlist(current: TokenData = Depends(get_current_user)) -> List[Dict[str, Any]]:
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(WatchedWallet).where(WatchedWallet.user_id == current.user_id)
                .order_by(WatchedWallet.added_at.desc())
            )
        ).scalars().all()
        return [
            {"wallet": r.wallet, "label": r.label, "added_at": r.added_at.isoformat() if r.added_at else None}
            for r in rows
        ]


@router.post("/watchlist", summary="Follow a wallet")
async def add_watchlist(
    payload: AddWalletRequest, current: TokenData = Depends(get_current_user)
) -> Dict[str, Any]:
    if not _is_valid_solana_address(payload.wallet):
        raise HTTPException(status_code=422, detail="Invalid Solana wallet address")

    async with AsyncSessionLocal() as db:
        count = (
            await db.execute(
                select(WatchedWallet).where(WatchedWallet.user_id == current.user_id)
            )
        ).scalars().all()
        if len(count) >= MAX_WATCHED:
            raise HTTPException(status_code=400, detail=f"Watchlist limit is {MAX_WATCHED}")
        if any(w.wallet == payload.wallet for w in count):
            raise HTTPException(status_code=409, detail="Already following this wallet")

        db.add(WatchedWallet(
            user_id=current.user_id, wallet=payload.wallet, label=payload.label,
        ))
        await db.commit()
        # Best-effort: tell Helius to start watching this wallet.
        sync = await sync_webhook_addresses(db)
        return {"wallet": payload.wallet, "label": payload.label, "added": True, "webhook": sync}


@router.delete("/watchlist/{wallet}", summary="Unfollow a wallet")
async def remove_watchlist(
    wallet: str, current: TokenData = Depends(get_current_user)
) -> Dict[str, Any]:
    async with AsyncSessionLocal() as db:
        await db.execute(
            WatchedWallet.__table__.delete().where(
                (WatchedWallet.user_id == current.user_id) & (WatchedWallet.wallet == wallet)
            )
        )
        await db.commit()
        # Best-effort: stop watching this wallet if no one else follows it.
        sync = await sync_webhook_addresses(db)
        return {"wallet": wallet, "removed": True, "webhook": sync}
