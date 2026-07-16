# ============================================================
#  COIN SCANNER - Manage coins to monitor
# ============================================================

from typing import List, Dict
from datetime import datetime
from src.core.logger import logger
from src.data.binance_client import BinanceClient


class CoinScanner:
    """Scan and manage coins to monitor"""
    
    def __init__(self):
        self.client = BinanceClient()
        self.coins: List[str] = []
        self.last_update: datetime = None
    
    def update_coins(self, force: bool = False) -> List[str]:
        """
        Update list of coins to monitor
        Forces update every hour unless forced
        """
        now = datetime.now()
        
        # Check if we need to update
        if not force and self.last_update:
            hours_since_update = (now - self.last_update).total_seconds() / 3600
            if hours_since_update < 1:
                logger.debug(f"Using cached coin list ({len(self.coins)} coins)")
                return self.coins
        
        logger.info("🔄 Updating coin list...")
        
        # Get top coins by volume
        top_coins = self.client.get_top_coins_by_volume(150)
        
        # Also get gainers and losers (top 20 each)
        # This would need additional logic for price changes
        # We'll keep it simple for now
        
        self.coins = list(set(top_coins))  # Remove duplicates
        self.last_update = now
        
        logger.info(f"✅ Updated coin list: {len(self.coins)} coins")
        return self.coins
    
    def get_coins_to_scan(self) -> List[str]:
        """Get current list of coins to scan"""
        if not self.coins:
            return self.update_coins(force=True)
        return self.coins