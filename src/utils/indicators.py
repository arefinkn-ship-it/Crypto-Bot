#!/usr/bin/env python3
# ============================================================
#  TECHNICAL INDICATORS - Utility functions for TA calculations
# ============================================================

import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict, List
import ta

from src.core.logger import logger


def calculate_indicators(data: pd.DataFrame, add_all: bool = True) -> pd.DataFrame:
    """
    Calculate multiple technical indicators for a given DataFrame
    
    Args:
        data: DataFrame with OHLCV data
        add_all: If True, add all indicators; if False, only add RSI, MACD, BB
        
    Returns:
        DataFrame with added indicator columns
    """
    df = data.copy()
    
    # Ensure we have required columns
    if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume']):
        logger.warning("Missing required columns for indicator calculation")
        return df
    
    try:
        # Basic indicators
        df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
        df['rsi_7'] = ta.momentum.RSIIndicator(df['close'], window=7).rsi()
        df['rsi_21'] = ta.momentum.RSIIndicator(df['close'], window=21).rsi()
        
        # MACD
        macd = ta.trend.MACD(df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()
        
        # Bollinger Bands
        bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
        df['bb_high'] = bb.bollinger_hband()
        df['bb_mid'] = bb.bollinger_mavg()
        df['bb_low'] = bb.bollinger_lband()
        df['bb_width'] = bb.bollinger_wband()
        df['bb_percent'] = bb.bollinger_pband()
        
        # Moving Averages
        df['ema_9'] = ta.trend.EMAIndicator(df['close'], window=9).ema_indicator()
        df['ema_20'] = ta.trend.EMAIndicator(df['close'], window=20).ema_indicator()
        df['ema_50'] = ta.trend.EMAIndicator(df['close'], window=50).ema_indicator()
        df['ema_200'] = ta.trend.EMAIndicator(df['close'], window=200).ema_indicator()
        
        df['sma_20'] = ta.trend.SMAIndicator(df['close'], window=20).sma_indicator()
        df['sma_50'] = ta.trend.SMAIndicator(df['close'], window=50).sma_indicator()
        df['sma_200'] = ta.trend.SMAIndicator(df['close'], window=200).sma_indicator()
        
        # ATR
        df['atr'] = ta.volatility.AverageTrueRange(
            df['high'], df['low'], df['close'], window=14
        ).average_true_range()
        
        # Stochastic
        stoch = ta.momentum.StochasticOscillator(
            df['high'], df['low'], df['close'], window=14, smooth_window=3
        )
        df['stoch_k'] = stoch.stoch()
        df['stoch_d'] = stoch.stoch_signal()
        
        # Additional indicators if requested
        if add_all:
            # Volume indicators
            df['volume_sma'] = ta.trend.SMAIndicator(df['volume'], window=20).sma_indicator()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            # MFI (Money Flow Index)
            df['mfi'] = ta.volume.MFIIndicator(
                df['high'], df['low'], df['close'], df['volume'], window=14
            ).money_flow_index()
            
            # ADX
            adx = ta.trend.ADXIndicator(df['high'], df['low'], df['close'], window=14)
            df['adx'] = adx.adx()
            df['adx_pos'] = adx.adx_pos()
            df['adx_neg'] = adx.adx_neg()
            
            # Williams %R
            df['williams_r'] = ta.momentum.WilliamsRIndicator(
                df['high'], df['low'], df['close'], lbp=14
            ).williams_r()
            
            # CCI
            df['cci'] = ta.trend.CCIIndicator(
                df['high'], df['low'], df['close'], window=20
            ).cci()
            
            # ROC
            df['roc'] = ta.momentum.ROCCIndicator(df['close'], window=12).roc()
            
            # OBV
            df['obv'] = ta.volume.OnBalanceVolumeIndicator(
                df['close'], df['volume']
            ).on_balance_volume()
            
            # VWAP (simplified)
            df['vwap'] = (df['volume'] * df['close']).cumsum() / df['volume'].cumsum()
            
        return df
        
    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")
        return df


def calculate_rsi(data: pd.DataFrame, window: int = 14) -> pd.Series:
    """Calculate RSI indicator"""
    try:
        return ta.momentum.RSIIndicator(data['close'], window=window).rsi()
    except Exception as e:
        logger.error(f"Error calculating RSI: {e}")
        return pd.Series()


def calculate_macd(data: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate MACD indicator"""
    try:
        macd = ta.trend.MACD(data['close'])
        return macd.macd(), macd.macd_signal(), macd.macd_diff()
    except Exception as e:
        logger.error(f"Error calculating MACD: {e}")
        return pd.Series(), pd.Series(), pd.Series()


def calculate_bollinger_bands(data: pd.DataFrame, window: int = 20, dev: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Bollinger Bands"""
    try:
        bb = ta.volatility.BollingerBands(data['close'], window=window, window_dev=dev)
        return bb.bollinger_hband(), bb.bollinger_mavg(), bb.bollinger_lband()
    except Exception as e:
        logger.error(f"Error calculating Bollinger Bands: {e}")
        return pd.Series(), pd.Series(), pd.Series()


def calculate_ema(data: pd.DataFrame, window: int = 20) -> pd.Series:
    """Calculate EMA"""
    try:
        return ta.trend.EMAIndicator(data['close'], window=window).ema_indicator()
    except Exception as e:
        logger.error(f"Error calculating EMA: {e}")
        return pd.Series()


def calculate_sma(data: pd.DataFrame, window: int = 20) -> pd.Series:
    """Calculate SMA"""
    try:
        return ta.trend.SMAIndicator(data['close'], window=window).sma_indicator()
    except Exception as e:
        logger.error(f"Error calculating SMA: {e}")
        return pd.Series()


def calculate_atr(data: pd.DataFrame, window: int = 14) -> pd.Series:
    """Calculate ATR"""
    try:
        return ta.volatility.AverageTrueRange(
            data['high'], data['low'], data['close'], window=window
        ).average_true_range()
    except Exception as e:
        logger.error(f"Error calculating ATR: {e}")
        return pd.Series()


def calculate_stochastic(data: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    """Calculate Stochastic Oscillator"""
    try:
        stoch = ta.momentum.StochasticOscillator(
            data['high'], data['low'], data['close'], window=14, smooth_window=3
        )
        return stoch.stoch(), stoch.stoch_signal()
    except Exception as e:
        logger.error(f"Error calculating Stochastic: {e}")
        return pd.Series(), pd.Series()


def calculate_ichimoku(data: pd.DataFrame) -> Dict[str, pd.Series]:
    """
    Calculate Ichimoku Cloud components
    
    Returns:
        Dictionary with tenkan_sen, kijun_sen, senkou_a, senkou_b, chikou_span
    """
    try:
        # Tenkan-sen (Conversion Line): (9-period high + 9-period low)/2
        tenkan_sen = ((data['high'].rolling(window=9).max() + 
                       data['low'].rolling(window=9).min()) / 2)
        
        # Kijun-sen (Base Line): (26-period high + 26-period low)/2
        kijun_sen = ((data['high'].rolling(window=26).max() + 
                      data['low'].rolling(window=26).min()) / 2)
        
        # Senkou Span A (Leading Span A): (Tenkan-sen + Kijun-sen)/2 shifted forward 26 periods
        senkou_a = ((tenkan_sen + kijun_sen) / 2).shift(26)
        
        # Senkou Span B (Leading Span B): (52-period high + 52-period low)/2 shifted forward 26 periods
        senkou_b = ((data['high'].rolling(window=52).max() + 
                     data['low'].rolling(window=52).min()) / 2).shift(26)
        
        # Chikou Span (Lagging Span): Close shifted backwards 26 periods
        chikou_span = data['close'].shift(-26)
        
        return {
            'tenkan_sen': tenkan_sen,
            'kijun_sen': kijun_sen,
            'senkou_a': senkou_a,
            'senkou_b': senkou_b,
            'chikou_span': chikou_span
        }
    except Exception as e:
        logger.error(f"Error calculating Ichimoku: {e}")
        return {}


def calculate_volume_profile(data: pd.DataFrame, num_bins: int = 20) -> Dict:
    """
    Calculate volume profile (volume at price levels)
    
    Args:
        data: DataFrame with 'high', 'low', 'close', 'volume' columns
        num_bins: Number of price bins
        
    Returns:
        Dictionary with volume profile data
    """
    try:
        price_range = data['high'].max() - data['low'].min()
        bin_size = price_range / num_bins
        
        bins = np.linspace(data['low'].min(), data['high'].max(), num_bins + 1)
        volume_profile = np.zeros(num_bins)
        
        for _, row in data.iterrows():
            low_idx = int((row['low'] - bins[0]) / bin_size)
            high_idx = int((row['high'] - bins[0]) / bin_size)
            
            for i in range(max(0, low_idx), min(num_bins, high_idx + 1)):
                volume_profile[i] += row['volume'] / (high_idx - low_idx + 1)
        
        # Find POC (Point of Control) - highest volume level
        poc_idx = np.argmax(volume_profile)
        poc_price = (bins[poc_idx] + bins[poc_idx + 1]) / 2
        
        return {
            'bins': bins,
            'volume_profile': volume_profile,
            'poc_price': poc_price,
            'poc_volume': volume_profile[poc_idx],
            'value_area_high': None,
            'value_area_low': None
        }
    except Exception as e:
        logger.error(f"Error calculating volume profile: {e}")
        return {}


def calculate_vwap(data: pd.DataFrame) -> pd.Series:
    """
    Calculate Volume Weighted Average Price (VWAP)
    
    Args:
        data: DataFrame with 'close' and 'volume' columns
        
    Returns:
        Series with VWAP values
    """
    try:
        return (data['volume'] * data['close']).cumsum() / data['volume'].cumsum()
    except Exception as e:
        logger.error(f"Error calculating VWAP: {e}")
        return pd.Series()


def get_donchian_channels(data: pd.DataFrame, period: int = 20) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Donchian Channels
    
    Args:
        data: DataFrame with 'high' and 'low' columns
        period: Lookback period
        
    Returns:
        Tuple of (upper, middle, lower) channels
    """
    try:
        upper = data['high'].rolling(window=period).max()
        lower = data['low'].rolling(window=period).min()
        middle = (upper + lower) / 2
        return upper, middle, lower
    except Exception as e:
        logger.error(f"Error calculating Donchian Channels: {e}")
        return pd.Series(), pd.Series(), pd.Series()