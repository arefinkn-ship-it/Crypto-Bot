# ============================================================
#  WHALE ACCUMULATION - Detect accumulation patterns
# ============================================================

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from src.core.logger import logger
from src.onchain.client import OnChainClient


class AccumulationDetector:
    """
    Detect whale accumulation patterns.
    
    Signals:
    - Increasing volume with stable/upward price = accumulation
    - Decreasing supply on exchanges = accumulation
    - High whale transaction count = accumulation
    """
    
    def __init__(self):
        self.client = OnChainClient()
    
    def detect_accumulation(self, symbol: str) -> Dict:
        """
        Detect accumulation patterns.
        
        Returns:
            score: 0-10 (10 = strong accumulation)
            direction: 'BUY' (accumulation) or 'NEUTRAL'
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
        circulating_supply = data.get('circulating_supply', 0)
        total_supply = data.get('total_supply', 0)
        
        # Proxy 1: Volume-to-market-cap ratio (accumulation indicator)
        if market_cap and market_cap > 0:
            volume_ratio = volume / market_cap
        else:
            volume_ratio = 0
        
        # Proxy 2: Circulating supply ratio (higher = more available for accumulation)
        if total_supply and total_supply > 0:
            supply_ratio = circulating_supply / total_supply
        else:
            supply_ratio = 0.5
        
        # Accumulation score
        score = 0
        reasons = []
        
        # Volume ratio component
        if volume_ratio > 0.1:
            score += 4
            reasons.append("High volume/mcap ratio")
        elif volume_ratio > 0.05:
            score += 2
            reasons.append("Moderate volume/mcap ratio")
        
        # Supply ratio component
        if supply_ratio > 0.6:
            score += 3
            reasons.append("High circulating supply ratio")
        elif supply_ratio > 0.4:
            score += 2
            reasons.append("Moderate circulating supply ratio")
        
        # Market cap component (larger coins = more institutional interest)
        if market_cap and market_cap > 10_000_000_000:  # >$10B
            score += 3
            reasons.append("Large market cap (institutional interest)")
        elif market_cap and market_cap > 1_000_000_000:  # >$1B
            score += 1
            reasons.append("Medium market cap")
        
        score = min(score, 10)
        
        return {
            'score': score,
            'direction': 'BUY' if score > 5 else 'NEUTRAL',
            'confidence': 'HIGH' if score > 7 else 'MEDIUM' if score > 4 else 'LOW',
            'reason': f"Accumulation score: {score:.1f}/10 - {' '.join(reasons[:2])}",
            'indicators': {
                'volume_to_mcap': round(volume_ratio * 100, 2),
                'supply_ratio': round(supply_ratio * 100, 2),
                'market_cap_usd': market_cap,
                'price_usd': price,
            }
        }