# ============================================================
#  STRATEGY: TREND FOLLOWING - Increased Scoring Weights
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
from src.core.config import config


# ------------------------------------------------------------
#  INDICATORS
# ------------------------------------------------------------
def add_trend_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ema_20"] = ta.trend.ema_indicator(df["close"], window=20)
    df["ema_50"] = ta.trend.ema_indicator(df["close"], window=50)
    df["ema_200"] = ta.trend.ema_indicator(df["close"], window=200)
    df["adx"] = ta.trend.adx(df["high"], df["low"], df["close"], window=14)
    df["rsi"] = ta.momentum.rsi(df["close"], window=14)
    df["volume_sma20"] = df["volume"].rolling(20).mean()

    supertrend, direction = _supertrend(df, period=10, multiplier=3.0)
    df["supertrend"] = supertrend
    df["supertrend_dir"] = direction
    return df


def _supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0):
    atr = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=period)
    hl2 = (df["high"] + df["low"]) / 2
    upper_band = hl2 + multiplier * atr
    lower_band = hl2 - multiplier * atr

    final_upper = upper_band.copy()
    final_lower = lower_band.copy()
    direction = pd.Series(1, index=df.index)
    supertrend = pd.Series(np.nan, index=df.index)

    for i in range(1, len(df)):
        if (upper_band.iloc[i] < final_upper.iloc[i - 1]) or (df["close"].iloc[i - 1] > final_upper.iloc[i - 1]):
            final_upper.iloc[i] = upper_band.iloc[i]
        else:
            final_upper.iloc[i] = final_upper.iloc[i - 1]

        if (lower_band.iloc[i] > final_lower.iloc[i - 1]) or (df["close"].iloc[i - 1] < final_lower.iloc[i - 1]):
            final_lower.iloc[i] = lower_band.iloc[i]
        else:
            final_lower.iloc[i] = final_lower.iloc[i - 1]

        if df["close"].iloc[i] > final_upper.iloc[i - 1]:
            direction.iloc[i] = 1
        elif df["close"].iloc[i] < final_lower.iloc[i - 1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]

        supertrend.iloc[i] = final_lower.iloc[i] if direction.iloc[i] == 1 else final_upper.iloc[i]

    return supertrend, direction


# ------------------------------------------------------------
#  STRATEGY SCORING - INCREASED WEIGHTS
# ------------------------------------------------------------
TREND_FOLLOWING_MAX_SCORE = 10.0


def trend_following(df: pd.DataFrame, min_candles: int = 200) -> StrategyResult:
    if len(df) < min_candles:
        return StrategyResult(
            name="trend_following",
            buy_score_raw=0.0, sell_score_raw=0.0,
            max_possible=TREND_FOLLOWING_MAX_SCORE,
            reasons_sell=["Insufficient history for EMA200"],
        )

    df = add_trend_indicators(df)
    last = df.iloc[-1]
    close_val = last["close"]

    required = ["ema_20", "ema_50", "ema_200", "adx", "supertrend_dir", "rsi", "volume_sma20"]
    if last[required].isna().any():
        return StrategyResult(
            name="trend_following",
            buy_score_raw=0.0, sell_score_raw=0.0,
            max_possible=TREND_FOLLOWING_MAX_SCORE,
            reasons_sell=["Indicator warm-up incomplete"],
        )

    ema20, ema50, ema200 = last["ema_20"], last["ema_50"], last["ema_200"]
    adx_val, st_dir, rsi_val = last["adx"], last["supertrend_dir"], last["rsi"]
    vol, vol_avg = last["volume"], last["volume_sma20"]

    buy_score, sell_score = 0.0, 0.0
    buy_reasons, sell_reasons = [], []

    # --- EMA alignment (INCREASED WEIGHTS) ---
    if close_val > ema20 > ema50 > ema200:
        buy_score += 5  # Was 4
        buy_reasons.append("Strong uptrend: Price > EMA20 > EMA50 > EMA200")
    elif close_val > ema20 > ema50:
        buy_score += 3  # Was 2
        buy_reasons.append("Moderate uptrend: Price > EMA20 > EMA50")

    if close_val < ema20 < ema50 < ema200:
        sell_score += 5  # Was 4
        sell_reasons.append("Strong downtrend: Price < EMA20 < EMA50 < EMA200")
    elif close_val < ema20 < ema50:
        sell_score += 3  # Was 2
        sell_reasons.append("Moderate downtrend: Price < EMA20 < EMA50")

    # --- SuperTrend (INCREASED WEIGHT) ---
    if st_dir == 1:
        buy_score += 4  # Was 3
        buy_reasons.append("SuperTrend bullish")
    elif st_dir == -1:
        sell_score += 4  # Was 3
        sell_reasons.append("SuperTrend bearish")

    # --- ADX (INCREASED WEIGHT) ---
    if adx_val > 25:
        if buy_score > sell_score and buy_score > 0:
            buy_score += 3  # Was 2
            buy_reasons.append(f"ADX {adx_val:.1f} confirms trend strength")
        elif sell_score > buy_score and sell_score > 0:
            sell_score += 3  # Was 2
            sell_reasons.append(f"ADX {adx_val:.1f} confirms trend strength")

    # --- Long-term bias (INCREASED WEIGHT) ---
    if close_val > ema200:
        buy_score += 2  # Was 1
        buy_reasons.append("Price above EMA200")
    elif close_val < ema200:
        sell_score += 2  # Was 1
        sell_reasons.append("Price below EMA200")

    # --- Volume (informational only) ---
    if vol > vol_avg * 1.5:
        if buy_score > sell_score:
            buy_reasons.append("Volume spike confirms trend")
        elif sell_score > buy_score:
            sell_reasons.append("Volume spike confirms trend")

    # --- Trend exhaustion dampener ---
    if buy_score > sell_score and rsi_val > 75:
        buy_score *= 0.7
        buy_reasons.append(f"RSI {rsi_val:.1f} overbought - dampened")
    elif sell_score > buy_score and rsi_val < 25:
        sell_score *= 0.7
        sell_reasons.append(f"RSI {rsi_val:.1f} oversold - dampened")

    return StrategyResult(
        name="trend_following",
        buy_score_raw=round(min(buy_score, TREND_FOLLOWING_MAX_SCORE), 2),
        sell_score_raw=round(min(sell_score, TREND_FOLLOWING_MAX_SCORE), 2),
        max_possible=TREND_FOLLOWING_MAX_SCORE,
        reasons_buy=buy_reasons,
        reasons_sell=sell_reasons,
    )


if __name__ == "__main__":
    np.random.seed(42)
    n = 250
    close = 100 + np.cumsum(np.random.normal(0.15, 1.0, n))
    high = close + np.random.uniform(0.1, 1.0, n)
    low = close - np.random.uniform(0.1, 1.0, n)
    open_ = close - np.random.uniform(-0.5, 0.5, n)
    volume = np.random.uniform(1000, 5000, n)
    volume[-1] *= 2.0
    df = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume})

    result = trend_following(df)
    print("Direction:", "BUY" if result.buy_score_raw > result.sell_score_raw else "SELL")
    print(f"Buy: {result.buy_score_raw}/{result.max_possible}")
    print(f"Sell: {result.sell_score_raw}/{result.max_possible}")