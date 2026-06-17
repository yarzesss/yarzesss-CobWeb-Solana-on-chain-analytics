"""Accounts + virtual copy-trading.

The whole feature is a paper-trading competition:
- A user registers (nickname + bcrypt-hashed password).
- They get a demo balance (default $1000) — just numbers, nothing real.
- They add real Solana wallets to a server-side watchlist.
- When a watched wallet BUYS a token (seen via the Helius webhook), the
  bot opens a VIRTUAL position for every user watching that wallet, sized
  by their configured position_size_usd, entered at the current market cap
  plus a small realism offset.
- When the watched wallet SELLS, the bot closes those positions at the
  current price; realised P&L lands on the user's demo balance.
- The leaderboard ranks users by total equity (cash + open positions
  marked to market).
- Reset wipes positions and restores the starting balance.

Nothing here touches real funds or real wallets of the user.
"""
import enum

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    nickname: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    nickname_lower: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))

    # Demo wallet — pure numbers
    balance_usd: Mapped[float] = mapped_column(Float, default=1000.0)
    starting_balance_usd: Mapped[float] = mapped_column(Float, default=1000.0)
    position_size_usd: Mapped[float] = mapped_column(Float, default=50.0)

    # Cached realised P&L so the leaderboard doesn't recompute every read
    realized_pnl_usd: Mapped[float] = mapped_column(Float, default=0.0)
    closed_trades: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class WatchedWallet(Base):
    """A real wallet a user is copy-following (server-side, for the bot)."""

    __tablename__ = "watched_wallets"
    __table_args__ = (
        UniqueConstraint("user_id", "wallet", name="uq_watch_user_wallet"),
        Index("ix_watched_wallet", "wallet"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    wallet: Mapped[str] = mapped_column(String(44))
    label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    added_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())


class Position(Base):
    """A virtual copy-trade position on a user's demo balance."""

    __tablename__ = "positions"
    __table_args__ = (
        Index("ix_pos_user_status", "user_id", "status"),
        Index("ix_pos_source_mint", "source_wallet", "mint", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    mint: Mapped[str] = mapped_column(String(44), index=True)
    source_wallet: Mapped[str] = mapped_column(String(44))  # whose buy we copied

    status: Mapped[str] = mapped_column(String(8), default="open")  # "open" | "closed"

    # entry
    invested_usd: Mapped[float] = mapped_column(Float)        # cash put in (position_size)
    entry_price_usd: Mapped[float] = mapped_column(Float)     # per-token, incl. realism offset
    entry_mcap_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    token_amount: Mapped[float] = mapped_column(Float)        # invested / entry_price
    opened_at: Mapped[int] = mapped_column(BigInteger)        # epoch seconds

    # exit (filled when closed)
    exit_price_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    proceeds_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    realized_pnl_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    closed_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
