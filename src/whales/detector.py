# ============================================================
#  WHALE DETECTOR - Identify large transactions
# ============================================================

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from src.core.logger import logger
from src.onchain.client import OnChainClient


class WhaleDetector:
    """
    Detect whale transactions and activity.
    
    Note: Full whale transaction data requires Glassnode API.
    This uses market data as a proxy until Glassnode is integrated.
    """
    
    def __init__(self):
        self.client = OnChainClient()
    
    def detect_whale_activity(self, symbol: str) -> Dict:
        """
        Detect whale activity using market data proxies.
        
        Returns:
            score: 0-10 (10 = high whale activity)
            direction: 'BUY' or 'SELL' or 'NEUTRAL'
        """
        data = self.client.get_coin_market_data(symbol)
        
        if not data:
            return {
                'score': 0,
                'direction': 'NEUTRAL',
                'confidence': 'LOW',
                'reason': 'No data available'
            }
        
        price = data.get('price_usd', 0)
        volume = data.get('volume_24h_usd', 0)
        market_cap = data.get('market_cap_usd', 0)
        
        # Proxy: large volume spikes indicate whale activity
        if market_cap and market_cap > 0:
            volume_to_mcap = volume / market_cap
        else:
            volume_to_mcap = 0
        
        # Whale activity score
        if volume_to_mcap > 0.15:
            score = 9.0
            reason = "Very high volume/mcap ratio (potential whale activity)"
        elif volume_to_mcap > 0.10:
            score = 7.0
            reason = "High volume/mcap ratio (whale activity likely)"
        elif volume_to_mcap > 0.05:
            score = 5.0
            reason = "Moderate volume/mcap ratio"
        else:
            score = min(volume_to_mcap * 50, 4)
            reason = "Low volume/mcap ratio (limited whale activity)"
        
        # Direction proxy: price movement with high volume
        # For now, return neutral
        direction = 'NEUTRAL'
        
        return {
            'score': min(score, 10),
            'direction': direction,
            'confidence': 'HIGH' if score > 7 else 'MEDIUM' if score > 4 else 'LOW',
            'reason': reason,
            'indicators': {
                'volume_to_mcap': round(volume_to_mcap * 100, 2),
                'price_usd': price,
                'volume_24h_usd': volume,
                'market_cap_usd': market_cap,
            }
        }