#!/usr/bin/env python3
# ============================================================
#  FIBONACCI MANAGER - Fibonacci Level Calculations
# ============================================================

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple

from src.core.logger import logger


class FibonacciManager:
    """
    Manages Fibonacci retracement and extension calculations
    for technical analysis and trading signals
    """
    
    # Standard Fibonacci retracement levels
    RETRACEMENT_LEVELS = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
    
    # Standard Fibonacci extension levels
    EXTENSION_LEVELS = [0.0, 0.618, 1.0, 1.272, 1.618, 2.0, 2.618, 3.0, 4.236]
    
    def __init__(self):
        self.levels = {}
        self.high = None
        self.low = None
        self.start_price = None
        self.end_price = None
        
    def calculate_retracement(self, high: float, low: float) -> Dict[float, float]:
        """
        Calculate Fibonacci retracement levels between high and low
        
        Args:
            high: The highest price in the range
            low: The lowest price in the range
            
        Returns:
            Dictionary mapping level to price
        """
        self.high = high
        self.low = low
        self.start_price = high
        self.end_price = low
        
        diff = high - low
        
        levels = {}
        for level in self.RETRACEMENT_LEVELS:
            price = high - (diff * level)
            levels[level] = price
            
        self.levels = levels
        return levels
    
    def calculate_extension(self, start: float, end: float, retracement: float = 0.618) -> Dict[float, float]:
        """
        Calculate Fibonacci extension levels
        
        Args:
            start: Starting price of the move
            end: Ending price of the move
            retracement: Retracement level to use as reference
            
        Returns:
            Dictionary mapping extension level to price
        """
        self.start_price = start
        self.end_price = end
        
        diff = end - start
        direction = 1 if diff > 0 else -1
        
        levels = {}
        for level in self.EXTENSION_LEVELS:
            price = end + (diff * direction * (level - retracement))
            levels[level] = price
            
        self.levels = levels
        return levels
    
    def get_level(self, level: float) -> Optional[float]:
        """
        Get price at a specific Fibonacci level
        
        Args:
            level: The Fibonacci level (e.g., 0.618)
            
        Returns:
            Price at that level, or None if not found
        """
        return self.levels.get(level)
    
    def find_nearest_level(self, price: float, levels: Optional[List[float]] = None) -> Tuple[Optional[float], Optional[float]]:
        """
        Find the nearest Fibonacci level to a given price
        
        Args:
            price: The price to check
            levels: Optional specific levels to check (default: all RETRACEMENT_LEVELS)
            
        Returns:
            Tuple of (nearest_level, price_at_level)
        """
        if levels is None:
            levels = self.RETRACEMENT_LEVELS
            
        nearest_level = None
        nearest_price = None
        min_diff = float('inf')
        
        for level in levels:
            if level in self.levels:
                level_price = self.levels[level]
                diff = abs(price - level_price)
                if diff < min_diff:
                    min_diff = diff
                    nearest_level = level
                    nearest_price = level_price
                    
        return nearest_level, nearest_price
    
    def get_support_resistance(self) -> Dict[str, Optional[float]]:
        """
        Identify key Fibonacci support and resistance levels
        
        Returns:
            Dictionary with 'support' and 'resistance' levels
        """
        if not self.levels:
            return {'support': None, 'resistance': None, 'support_level': None, 'resistance_level': None}
            
        # Key levels for support/resistance
        key_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
        
        support_levels = []
        resistance_levels = []
        
        current_price = self.levels.get(1.0, self.high)
        
        for level in key_levels:
            if level in self.levels:
                price = self.levels[level]
                if price < current_price:
                    support_levels.append((level, price))
                else:
                    resistance_levels.append((level, price))
                    
        # Get nearest support and resistance
        support = max(support_levels, key=lambda x: x[1])[1] if support_levels else None
        resistance = min(resistance_levels, key=lambda x: x[1])[1] if resistance_levels else None
        
        return {
            'support': support,
            'resistance': resistance,
            'support_level': support_levels[-1][0] if support_levels else None,
            'resistance_level': resistance_levels[0][0] if resistance_levels else None
        }
    
    def calculate_fibonacci_clusters(self, data: pd.DataFrame, window: int = 100) -> pd.DataFrame:
        """
        Calculate Fibonacci levels for multiple swing points in a dataset
        
        Args:
            data: DataFrame with 'high', 'low', 'close' columns
            window: Number of candles to look back for swing points
            
        Returns:
            DataFrame with Fibonacci levels for each candle
        """
        if len(data) < window:
            logger.warning("Insufficient data for Fibonacci cluster calculation")
            return pd.DataFrame()
            
        # Find swing highs and lows
        data = data.copy()
        data['swing_high'] = data['high'].rolling(window=window, center=True).apply(
            lambda x: x[-window//2] if x[-window//2] == x.max() else np.nan
        )
        data['swing_low'] = data['low'].rolling(window=window, center=True).apply(
            lambda x: x[-window//2] if x[-window//2] == x.min() else np.nan
        )
        
        # Forward fill to propagate swings
        data['swing_high'] = data['swing_high'].ffill()
        data['swing_low'] = data['swing_low'].ffill()
        
        # Calculate Fibonacci levels for each point
        levels = {}
        for level in self.RETRACEMENT_LEVELS:
            levels[f'fib_{int(level*1000)}'] = data['swing_high'] - (data['swing_high'] - data['swing_low']) * level
            
        result = pd.DataFrame(levels)
        result['timestamp'] = data['timestamp'] if 'timestamp' in data else data.index
        
        return result
    
    def get_trade_levels(self, direction: str, entry_price: float, 
                         risk_reward: float = 2.0) -> Dict[str, Optional[float]]:
        """
        Get optimal entry, stop loss, and take profit levels using Fibonacci
        
        Args:
            direction: 'BUY' or 'SELL'
            entry_price: The entry price
            risk_reward: Desired risk-reward ratio
            
        Returns:
            Dictionary with entry, stop_loss, take_profit levels
        """
        if not self.levels:
            return {
                'entry': entry_price,
                'stop_loss': None,
                'take_profit': None,
                'risk_reward': None,
                'support': None,
                'resistance': None
            }
            
        # Get support and resistance
        sr = self.get_support_resistance()
        
        if direction == 'BUY':
            # For buys: place stop below support, take profit at resistance
            stop_loss = sr.get('support')
            if stop_loss is None:
                # Fallback: use 0.786 level or 2% below entry
                stop_loss = self.get_level(0.786) or (entry_price * 0.98)
                
            take_profit = sr.get('resistance')
            if take_profit is None:
                # Fallback: use risk_reward ratio
                risk = entry_price - stop_loss
                take_profit = entry_price + (risk * risk_reward)
                
        else:  # SELL
            # For sells: place stop above resistance, take profit at support
            stop_loss = sr.get('resistance')
            if stop_loss is None:
                # Fallback: use 0.786 level or 2% above entry
                stop_loss = self.get_level(0.786) or (entry_price * 1.02)
                
            take_profit = sr.get('support')
            if take_profit is None:
                # Fallback: use risk_reward ratio
                risk = stop_loss - entry_price
                take_profit = entry_price - (risk * risk_reward)
                
        # Calculate actual risk-reward ratio
        risk = abs(stop_loss - entry_price) if stop_loss else 0
        reward = abs(take_profit - entry_price) if take_profit else 0
        actual_rr = reward / risk if risk > 0 else None
        
        return {
            'entry': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'risk_reward': actual_rr,
            'support': sr.get('support'),
            'resistance': sr.get('resistance')
        }
    
    def is_at_fibonacci_level(self, price: float, tolerance: float = 0.001) -> Dict[str, bool]:
        """
        Check if price is at any Fibonacci level
        
        Args:
            price: Current price
            tolerance: Tolerance as percentage (0.001 = 0.1%)
            
        Returns:
            Dictionary mapping level to boolean indicating if price is at that level
        """
        results = {}
        
        for level, level_price in self.levels.items():
            diff_pct = abs(price - level_price) / price if price > 0 else 0
            results[f'at_fib_{int(level*1000)}'] = diff_pct <= tolerance
            
        return results
    
    def get_fibonacci_confluence(self, prices: List[float]) -> Dict[float, int]:
        """
        Find Fibonacci levels where multiple prices converge
        
        Args:
            prices: List of prices to check
            
        Returns:
            Dictionary mapping level to number of convergences
        """
        confluence = {}
        
        for price in prices:
            nearest_level, _ = self.find_nearest_level(price)
            if nearest_level is not None:
                confluence[nearest_level] = confluence.get(nearest_level, 0) + 1
                
        return confluence
    
    def generate_fibonacci_description(self) -> str:
        """
        Generate a human-readable description of the Fibonacci levels
        
        Returns:
            Description string
        """
        if not self.levels:
            return "No Fibonacci levels calculated"
            
        desc = f"Fibonacci Levels (High: {self.high:.8f}, Low: {self.low:.8f})\n"
        
        for level in self.RETRACEMENT_LEVELS:
            if level in self.levels:
                price = self.levels[level]
                desc += f"  {level:.3f}: {price:.8f}\n"
                
        # Add support/resistance
        sr = self.get_support_resistance()
        if sr['support']:
            desc += f"Support: {sr['support']:.8f} (Level {sr['support_level']:.3f})\n"
        if sr['resistance']:
            desc += f"Resistance: {sr['resistance']:.8f} (Level {sr['resistance_level']:.3f})"
            
        return desc


# Utility functions for easy access

def calculate_fibonacci_levels(high: float, low: float) -> Dict[float, float]:
    """
    Quick utility to calculate Fibonacci retracement levels
    
    Args:
        high: Highest price
        low: Lowest price
        
    Returns:
        Dictionary of Fibonacci levels
    """
    fm = FibonacciManager()
    return fm.calculate_retracement(high, low)


def find_fibonacci_support_resistance(high: float, low: float) -> Dict[str, Optional[float]]:
    """
    Quick utility to find support and resistance using Fibonacci
    
    Args:
        high: Highest price
        low: Lowest price
        
    Returns:
        Dictionary with support and resistance
    """
    fm = FibonacciManager()
    fm.calculate_retracement(high, low)
    return fm.get_support_resistance()


def is_near_fibonacci_level(price: float, high: float, low: float, tolerance: float = 0.005) -> Dict[str, bool]:
    """
    Quick utility to check if price is near Fibonacci levels
    
    Args:
        price: Current price
        high: Highest price
        low: Lowest price
        tolerance: Tolerance percentage
        
    Returns:
        Dictionary mapping level to boolean
    """
    fm = FibonacciManager()
    fm.calculate_retracement(high, low)
    return fm.is_at_fibonacci_level(price, tolerance)