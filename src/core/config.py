# ============================================================
#  CONFIG LOADER - Secure environment configuration
#  Secrets & environment values ONLY. Strategy/signal-tuning
#  values (scan interval, thresholds, weights, whitelist) live
#  in src/core/bot_config.py instead - keeping them separate
#  avoids the two files silently disagreeing about which one
#  actually controls behavior.
# ============================================================

import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / '.env'

load_dotenv(dotenv_path=ENV_FILE)


@dataclass
class Config:
    """Secrets and environment settings only."""

    BASE_DIR: Path = BASE_DIR

    # ---------- Binance API ----------
    BINANCE_API_KEY: str = os.getenv('BINANCE_API_KEY', '')
    BINANCE_API_SECRET: str = os.getenv('BINANCE_API_SECRET', '')

    # ---------- Telegram ----------
    TELEGRAM_TOKEN: str = os.getenv('TELEGRAM_TOKEN', '')
    TELEGRAM_CHAT_ID: str = os.getenv('TELEGRAM_CHAT_ID', '')

    # ---------- Database ----------
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'sqlite:///crypto_bot.db')

    # ---------- Logging ----------
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_RETENTION_DAYS: int = int(os.getenv('LOG_RETENTION_DAYS', '30'))

    # NOTE: SCAN_INTERVAL_SECONDS, MIN_SIGNAL_SCORE, MAX_SIGNALS_PER_DAY,
    # TOP_N_COINS, WATCHLIST etc. used to live here - REMOVED. They now
    # live in src/core/bot_config.py. If you're looking to tune signal
    # behavior, edit that file, not this one or .env.

    @classmethod
    def validate(cls) -> bool:
        required = [
            ('BINANCE_API_KEY', cls.BINANCE_API_KEY),
            ('BINANCE_API_SECRET', cls.BINANCE_API_SECRET),
            ('TELEGRAM_TOKEN', cls.TELEGRAM_TOKEN),
            ('TELEGRAM_CHAT_ID', cls.TELEGRAM_CHAT_ID),
        ]

        missing = [name for name, value in required if not value]

        if missing:
            raise ValueError(
                f"\n{'='*60}\n"
                f"❌ MISSING REQUIRED ENVIRONMENT VARIABLES:\n"
                f"{', '.join(missing)}\n\n"
                f"Please check your .env file at: {cls.BASE_DIR / '.env'}\n"
                f"{'='*60}\n"
            )

        masked = {
            'BINANCE_API_KEY': cls.BINANCE_API_KEY[:8] + '...' if cls.BINANCE_API_KEY else None,
            'TELEGRAM_TOKEN': cls.TELEGRAM_TOKEN[:8] + '...' if cls.TELEGRAM_TOKEN else None,
        }

        print("\n" + "="*60)
        print("✅ CONFIGURATION LOADED SUCCESSFULLY")
        print("="*60)
        print(f"📁 Project Directory: {cls.BASE_DIR}")
        print(f"🗄️  Database: {cls.DATABASE_URL}")
        print(f"🔑 Binance Key: {masked['BINANCE_API_KEY']}")
        print(f"🤖 Telegram Token: {masked['TELEGRAM_TOKEN']}")
        print("ℹ️  Signal tuning values now live in src/core/bot_config.py")
        print("="*60 + "\n")

        return True


config = Config()
config.validate()