# ============================================================
#  STRATEGY: MEAN REVERSION - Increased Scoring Weights
#  Changes: Higher raw scores for stronger signals
# ============================================================

import sys
from pathlib import Path
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import numpy as np
import ta

from src.signals.signal_combiner import StrategyResult


# ------------------------------------------------------------
#  INDICATORS
# ------------------------------------------------------------
def add_mean_reversion_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["rsi"] = ta.momentum.rsi(df["close"], window=14)

    bb = ta.volatility.BollingerBands(df["close"], window=20, window_dev=2.0)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_lower"] = bb.bollinger_lband()
    band_width = (df["bb_upper"] - df["bb_lower"]).replace(0, np.nan)
    df["bb_position"] = (df["close"] - df["bb_lower"]) / band_width

    df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
    df["adx"] = ta.trend.adx(df["high"], df["low"], df["close"], window=14)
    df["volume_sma20"] = df["volume"].rolling(20).mean()

    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    df["vwap"] = (typical_price * df["volume"]).rolling(20).sum() / df["volume"].rolling(20).sum()

    return df


def _find_swing_lows(series: pd.Series, order: int = 3) -> pd.Series:
    is_swing_low = pd.Series(False, index=series.index)
    for i in range(order, len(series) - order):
        window = series.iloc[i - order: i + order + 1]
        if series.iloc[i] == window.min() and (window == series.iloc[i]).sum() == 1:
            is_swing_low.iloc[i] = True
    return is_swing_low


def _find_swing_highs(series: pd.Series, order: int = 3) -> pd.Series:
    is_swing_high = pd.Series(False, index=series.index)
    for i in range(order, len(series) - order):
        window = series.iloc[i - order: i + order + 1]
        if series.iloc[i] == window.max() and (window == series.iloc[i]).sum() == 1:
            is_swing_high.iloc[i] = True
    return is_swing_high


def _detect_bullish_divergence(df: pd.DataFrame, lookback: int = 30) -> bool:
    window = df.iloc[-lookback:]
    swing_low_mask = _find_swing_lows(window["low"], order=3)
    swing_idxs = window.index[swing_low_mask]
    if len(swing_idxs) < 2:
        return False
    i1, i2 = swing_idxs[-2], swing_idxs[-1]
    price_lower_low = window.loc[i2, "low"] < window.loc[i1, "low"]
    rsi_higher_low = window.loc[i2, "rsi"] > window.loc[i1, "rsi"]
    return bool(price_lower_low and rsi_higher_low)


def _detect_bearish_divergence(df: pd.DataFrame, lookback: int = 30) -> bool:
    window = df.iloc[-lookback:]
    swing_high_mask = _find_swing_highs(window["high"], order=3)
    swing_idxs = window.index[swing_high_mask]
    if len(swing_idxs) < 2:
        return False
    i1, i2 = swing_idxs[-2], swing_idxs[-1]
    price_higher_high = window.loc[i2, "high"] > window.loc[i1, "high"]
    rsi_lower_high = window.loc[i2, "rsi"] < window.loc[i1, "rsi"]
    return bool(price_higher_high and rsi_lower_high)


# ------------------------------------------------------------
#  STRATEGY SCORING - INCREASED WEIGHTS
# ------------------------------------------------------------
MEAN_REVERSION_MAX_SCORE = 10.0
ADX_TREND_GATE = 25
ADX_GATE_MULTIPLIER = 0.3


def mean_reversion(df: pd.DataFrame, min_candles: int = 50) -> StrategyResult:
    if len(df) < min_candles:
        return StrategyResult(
            name="mean_reversion",
            buy_score_raw=0.0, sell_score_raw=0.0,
            max_possible=MEAN_REVERSION_MAX_SCORE,
            reasons_sell=["Insufficient history"],
        )

    df = add_mean_reversion_indicators(df)
    last = df.iloc[-1]

    required = ["rsi", "bb_upper", "bb_lower", "bb_position", "atr", "adx", "vwap", "volume_sma20"]
    if last[required].isna().any():
        return StrategyResult(
            name="mean_reversion",
            buy_score_raw=0.0, sell_score_raw=0.0,
            max_possible=MEAN_REVERSION_MAX_SCORE,
            reasons_sell=["Indicator warm-up incomplete"],
        )

    close, rsi_val = last["close"], last["rsi"]
    bb_upper, bb_lower = last["bb_upper"], last["bb_lower"]
    atr_val, adx_val, vwap = last["atr"], last["adx"], last["vwap"]

    buy_score, sell_score = 0.0, 0.0
    buy_reasons, sell_reasons = [], []

    # --- RSI extremity (INCREASED WEIGHTS) ---
    if rsi_val < 30:
        buy_score += 5  # Was 4
        buy_reasons.append(f"RSI {rsi_val:.1f} deeply oversold")
    elif rsi_val < 35:
        buy_score += 3  # Was 2
        buy_reasons.append(f"RSI {rsi_val:.1f} approaching oversold")

    if rsi_val > 70:
        sell_score += 5  # Was 4
        sell_reasons.append(f"RSI {rsi_val:.1f} deeply overbought")
    elif rsi_val > 65:
        sell_score += 3  # Was 2
        sell_reasons.append(f"RSI {rsi_val:.1f} approaching overbought")

    # --- ATR-based BB proximity (INCREASED WEIGHT) ---
    dist_to_lower_atr = (close - bb_lower) / atr_val if atr_val > 0 else np.inf
    dist_to_upper_atr = (bb_upper - close) / atr_val if atr_val > 0 else np.inf

    if buy_score > 0 and dist_to_lower_atr < 0.5:
        buy_score += 3  # Was 2
        buy_reasons.append(f"Price within 0.5x ATR of lower BB")
    if sell_score > 0 and dist_to_upper_atr < 0.5:
        sell_score += 3  # Was 2
        sell_reasons.append(f"Price within 0.5x ATR of upper BB")

    # --- VWAP anchor (INCREASED WEIGHT) ---
    if buy_score > 0 and close < vwap:
        buy_score += 3  # Was 2
        buy_reasons.append("Price below VWAP (undervalued)")
    if sell_score > 0 and close > vwap:
        sell_score += 3  # Was 2
        sell_reasons.append("Price above VWAP (overvalued)")

    # --- Divergence (INCREASED WEIGHT) ---
    if buy_score > 0 and _detect_bullish_divergence(df):
        buy_score += 3  # Was 2
        buy_reasons.append("Bullish RSI divergence (price lower low, RSI higher low)")
    if sell_score > 0 and _detect_bearish_divergence(df):
        sell_score += 3  # Was 2
        sell_reasons.append("Bearish RSI divergence (price higher high, RSI lower high)")

    # --- ADX hard gate ---
    if adx_val > ADX_TREND_GATE:
        if buy_score > 0:
            buy_score *= ADX_GATE_MULTIPLIER
            buy_reasons.append(f"ADX {adx_val:.1f} trending - discounted")
        if sell_score > 0:
            sell_score *= ADX_GATE_MULTIPLIER
            sell_reasons.append(f"ADX {adx_val:.1f} trending - discounted")

    return StrategyResult(
        name="mean_reversion",
        buy_score_raw=round(min(buy_score, MEAN_REVERSION_MAX_SCORE), 2),
        sell_score_raw=round(min(sell_score, MEAN_REVERSION_MAX_SCORE), 2),
        max_possible=MEAN_REVERSION_MAX_SCORE,
        reasons_buy=buy_reasons,
        reasons_sell=sell_reasons,
    )


if __name__ == "__main__":
    np.random.seed(11)
    n = 60
    base = 100 + 3 * np.sin(np.linspace(0, 6 * np.pi, n)) + np.random.normal(0, 0.2, n)
    base[-5:] -= np.array([0.5, 1.2, 2.0, 2.8, 3.5])
    close = base
    high = close + np.random.uniform(0.1, 0.3, n)
    low = close - np.random.uniform(0.1, 0.3, n)
    open_ = close - np.random.uniform(-0.15, 0.15, n)
    volume = np.random.uniform(1000, 1500, n)
    df = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume})

    result = mean_reversion(df)
    print("Direction:", "BUY" if result.buy_score_raw > result.sell_score_raw else "SELL")
    print(f"Buy: {result.buy_score_raw}/{result.max_possible}")
    print(f"Sell: {result.sell_score_raw}/{result.max_possible}")