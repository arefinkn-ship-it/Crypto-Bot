# ============================================================
#  VOLATILITY INDICATORS - Bollinger Bands, ATR
# ============================================================

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from src.indicators.base import BaseIndicator
from src.core.logger import logger


class BollingerBands(BaseIndicator):
    """
    Bollinger Bands - volatility-based bands.
    
    Parameters:
        period: int - Moving average period (default: 20)
        std_dev: float - Number of standard deviations (default: 2.0)
        column: str - Column to calculate on (default: 'close')
    """
    
    def __init__(
        self,
        period: int = 20,
        std_dev: float = 2.0,
        column: str = 'close',
        **kwargs
    ):
        super().__init__(
            name=f"BB_{period}_{std_dev}",
            params={'period': period, 'std_dev': std_dev, 'column': column}
        )
        self.period = period
        self.std_dev = std_dev
        self.column = column
        
        self.upper = None
        self.middle = None
        self.lower = None
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """Returns percentage position within bands. Stores upper, middle, lower."""
        if not self.validate_data(data, [self.column]):
            return pd.Series(index=data.index, dtype=float)
        
        self.middle = data[self.column].rolling(window=self.period).mean()
        std = data[self.column].rolling(window=self.period).std()
        
        self.upper = self.middle + (self.std_dev * std)
        self.lower = self.middle - (self.std_dev * std)
        
        # Percentage position within bands (0 = lower, 1 = upper)
        self.result = (data[self.column] - self.lower) / (self.upper - self.lower)
        return self.result
    
    def get_upper(self) -> pd.Series:
        return self.upper
    
    def get_middle(self) -> pd.Series:
        return self.middle
    
    def get_lower(self) -> pd.Series:
        return self.lower


class ATR(BaseIndicator):
    """
    Average True Range - volatility measurement.
    
    Parameters:
        period: int - ATR period (default: 14)
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
        super().__init__(name=f"ATR_{period}", params={'period': period})
        self.period = period
        self.high_col = high_col
        self.low_col = low_col
        self.close_col = close_col
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        if not self.validate_data(data, [self.high_col, self.low_col, self.close_col]):
            return pd.Series(index=data.index, dtype=float)
        
        high_low = data[self.high_col] - data[self.low_col]
        high_close = abs(data[self.high_col] - data[self.close_col].shift())
        low_close = abs(data[self.low_col] - data[self.close_col].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        tr = ranges.max(axis=1)
        
        self.result = tr.rolling(window=self.period).mean()
        return self.result