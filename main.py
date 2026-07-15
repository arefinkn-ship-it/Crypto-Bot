#!/usr/bin/env python3
# ============================================================
#  CRYPTO BOT V2 - MAIN ENTRY POINT
# ============================================================

import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.core.logger import logger
from src.core.config import config
from src.core.database import init_database


def main():
    """Main entry point"""
    logger.info("🚀 Starting Crypto Bot V2")
    logger.info(f"📁 Project: {config.BASE_DIR}")
    
    try:
        # Initialize database
        init_database()
        logger.info("✅ Database ready")
        
        # TODO: Phase 2 - Data collector
        # TODO: Phase 3 - Indicators
        # TODO: Phase 4 - Strategies
        # TODO: Phase 5 - Alerts
        
        logger.info("✅ Bot initialized successfully!")
        logger.info("📊 Ready to scan for signals...")
        
        # Keep running
        import time
        while True:
            logger.info("⏳ Waiting for next scan cycle...")
            time.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("👋 Shutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()