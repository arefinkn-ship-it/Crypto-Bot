# ============================================================
#  BASE INDICATOR - Abstract base class for all indicators
# ============================================================

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
from src.core.logger import logger


class BaseIndicator(ABC):
    """
    Abstract base class for all technical indicators.
    
    All indicators should inherit from this class and implement
    the calculate() method.
    """
    
    def __init__(self, name: str, params: Dict[str, Any] = None):
        """
        Initialize the indicator.
        
        Args:
            name: Name of the indicator (e.g., 'RSI', 'MACD')
            params: Dictionary of parameters for the indicator
        """
        self.name = name
        self.params = params or {}
        self.result = None
    
    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        Calculate the indicator values.
        
        Args:
            data: DataFrame with OHLCV data (must include 'close' at minimum)
            
        Returns:
            Series with the indicator values
        """
        pass
    
    def validate_data(self, data: pd.DataFrame, required_columns: List[str]) -> bool:
        """
        Validate that the data contains required columns.
        
        Args:
            data: DataFrame to validate
            required_columns: List of required column names
            
        Returns:
            True if valid, False otherwise
        """
        missing = [col for col in required_columns if col not in data.columns]
        if missing:
            logger.error(f"Missing required columns for {self.name}: {missing}")
            return False
        return True
    
    def get_result(self) -> Optional[pd.Series]:
        """Get the calculated indicator result."""
        return self.result
    
    def __repr__(self):
        return f"{self.name}({self.params})"


class IndicatorManager:
    """
    Manages multiple indicators for a given dataset.
    Useful for calculating many indicators at once.
    """
    
    def __init__(self):
        self.indicators = {}
        self.results = {}
    
    def register(self, indicator: BaseIndicator):
        """Register an indicator to be calculated."""
        self.indicators[indicator.name] = indicator
    
    def calculate_all(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        Calculate all registered indicators on the data.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            Dictionary of {indicator_name: result_series}
        """
        self.results = {}
        for name, indicator in self.indicators.items():
            try:
                self.results[name] = indicator.calculate(data)
            except Exception as e:
                logger.error(f"Error calculating {name}: {e}")
                self.results[name] = pd.Series(index=data.index, dtype=float)
        
        return self.results
    
    def get_results(self) -> Dict[str, pd.Series]:
        """Get all calculated results."""
        return self.results