# ============================================================
#  BASE STRATEGY - Abstract base class for all strategies
# ============================================================

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from src.core.logger import logger
from src.indicators import *


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    
    Each strategy should implement:
    - evaluate(): Returns a score (0-10) and direction (BUY/SELL/NEUTRAL)
    - get_name(): Returns the strategy name
    """
    
    def __init__(self, name: str, params: Dict[str, Any] = None):
        """
        Initialize the strategy.
        
        Args:
            name: Strategy name
            params: Strategy parameters
        """
        self.name = name
        self.params = params or {}
        self.last_score = 0
        self.last_direction = 'NEUTRAL'
        self.last_details = {}
    
    @abstractmethod
    def evaluate(self, data: pd.DataFrame) -> Tuple[float, str, Dict]:
        """
        Evaluate the strategy on the given data.
        
        Args:
            data: DataFrame with OHLCV data and indicators
            
        Returns:
            Tuple of (score, direction, details)
            - score: 0-10 float
            - direction: 'BUY', 'SELL', or 'NEUTRAL'
            - details: Dict with additional information
        """
        pass
    
    def get_name(self) -> str:
        """Get the strategy name."""
        return self.name
    
    def get_last_result(self) -> Dict:
        """Get the last evaluation result."""
        return {
            'score': self.last_score,
            'direction': self.last_direction,
            'details': self.last_details
        }
    
    def __repr__(self):
        return f"{self.name}({self.params})"


class StrategyManager:
    """
    Manages multiple strategies and calculates combined scores.
    """
    
    def __init__(self, strategies: list = None):
        """
        Initialize with a list of strategies.
        
        Args:
            strategies: List of BaseStrategy instances
        """
        self.strategies = strategies or []
        self.results = {}
        self.weights = {}
    
    def add_strategy(self, strategy: BaseStrategy, weight: float = 1.0):
        """
        Add a strategy with a weight.
        
        Args:
            strategy: BaseStrategy instance
            weight: Weight for this strategy (default: 1.0)
        """
        self.strategies.append(strategy)
        self.weights[strategy.get_name()] = weight
    
    def evaluate_all(self, data: pd.DataFrame) -> Dict[str, Dict]:
        """
        Evaluate all strategies on the data.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            Dictionary of {strategy_name: result}
        """
        self.results = {}
        
        for strategy in self.strategies:
            try:
                score, direction, details = strategy.evaluate(data)
                self.results[strategy.get_name()] = {
                    'score': score,
                    'direction': direction,
                    'details': details
                }
            except Exception as e:
                logger.error(f"Error evaluating {strategy.get_name()}: {e}")
                self.results[strategy.get_name()] = {
                    'score': 0,
                    'direction': 'NEUTRAL',
                    'details': {'error': str(e)}
                }
        
        return self.results
    
    def get_combined_score(self) -> Dict:
        """
        Calculate combined score and direction from all strategies.
        
        Returns:
            Dictionary with combined results:
            - total_score: Weighted average score (0-10)
            - direction: 'BUY', 'SELL', or 'NEUTRAL'
            - confidence: 'HIGH', 'MEDIUM', or 'LOW'
            - strategy_results: Individual strategy results
        """
        if not self.results:
            return {
                'total_score': 0,
                'direction': 'NEUTRAL',
                'confidence': 'LOW',
                'strategy_results': {}
            }
        
        total_weight = sum(self.weights.values())
        if total_weight == 0:
            total_weight = len(self.strategies)
        
        weighted_score = 0
        direction_votes = {'BUY': 0, 'SELL': 0, 'NEUTRAL': 0}
        
        for name, result in self.results.items():
            weight = self.weights.get(name, 1.0)
            weighted_score += result['score'] * weight
            direction_votes[result['direction']] += weight
        
        total_score = weighted_score / total_weight
        
        # Determine direction by weighted votes
        if direction_votes['BUY'] > direction_votes['SELL']:
            direction = 'BUY'
        elif direction_votes['SELL'] > direction_votes['BUY']:
            direction = 'SELL'
        else:
            direction = 'NEUTRAL'
        
        # Determine confidence
        if total_score >= 8 and direction != 'NEUTRAL':
            confidence = 'HIGH'
        elif total_score >= 5 and direction != 'NEUTRAL':
            confidence = 'MEDIUM'
        else:
            confidence = 'LOW'
        
        return {
            'total_score': round(total_score, 2),
            'direction': direction,
            'confidence': confidence,
            'strategy_results': self.results
        }