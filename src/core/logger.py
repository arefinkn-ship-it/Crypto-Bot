# ============================================================
#  LOGGER - Structured logging with rotation
# ============================================================

import sys
from pathlib import Path
from loguru import logger
from src.core.config import config

# Remove default handler
logger.remove()

# Console logging with color
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=config.LOG_LEVEL,
    colorize=True,
)

# File logging with rotation
LOG_DIR = config.BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

logger.add(
    LOG_DIR / 'bot_{time:YYYY-MM-DD}.log',
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
    level='DEBUG',
    rotation='1 day',
    retention=f'{config.LOG_RETENTION_DAYS} days',
    compression='zip',
    backtrace=True,
    diagnose=True,
)

# Error logging separately
logger.add(
    LOG_DIR / 'errors_{time:YYYY-MM-DD}.log',
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
    level='ERROR',
    rotation='1 day',
    retention=f'{config.LOG_RETENTION_DAYS} days',
    compression='zip',
    backtrace=True,
    diagnose=True,
)

# Export logger
__all__ = ['logger']