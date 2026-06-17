"""Registration & login — nickname + password."""
import re
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.core.auth import (
    create_access_token,
    hash_password,
    verify_password,
    get_current_user,
    TokenData,
)
from app.core.ratelimit import light_limiter
from app.database import AsyncSessionLocal
from app.models.accounts import User
from sqlalchemy import select

router = APIRouter(prefix="/auth", tags=["Auth"], dependencies=[Depends(light_limiter)])

_NICK_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")


class Credentials(BaseModel):
    nickname: str = Field(..., min_length=3, max_length=20)
    password: str = Field(..., min_length=6, max_length=128)


def _token_response(user: User) -> Dict[str, Any]:
    return {
        "access_token": create_access_token(user.id, user.nickname),
        "token_type": "bearer",
        "nickname": user.nickname,
    }


@router.post("/register", summary="Create an account")
async def register(creds: Credentials) -> Dict[str, Any]:
    if not _NICK_RE.match(creds.nickname):
        raise HTTPException(
            status_code=422,
            detail="Nickname must be 3-20 chars: letters, digits, underscore only",
        )
    nick_lower = creds.nickname.lower()

    async with AsyncSessionLocal() as db:
        existing = (
            await db.execute(select(User).where(User.nickname_lower == nick_lower))
        ).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(status_code=409, detail="Nickname already taken")

        user = User(
            nickname=creds.nickname,
            nickname_lower=nick_lower,
            password_hash=hash_password(creds.password),
            balance_usd=settings.DEMO_STARTING_BALANCE_USD,
            starting_balance_usd=settings.DEMO_STARTING_BALANCE_USD,
            position_size_usd=settings.DEFAULT_POSITION_SIZE_USD,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return _token_response(user)


@router.post("/login", summary="Log in")
async def login(creds: Credentials) -> Dict[str, Any]:
    async with AsyncSessionLocal() as db:
        user = (
            await db.execute(select(User).where(User.nickname_lower == creds.nickname.lower()))
        ).scalar_one_or_none()
        if user is None or not verify_password(creds.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Wrong nickname or password")
        return _token_response(user)


@router.get("/me", summary="Current account (token check)")
async def me(current: TokenData = Depends(get_current_user)) -> Dict[str, Any]:
    return {"user_id": current.user_id, "nickname": current.nickname}
