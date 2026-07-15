# ============================================================
#  TREND INDICATORS - EMA, SMA, SuperTrend, ADX
#  Fixed: pandas FutureWarning for incompatible dtype
# ============================================================

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from src.indicators.base import BaseIndicator
from src.core.logger import logger


class EMA(BaseIndicator):
    """
    Exponential Moving Average.
    
    Parameters:
        period: int - Moving average period (default: 14)
        column: str - Column to calculate on (default: 'close')
    """
    
    def __init__(self, period: int = 14, column: str = 'close', **kwargs):
        super().__init__(name=f"EMA_{period}", params={'period': period, 'column': column})
        self.period = period
        self.column = column
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        if not self.validate_data(data, [self.column]):
            return pd.Series(index=data.index, dtype=float)
        
        self.result = data[self.column].ewm(span=self.period, adjust=False).mean()
        return self.result


class SMA(BaseIndicator):
    """
    Simple Moving Average.
    
    Parameters:
        period: int - Moving average period (default: 14)
        column: str - Column to calculate on (default: 'close')
    """
    
    def __init__(self, period: int = 14, column: str = 'close', **kwargs):
        super().__init__(name=f"SMA_{period}", params={'period': period, 'column': column})
        self.period = period
        self.column = column
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        if not self.validate_data(data, [self.column]):
            return pd.Series(index=data.index, dtype=float)
        
        self.result = data[self.column].rolling(window=self.period).mean()
        return self.result


class SuperTrend(BaseIndicator):
    """
    SuperTrend indicator - volatility-adaptive trend following.
    
    Parameters:
        period: int - ATR period (default: 10)
        multiplier: float - ATR multiplier (default: 3.0)
        high_col: str - High price column (default: 'high')
        low_col: str - Low price column (default: 'low')
        close_col: str - Close price column (default: 'close')
    """
    
    def __init__(
        self,
        period: int = 10,
        multiplier: float = 3.0,
        high_col: str = 'high',
        low_col: str = 'low',
        close_col: str = 'close',
        **kwargs
    ):
        super().__init__(
            name=f"SuperTrend_{period}_{multiplier}",
            params={'period': period, 'multiplier': multiplier}
        )
        self.period = period
        self.multiplier = multiplier
        self.high_col = high_col
        self.low_col = low_col
        self.close_col = close_col
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """Calculate SuperTrend. Returns 1 for uptrend, -1 for downtrend, 0 for neutral."""
        if not self.validate_data(data, [self.high_col, self.low_col, self.close_col]):
            return pd.Series(index=data.index, dtype=float)
        
        # Calculate ATR
        high_low = data[self.high_col] - data[self.low_col]
        high_close = abs(data[self.high_col] - data[self.close_col].shift())
        low_close = abs(data[self.low_col] - data[self.close_col].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        atr = ranges.max(axis=1).rolling(window=self.period).mean()
        
        # Calculate bands
        hl2 = (data[self.high_col] + data[self.low_col]) / 2
        upper_band = hl2 + (self.multiplier * atr)
        lower_band = hl2 - (self.multiplier * atr)
        
        # Calculate SuperTrend - ensure float dtype throughout
        trend = pd.Series(0.0, index=data.index, dtype=float)  # Changed: 0.0 instead of 0
        trend.iloc[:self.period] = 0.0
        
        for i in range(self.period, len(data)):
            if data[self.close_col].iloc[i] > upper_band.iloc[i-1]:
                trend.iloc[i] = 1.0
            elif data[self.close_col].iloc[i] < lower_band.iloc[i-1]:
                trend.iloc[i] = -1.0
            else:
                trend.iloc[i] = trend.iloc[i-1]
        
        self.result = trend
        return self.result


class ADX(BaseIndicator):
    """
    Average Directional Index - measures trend strength.
    
    Parameters:
        period: int - ADX period (default: 14)
        high_col: str - High price column (default: 'high')
        low_col: str - Low price column (default: 'low')
        close_col: str - Close price column (default: 'close')
    """
    
    def __init__(
        self,
        period: int = 14,
        high_col: str = 'high',
        low_col: str = 'low',
        close_col: str = 'close',
        **kwargs
    ):
        super().__init__(name=f"ADX_{period}", params={'period': period})
        self.period = period
        self.high_col = high_col
        self.low_col = low_col
        self.close_col = close_col
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        if not self.validate_data(data, [self.high_col, self.low_col, self.close_col]):
            return pd.Series(index=data.index, dtype=float)
        
        high = data[self.high_col]
        low = data[self.low_col]
        close = data[self.close_col]
        
        # True Range
        tr = pd.concat([
            high - low,
            abs(high - close.shift()),
            abs(low - close.shift())
        ], axis=1).max(axis=1)
        
        # Directional movements - use float dtype throughout
        up_move = high - high.shift()
        down_move = low.shift() - low
        
        # Initialize with float dtype (0.0 instead of 0)
        plus_dm = pd.Series(0.0, index=data.index, dtype=float)
        minus_dm = pd.Series(0.0, index=data.index, dtype=float)
        
        # Use .loc to avoid SettingWithCopyWarning and dtype issues
        plus_dm.loc[(up_move > down_move) & (up_move > 0)] = up_move
        minus_dm.loc[(down_move > up_move) & (down_move > 0)] = down_move
        
        # Smoothed averages
        tr_smooth = tr.rolling(window=self.period).sum()
        plus_dm_smooth = plus_dm.rolling(window=self.period).sum()
        minus_dm_smooth = minus_dm.rolling(window=self.period).sum()
        
        # Calculate DI
        plus_di = 100 * (plus_dm_smooth / tr_smooth)
        minus_di = 100 * (minus_dm_smooth / tr_smooth)
        
        # DX and ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=self.period).mean()
        
        self.result = adx
        return self.result