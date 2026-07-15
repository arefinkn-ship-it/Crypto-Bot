#!/usr/bin/env python3
# ============================================================
#  HELPERS - Utility helper functions
# ============================================================

import re
from typing import Optional, Union, Any
from datetime import datetime


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert a value to float
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Float value or default
    """
    try:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Remove commas and currency symbols
            cleaned = re.sub(r'[^\d.\-]', '', value.strip())
            return float(cleaned) if cleaned else default
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """
    Safely convert a value to int
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Int value or default
    """
    try:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            cleaned = re.sub(r'[^\d\-]', '', value.strip())
            return int(cleaned) if cleaned else default
        return int(value)
    except (ValueError, TypeError):
        return default


def format_price(price: float, decimals: int = 8) -> str:
    """
    Format price with appropriate decimal places
    
    Args:
        price: Price value
        decimals: Number of decimal places
        
    Returns:
        Formatted price string
    """
    try:
        if price is None:
            return "N/A"
        return f"{price:.{decimals}f}"
    except (ValueError, TypeError):
        return "N/A"


def calculate_risk_metrics(entry: float, stop_loss: float, take_profit: float) -> dict:
    """
    Calculate risk metrics for a trade
    
    Args:
        entry: Entry price
        stop_loss: Stop loss price
        take_profit: Take profit price
        
    Returns:
        Dictionary with risk metrics
    """
    try:
        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)
        risk_reward_ratio = reward / risk if risk > 0 else 0
        
        risk_percent = (risk / entry) * 100
        reward_percent = (reward / entry) * 100
        
        return {
            'risk_amount': risk,
            'reward_amount': reward,
            'risk_reward_ratio': risk_reward_ratio,
            'risk_percent': risk_percent,
            'reward_percent': reward_percent,
            'total_risk_percent': risk_percent
        }
    except (ValueError, TypeError, ZeroDivisionError):
        return {
            'risk_amount': 0,
            'reward_amount': 0,
            'risk_reward_ratio': 0,
            'risk_percent': 0,
            'reward_percent': 0,
            'total_risk_percent': 0
        }


def get_timestamp_ms() -> int:
    """
    Get current timestamp in milliseconds
    
    Returns:
        Current timestamp in milliseconds
    """
    return int(datetime.now().timestamp() * 1000)


def safe_divide(a: float, b: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, handling division by zero
    
    Args:
        a: Numerator
        b: Denominator
        default: Default value if division by zero
        
    Returns:
        Division result or default
    """
    try:
        if b == 0:
            return default
        return a / b
    except (ValueError, TypeError, ZeroDivisionError):
        return default


def clamp(value: float, min_val: float, max_val: float) -> float:
    """
    Clamp a value between min and max
    
    Args:
        value: Value to clamp
        min_val: Minimum value
        max_val: Maximum value
        
    Returns:
        Clamped value
    """
    try:
        return max(min_val, min(value, max_val))
    except (ValueError, TypeError):
        return min_val


def is_valid_price(price: Any) -> bool:
    """
    Check if a price is valid (positive number)
    
    Args:
        price: Price to check
        
    Returns:
        True if valid, False otherwise
    """
    try:
        if price is None:
            return False
        p = float(price)
        return p > 0 and not (p == float('inf') or p == float('-inf'))
    except (ValueError, TypeError):
        return False


def normalize_symbol(symbol: str) -> str:
    """
    Normalize a trading symbol to standard format (uppercase)
    
    Args:
        symbol: Symbol to normalize
        
    Returns:
        Normalized symbol
    """
    if not symbol:
        return ""
    return symbol.upper().strip()


def truncate_string(s: str, max_length: int = 100) -> str:
    """
    Truncate a string to max_length
    
    Args:
        s: String to truncate
        max_length: Maximum length
        
    Returns:
        Truncated string
    """
    if not s:
        return ""
    if len(s) <= max_length:
        return s
    return s[:max_length] + "..."