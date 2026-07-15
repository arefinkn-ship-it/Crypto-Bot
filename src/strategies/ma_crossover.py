# ============================================================
#  Fix: Add project root to path for self-test
# ============================================================
import sys
from pathlib import Path
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# ============================================================
#  STRATEGY: MA CROSSOVER - Reference implementation
#  Same pattern as trend_following.py / breakout.py
# ============================================================

import pandas as pd
import numpy as np
import ta

from src.signals.signal_combiner import StrategyResult


# ------------------------------------------------------------
#  INDICATORS
# ------------------------------------------------------------
def add_ma_crossover_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add MA crossover indicators to dataframe."""
    df = df.copy()

    df["ema_9"] = ta.trend.ema_indicator(df["close"], window=9)
    df["ema_21"] = ta.trend.ema_indicator(df["close"], window=21)
    df["ema_200"] = ta.trend.ema_indicator(df["close"], window=200)

    df["rsi"] = ta.momentum.rsi(df["close"], window=14)
    df["volume_sma20"] = df["volume"].rolling(20).mean()

    macd = ta.trend.MACD(df["close"], window_slow=26, window_fast=12, window_sign=9)
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_hist"] = macd.macd_diff()

    df["ema_diff_pct"] = (df["ema_9"] - df["ema_21"]) / df["ema_21"] * 100

    return df


# ------------------------------------------------------------
#  STRATEGY SCORING
# ------------------------------------------------------------
MA_CROSSOVER_MAX_SCORE = 10.0
DISTANCE_THRESHOLD_PCT = 0.5


def ma_crossover(df: pd.DataFrame, min_candles: int = 205) -> StrategyResult:
    """Evaluate MA crossover conditions."""
    if len(df) < min_candles:
        return StrategyResult(
            name="ma_crossover",
            buy_score_raw=0.0, sell_score_raw=0.0,
            max_possible=MA_CROSSOVER_MAX_SCORE,
            reasons_sell=["Insufficient history for EMA200"],
        )

    df = add_ma_crossover_indicators(df)
    last = df.iloc[-1]
    prev = df.iloc[-2]

    required = ["ema_9", "ema_21", "ema_200", "rsi", "volume_sma20",
                "macd_hist", "ema_diff_pct"]
    if last[required].isna().any() or prev[["ema_9", "ema_21"]].isna().any():
        return StrategyResult(
            name="ma_crossover",
            buy_score_raw=0.0, sell_score_raw=0.0,
            max_possible=MA_CROSSOVER_MAX_SCORE,
            reasons_sell=["Indicator warm-up incomplete (NaN present)"],
        )

    close = last["close"]
    ema9, ema21, ema200 = last["ema_9"], last["ema_21"], last["ema_200"]
    prev_ema9, prev_ema21 = prev["ema_9"], prev["ema_21"]
    rsi_val = last["rsi"]
    macd_hist = last["macd_hist"]
    ema_diff_pct = last["ema_diff_pct"]
    vol, vol_avg = last["volume"], last["volume_sma20"]

    buy_score = 0.0
    sell_score = 0.0
    buy_reasons: list[str] = []
    sell_reasons: list[str] = []

    # --- Crossover event vs sustained separation ---
    golden_cross = (prev_ema9 <= prev_ema21) and (ema9 > ema21)
    death_cross = (prev_ema9 >= prev_ema21) and (ema9 < ema21)

    if golden_cross:
        buy_score += 5
        buy_reasons.append("Golden cross: EMA9 crossed above EMA21 this candle")
    elif ema9 > ema21 and ema_diff_pct > DISTANCE_THRESHOLD_PCT:
        buy_score += 3
        buy_reasons.append(f"EMA9 > EMA21 by {ema_diff_pct:.2f}% (sustained bullish separation)")

    if death_cross:
        sell_score += 5
        sell_reasons.append("Death cross: EMA9 crossed below EMA21 this candle")
    elif ema9 < ema21 and ema_diff_pct < -DISTANCE_THRESHOLD_PCT:
        sell_score += 3
        sell_reasons.append(f"EMA9 < EMA21 by {abs(ema_diff_pct):.2f}% (sustained bearish separation)")

    # --- 200 EMA trend alignment ---
    if buy_score > 0 and close > ema200:
        buy_score += 2
        buy_reasons.append("Aligned with 200 EMA trend (bullish)")
    if sell_score > 0 and close < ema200:
        sell_score += 2
        sell_reasons.append("Aligned with 200 EMA trend (bearish)")

    # --- RSI confirmation ---
    if buy_score > 0 and rsi_val > 50:
        buy_score += 2
        buy_reasons.append(f"RSI {rsi_val:.1f} confirms bullish bias")
    if sell_score > 0 and rsi_val < 50:
        sell_score += 2
        sell_reasons.append(f"RSI {rsi_val:.1f} confirms bearish bias")

    # --- MACD histogram confirmation ---
    if buy_score > 0 and macd_hist > 0:
        buy_score += 1
        buy_reasons.append("MACD histogram positive confirms crossover")
    if sell_score > 0 and macd_hist < 0:
        sell_score += 1
        sell_reasons.append("MACD histogram negative confirms crossover")

    return StrategyResult(
        name="ma_crossover",
        buy_score_raw=round(min(buy_score, MA_CROSSOVER_MAX_SCORE), 2),
        sell_score_raw=round(min(sell_score, MA_CROSSOVER_MAX_SCORE), 2),
        max_possible=MA_CROSSOVER_MAX_SCORE,
        reasons_buy=buy_reasons,
        reasons_sell=sell_reasons,
    )


# ------------------------------------------------------------
#  SELF-TEST
# ------------------------------------------------------------
if __name__ == "__main__":
    np.random.seed(3)
    n = 250
    chop = 100 + np.cumsum(np.random.normal(0, 0.3, n - 15))
    up = chop[-1] + np.cumsum(np.random.normal(0.4, 0.3, 15))
    close = np.concatenate([chop, up])

    high = close + np.random.uniform(0.1, 0.4, n)
    low = close - np.random.uniform(0.1, 0.4, n)
    open_ = close - np.random.uniform(-0.2, 0.2, n)
    volume = np.random.uniform(1000, 2000, n)

    df = pd.DataFrame({
        "open": open_, "high": high, "low": low,
        "close": close, "volume": volume,
    })

    result = ma_crossover(df)
    print("Direction lean:", "BUY" if result.buy_score_raw > result.sell_score_raw else "SELL")
    print("Buy score:", result.buy_score_raw, "/", result.max_possible)
    print("Sell score:", result.sell_score_raw, "/", result.max_possible)
    print("Buy reasons:", result.reasons_buy)
    print("Sell reasons:", result.reasons_sell)

# ------------------------------------------------------------
#  SELF-TEST
# ------------------------------------------------------------
if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    
    np.random.seed(3)
    n = 250
    chop = 100 + np.cumsum(np.random.normal(0, 0.3, n - 15))
    up = chop[-1] + np.cumsum(np.random.normal(0.4, 0.3, 15))
    close = np.concatenate([chop, up])

    high = close + np.random.uniform(0.1, 0.4, n)
    low = close - np.random.uniform(0.1, 0.4, n)
    open_ = close - np.random.uniform(-0.2, 0.2, n)
    volume = np.random.uniform(1000, 2000, n)

    df = pd.DataFrame({
        "open": open_, "high": high, "low": low,
        "close": close, "volume": volume,
    })

    result = ma_crossover(df)
    print("Direction lean:", "BUY" if result.buy_score_raw > result.sell_score_raw else "SELL")
    print("Buy score:", result.buy_score_raw, "/", result.max_possible)
    print("Sell score:", result.sell_score_raw, "/", result.max_possible)
    print("Buy reasons:", result.reasons_buy)
    print("Sell reasons:", result.reasons_sell)