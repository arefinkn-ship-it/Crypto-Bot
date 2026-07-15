# ============================================================
#  MOMENTUM INDICATORS - RSI, MACD, Stochastic
# ============================================================

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from src.indicators.base import BaseIndicator
from src.core.logger import logger


class RSI(BaseIndicator):
    """
    Relative Strength Index.
    
    Parameters:
        period: int - RSI period (default: 14)
        column: str - Column to calculate on (default: 'close')
    """
    
    def __init__(self, period: int = 14, column: str = 'close', **kwargs):
        super().__init__(name=f"RSI_{period}", params={'period': period, 'column': column})
        self.period = period
        self.column = column
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        if not self.validate_data(data, [self.column]):
            return pd.Series(index=data.index, dtype=float)
        
        delta = data[self.column].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        self.result = rsi
        return self.result


class MACD(BaseIndicator):
    """
    Moving Average Convergence Divergence.
    
    Parameters:
        fast: int - Fast EMA period (default: 12)
        slow: int - Slow EMA period (default: 26)
        signal: int - Signal line period (default: 9)
        column: str - Column to calculate on (default: 'close')
    """
    
    def __init__(
        self,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        column: str = 'close',
        **kwargs
    ):
        super().__init__(
            name=f"MACD_{fast}_{slow}_{signal}",
            params={'fast': fast, 'slow': slow, 'signal': signal, 'column': column}
        )
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.column = column
        self.macd_line = None
        self.signal_line = None
        self.histogram = None
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """Returns MACD histogram. Also stores macd_line and signal_line."""
        if not self.validate_data(data, [self.column]):
            return pd.Series(index=data.index, dtype=float)
        
        ema_fast = data[self.column].ewm(span=self.fast, adjust=False).mean()
        ema_slow = data[self.column].ewm(span=self.slow, adjust=False).mean()
        
        self.macd_line = ema_fast - ema_slow
        self.signal_line = self.macd_line.ewm(span=self.signal, adjust=False).mean()
        self.histogram = self.macd_line - self.signal_line
        
        self.result = self.histogram
        return self.result
    
    def get_macd(self) -> pd.Series:
        return self.macd_line
    
    def get_signal(self) -> pd.Series:
        return self.signal_line
    
    def get_histogram(self) -> pd.Series:
        return self.histogram


class Stochastic(BaseIndicator):
    """
    Stochastic Oscillator.
    
    Parameters:
        k_period: int - %K period (default: 14)
        d_period: int - %D period (default: 3)
        smooth: int - Smoothing period (default: 3)
        high_col: str - High price column (default: 'high')
        low_col: str - Low price column (default: 'low')
        close_col: str - Close price column (default: 'close')
    """
    
    def __init__(
        self,
        k_period: int = 14,
        d_period: int = 3,
        smooth: int = 3,
        high_col: str = 'high',
        low_col: str = 'low',
        close_col: str = 'close',
        **kwargs
    ):
        super().__init__(
            name=f"Stoch_{k_period}_{d_period}_{smooth}",
            params={'k_period': k_period, 'd_period': d_period, 'smooth': smooth}
        )
        self.k_period = k_period
        self.d_period = d_period
        self.smooth = smooth
        self.high_col = high_col
        self.low_col = low_col
        self.close_col = close_col
        
        self.k_line = None
        self.d_line = None
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """Returns %D (signal) line. Stores %K as well."""
        if not self.validate_data(data, [self.high_col, self.low_col, self.close_col]):
            return pd.Series(index=data.index, dtype=float)
        
        low_min = data[self.low_col].rolling(window=self.k_period).min()
        high_max = data[self.high_col].rolling(window=self.k_period).max()
        
        self.k_line = 100 * ((data[self.close_col] - low_min) / (high_max - low_min))
        self.d_line = self.k_line.rolling(window=self.d_period).mean()
        
        self.result = self.d_line
        return self.result
    
    def get_k(self) -> pd.Series:
        return self.k_line
    
    def get_d(self) -> pd.Series:
        return self.d_line