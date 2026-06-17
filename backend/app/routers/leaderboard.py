"""Leaderboard — accounts ranked by demo-trading equity.

The competition: who picked the best wallets to copy. Equity is cash +
open positions marked to market, so even unclosed trades count.
"""
from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.core.ratelimit import light_limiter
from app.database import AsyncSessionLocal
from app.services.copytrade import get_leaderboard

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"], dependencies=[Depends(light_limiter)])


@router.get("", summary="Top accounts by demo equity")
async def leaderboard(limit: int = 50) -> Dict[str, Any]:
    limit = max(1, min(limit, 100))
    try:
        async with AsyncSessionLocal() as db:
            entries = await get_leaderboard(db, limit=limit)
    except Exception:
        return {"entries": [], "active": False,
                "message": "Leaderboard unavailable — database not reachable."}

    return {
        "entries": entries,
        "active": True,
        "message": None if entries else "No players yet. Register, follow wallets, and start climbing.",
    }
