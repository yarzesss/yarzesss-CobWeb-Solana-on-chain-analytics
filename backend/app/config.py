from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "SolanaIntel"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database (поки що не використовується роутерами — watchlist живе в Redis)
    DATABASE_URL: str = "postgresql+asyncpg://cobweb:cobweb@postgres:5432/cobweb"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth
    JWT_SECRET: str = "change_me_in_production_via_env"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 20160  # 14 days

    # Demo copy-trading
    DEMO_STARTING_BALANCE_USD: float = 1000.0
    DEFAULT_POSITION_SIZE_USD: float = 50.0
    COPY_ENTRY_MCAP_OFFSET_USD: float = 2500.0  # realism: enter a bit higher than the watched wallet
    MIN_POSITION_SIZE_USD: float = 5.0
    MAX_POSITION_SIZE_USD: float = 500.0

    # Helius RPC
    HELIUS_API_KEY: str
    HELIUS_RPC_URL: str = "https://mainnet.helius-rpc.com"
    HELIUS_API_URL: str = "https://api.helius.xyz/v0"


    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""

    # Cache TTL (секунди)
    CACHE_TTL_TOKEN: int = 300       # 5 хвилин — дані токена
    CACHE_TTL_WALLET: int = 600      # 10 хвилин — профіль гаманця
    CACHE_TTL_CABAL: int = 1800      # 30 хвилин — cabal аналіз

    # Rate limiting
    HELIUS_REQUESTS_PER_SECOND: int = 10
    MAX_WALLETS_PER_CABAL_SCAN: int = 50  # скільки гаманців аналізуємо за раз
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_HEAVY_PER_MINUTE: int = 10   # /token/{ca}, /wallet/{addr} — fan-out у Helius
    RATE_LIMIT_LIGHT_PER_MINUTE: int = 60   # auth, watchlist, кешовані читання

    # Early buyers
    EARLY_BUY_MARKET_CAP_USD: int = 10000  # поріг "ранній покупець" — 10k капа
    MAX_TX_PAGES_FOR_EARLY_BUYERS: int = 30  # макс. сторінок історії (30 × 100 = 3000 tx)
    MAX_EARLY_BUYERS: int = 150  # скільки перших унікальних покупців вважаємо "ранніми"

    # Prices
    CACHE_TTL_PRICE: int = 60                # 1 хвилина — ціна SOL
    SOL_PRICE_FALLBACK_USD: float = 150.0    # якщо всі price API недоступні

    # Webhook indexing
    HELIUS_WEBHOOK_SECRET: str = ""
    HELIUS_WEBHOOK_ID: str = ""        # for dynamic copy-trade wallet tracking        # Authorization header value Helius sends; empty = disabled check
    INDEX_MAX_EARLY_BUYS_PER_TOKEN: int = 150
    DB_AUTO_CREATE: bool = True            # create_all on startup (pre-alembic stage)

    # Background leaderboard stats
    LEADERBOARD_REFRESH_ENABLED: bool = True
    LEADERBOARD_REFRESH_MINUTES: int = 30
    LEADERBOARD_STATS_BATCH: int = 15      # wallets profiled per refresh cycle
    LEADERBOARD_STATS_MAX_AGE_HOURS: int = 6

    # Alerts
    ALERTS_ENABLED: bool = True

    # Monitoring
    SENTRY_DSN: str = ""

    # CORS
    FRONTEND_ORIGIN: str = "https://cobweb.so"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()