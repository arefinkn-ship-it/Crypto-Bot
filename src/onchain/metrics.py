# ============================================================
#  ON-CHAIN METRICS - Calculate on-chain indicators
# ============================================================

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from src.core.logger import logger
from src.onchain.client import OnChainClient


class OnChainMetrics:
    """
    Calculate on-chain metrics for signals.
    
    Metrics:
    - Netflow: Exchange inflows/outflows (proxy for whale activity)
    - Whale Score: Large transaction activity
    - Accumulation Score: Address accumulation patterns
    - Active Addresses: Network activity
    """
    
    def __init__(self):
        self.client = OnChainClient()
    
    def calculate_whale_score(self, symbol: str) -> Dict:
        """
        Calculate whale activity score.
        
        Returns:
            score: 0-10 (10 = high whale activity)
            direction: 'BUY' (accumulation), 'SELL' (distribution), or 'NEUTRAL'
        """
        # Placeholder - uses market data as proxy
        # In production, this would use Glassnode's whale transaction data
        data = self.client.get_coin_market_data(symbol)
        
        if not data:
            return {'score': 0, 'direction': 'NEUTRAL', 'confidence': 'LOW', 'reason': 'No data'}
        
        price = data.get('price_usd', 0)
        volume = data.get('volume_24h_usd', 0)
        market_cap = data.get('market_cap_usd', 0)
        
        # Proxy whale activity: high volume relative to market cap
        if market_cap and market_cap > 0:
            volume_ratio = volume / market_cap
        else:
            volume_ratio = 0
        
        # Score: 0-10 based on volume ratio
        if volume_ratio > 0.1:  # >10% of market cap traded daily
            score = 8 + min((volume_ratio - 0.1) * 10, 2)  # 8-10
            reason = "High volume relative to market cap (potential whale activity)"
        elif volume_ratio > 0.05:  # >5% of market cap
            score = 5 + (volume_ratio - 0.05) * 60  # 5-8
            reason = "Moderate volume relative to market cap"
        else:
            score = min(volume_ratio * 100, 5)  # 0-5
            reason = "Low volume relative to market cap"
        
        # Direction: price up + high volume = potential accumulation
        # Price down + high volume = potential distribution
        # We need price change to determine direction
        # For now, return neutral
        direction = 'NEUTRAL'
        
        return {
            'score': min(score, 10),
            'direction': direction,
            'confidence': 'MEDIUM' if score > 5 else 'LOW',
            'reason': reason,
            'indicators': {
                'price_usd': price,
                'volume_24h_usd': volume,
                'volume_ratio': round(volume_ratio * 100, 2),
                'market_cap_usd': market_cap,
            }
        }
    
    def calculate_accumulation_score(self, symbol: str) -> Dict:
        """
        Calculate accumulation score based on supply distribution.
        
        Returns:
            score: 0-10 (10 = strong accumulation)
            direction: 'BUY' (accumulation) or 'NEUTRAL'
        """
        data = self.client.get_coin_market_data(symbol)
        
        if not data:
            return {'score': 0, 'direction': 'NEUTRAL', 'confidence': 'LOW', 'reason': 'No data'}
        
        circulating_supply = data.get('circulating_supply', 0)
        total_supply = data.get('total_supply', 0)
        price = data.get('price_usd', 0)
        
        # Proxy for accumulation: high circulating supply ratio
        # High ratio = more supply available = potential accumulation
        if total_supply and total_supply > 0:
            supply_ratio = circulating_supply / total_supply
        else:
            supply_ratio = 0.5
        
        # Score: 0-10
        # High supply ratio = 6-10, Low supply ratio = 0-5
        score = 5 + (supply_ratio - 0.5) * 10
        score = min(max(score, 0), 10)
        
        return {
            'score': score,
            'direction': 'BUY' if score > 6 else 'NEUTRAL',
            'confidence': 'MEDIUM' if score > 6 else 'LOW',
            'reason': f"Supply ratio: {supply_ratio*100:.1f}% ({'accumulation potential' if score > 6 else 'limited'})",
            'indicators': {
                'circulating_supply': circulating_supply,
                'total_supply': total_supply,
                'supply_ratio': round(supply_ratio * 100, 2),
                'price_usd': price,
            }
        }
    
    def calculate_network_activity_score(self, symbol: str) -> Dict:
        """
        Calculate network activity score.
        
        Returns:
            score: 0-10 (10 = high network activity)
            direction: 'BUY' (increasing activity) or 'NEUTRAL'
        """
        data = self.client.get_coin_market_data(symbol)
        
        if not data:
            return {'score': 0, 'direction': 'NEUTRAL', 'confidence': 'LOW', 'reason': 'No data'}
        
        volume = data.get('volume_24h_usd', 0)
        market_cap = data.get('market_cap_usd', 0)
        
        # Volume-to-market-cap ratio as proxy for network activity
        if market_cap and market_cap > 0:
            activity_ratio = volume / market_cap
        else:
            activity_ratio = 0
        
        # Score: 0-10
        if activity_ratio > 0.1:
            score = 8 + min((activity_ratio - 0.1) * 20, 2)
        elif activity_ratio > 0.05:
            score = 5 + (activity_ratio - 0.05) * 60
        else:
            score = min(activity_ratio * 100, 5)
        
        score = min(max(score, 0), 10)
        
        return {
            'score': score,
            'direction': 'BUY' if score > 6 else 'NEUTRAL',
            'confidence': 'MEDIUM' if score > 6 else 'LOW',
            'reason': f"Network activity ratio: {activity_ratio*100:.2f}%",
            'indicators': {
                'volume_24h_usd': volume,
                'market_cap_usd': market_cap,
                'activity_ratio': round(activity_ratio * 100, 2),
            }
        }
    
    def calculate_onchain_score(self, symbol: str) -> Dict:
        """
        Calculate combined on-chain score.
        
        Returns:
            score: 0-10
            direction: 'BUY' or 'SELL' or 'NEUTRAL'
            confidence: 'HIGH', 'MEDIUM', or 'LOW'
        """
        # Get individual metrics
        whale = self.calculate_whale_score(symbol)
        accumulation = self.calculate_accumulation_score(symbol)
        network = self.calculate_network_activity_score(symbol)
        
        # Weighted average
        scores = {
            'whale': whale['score'] * 0.4,
            'accumulation': accumulation['score'] * 0.4,
            'network': network['score'] * 0.2,
        }
        
        total_score = sum(scores.values())
        
        # Determine direction
        directions = [whale['direction'], accumulation['direction'], network['direction']]
        buy_count = sum(1 for d in directions if d == 'BUY')
        sell_count = sum(1 for d in directions if d == 'SELL')
        
        if buy_count > sell_count:
            direction = 'BUY'
        elif sell_count > buy_count:
            direction = 'SELL'
        else:
            direction = 'NEUTRAL'
        
        # Confidence
        if total_score >= 7 and buy_count >= 2:
            confidence = 'HIGH'
        elif total_score >= 5 or buy_count >= 1:
            confidence = 'MEDIUM'
        else:
            confidence = 'LOW'
        
        return {
            'symbol': symbol,
            'score': round(total_score, 2),
            'direction': direction,
            'confidence': confidence,
            'details': {
                'whale': whale,
                'accumulation': accumulation,
                'network': network,
            },
            'reason': f"On-chain score: {total_score:.1f}/10",
        }