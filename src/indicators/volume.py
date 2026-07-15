# ============================================================
#  VOLUME INDICATORS - VWAP, OBV
#  Fixed: pandas FutureWarning for incompatible dtype
# ============================================================

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from src.indicators.base import BaseIndicator
from src.core.logger import logger


class VWAP(BaseIndicator):
    """
    Volume-Weighted Average Price - intraday fair value.
    
    Parameters:
        high_col: str - High price column (default: 'high')
        low_col: str - Low price column (default: 'low')
        close_col: str - Close price column (default: 'close')
        volume_col: str - Volume column (default: 'volume')
    """
    
    def __init__(
        self,
        high_col: str = 'high',
        low_col: str = 'low',
        close_col: str = 'close',
        volume_col: str = 'volume',
        **kwargs
    ):
        super().__init__(name="VWAP", params={})
        self.high_col = high_col
        self.low_col = low_col
        self.close_col = close_col
        self.volume_col = volume_col
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        if not self.validate_data(data, [self.high_col, self.low_col, self.close_col, self.volume_col]):
            return pd.Series(index=data.index, dtype=float)
        
        typical_price = (data[self.high_col] + data[self.low_col] + data[self.close_col]) / 3
        cumulative_tp_vol = (typical_price * data[self.volume_col]).cumsum()
        cumulative_vol = data[self.volume_col].cumsum()
        
        self.result = cumulative_tp_vol / cumulative_vol
        return self.result


class OBV(BaseIndicator):
    """
    On-Balance Volume - volume-based momentum.
    
    Parameters:
        close_col: str - Close price column (default: 'close')
        volume_col: str - Volume column (default: 'volume')
    """
    
    def __init__(
        self,
        close_col: str = 'close',
        volume_col: str = 'volume',
        **kwargs
    ):
        super().__init__(name="OBV", params={})
        self.close_col = close_col
        self.volume_col = volume_col
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        if not self.validate_data(data, [self.close_col, self.volume_col]):
            return pd.Series(index=data.index, dtype=float)
        
        # Initialize with float dtype (0.0 instead of 0)
        obv = pd.Series(0.0, index=data.index, dtype=float)
        
        for i in range(1, len(data)):
            if data[self.close_col].iloc[i] > data[self.close_col].iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + data[self.volume_col].iloc[i]
            elif data[self.close_col].iloc[i] < data[self.close_col].iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - data[self.volume_col].iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        
        self.result = obv
        return self.result