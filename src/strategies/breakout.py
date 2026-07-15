# ============================================================
#  STRATEGY: BREAKOUT - Increased Scoring Weights
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
def add_breakout_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    bb = ta.volatility.BollingerBands(df["close"], window=20, window_dev=2.0)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_lower"] = bb.bollinger_lband()
    df["bb_mid"] = bb.bollinger_mavg()
    band_width = (df["bb_upper"] - df["bb_lower"]).replace(0, np.nan)
    df["bb_position"] = (df["close"] - df["bb_lower"]) / band_width

    df["rsi"] = ta.momentum.rsi(df["close"], window=14)
    df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
    df["volume_sma20"] = df["volume"].rolling(20).mean()

    df["recent_high_20"] = df["high"].shift(1).rolling(20).max()
    df["recent_low_20"] = df["low"].shift(1).rolling(20).min()

    return df


# ------------------------------------------------------------
#  STRATEGY SCORING - INCREASED WEIGHTS
# ------------------------------------------------------------
BREAKOUT_MAX_SCORE = 10.0


def breakout(df: pd.DataFrame, min_candles: int = 25) -> StrategyResult:
    if len(df) < min_candles:
        return StrategyResult(
            name="breakout",
            buy_score_raw=0.0, sell_score_raw=0.0,
            max_possible=BREAKOUT_MAX_SCORE,
            reasons_sell=["Insufficient history"],
        )

    df = add_breakout_indicators(df)
    last = df.iloc[-1]
    prev = df.iloc[-2]

    required = ["bb_upper", "bb_lower", "bb_position", "rsi", "atr",
                "volume_sma20", "recent_high_20", "recent_low_20"]
    if last[required].isna().any() or prev[required].isna().any():
        return StrategyResult(
            name="breakout",
            buy_score_raw=0.0, sell_score_raw=0.0,
            max_possible=BREAKOUT_MAX_SCORE,
            reasons_sell=["Indicator warm-up incomplete"],
        )

    close = last["close"]
    prev_close = prev["close"]
    bb_upper, bb_lower, bb_pos = last["bb_upper"], last["bb_lower"], last["bb_position"]
    rsi_val = last["rsi"]
    atr_val = last["atr"]
    vol, vol_avg = last["volume"], last["volume_sma20"]
    recent_high, recent_low = last["recent_high_20"], last["recent_low_20"]

    buy_score, sell_score = 0.0, 0.0
    buy_reasons, sell_reasons = [], []

    # --- Breakout trigger (INCREASED WEIGHTS) ---
    strong_up = close > bb_upper and close > (recent_high + atr_val * 0.5)
    weak_up = close > bb_upper and not strong_up

    strong_down = close < bb_lower and close < (recent_low - atr_val * 0.5)
    weak_down = close < bb_lower and not strong_down

    if strong_up:
        buy_score += 5  # Was 4
        buy_reasons.append("Strong breakout: close > BB upper AND > 20-bar high + 0.5x ATR")
    elif weak_up:
        buy_score += 3  # Was 2
        buy_reasons.append("Breakout above upper BB (no ATR confirmation)")

    if strong_down:
        sell_score += 5  # Was 4
        sell_reasons.append("Strong breakdown: close < BB lower AND < 20-bar low - 0.5x ATR")
    elif weak_down:
        sell_score += 3  # Was 2
        sell_reasons.append("Breakdown below lower BB (no ATR confirmation)")

    # --- False-breakout filter ---
    if buy_score > 0 and prev_close > bb_upper:
        buy_score += 2
        buy_reasons.append("Breakout held for 2 consecutive closes")
    if sell_score > 0 and prev_close < bb_lower:
        sell_score += 2
        sell_reasons.append("Breakdown held for 2 consecutive closes")

    # --- Volume spike (INCREASED WEIGHT) ---
    if vol > vol_avg * 1.5:
        if buy_score > sell_score and buy_score > 0:
            buy_score += 3  # Was 2
            buy_reasons.append(f"Volume spike {vol / vol_avg:.1f}x confirms breakout")
        elif sell_score > buy_score and sell_score > 0:
            sell_score += 3  # Was 2
            sell_reasons.append(f"Volume spike {vol / vol_avg:.1f}x confirms breakdown")

    # --- RSI momentum alignment (INCREASED WEIGHT) ---
    if buy_score > 0 and rsi_val > 50:
        buy_score += 2  # Was 1
        buy_reasons.append(f"RSI {rsi_val:.1f} confirms bullish momentum")
    if sell_score > 0 and rsi_val < 50:
        sell_score += 2  # Was 1
        sell_reasons.append(f"RSI {rsi_val:.1f} confirms bearish momentum")

    # --- BB position extremity ---
    if buy_score > 0 and bb_pos > 0.7:
        buy_score += 1
        buy_reasons.append(f"BB position {bb_pos:.2f} - deep in breakout zone")
    if sell_score > 0 and bb_pos < 0.3:
        sell_score += 1
        sell_reasons.append(f"BB position {bb_pos:.2f} - deep in breakdown zone")

    return StrategyResult(
        name="breakout",
        buy_score_raw=round(min(buy_score, BREAKOUT_MAX_SCORE), 2),
        sell_score_raw=round(min(sell_score, BREAKOUT_MAX_SCORE), 2),
        max_possible=BREAKOUT_MAX_SCORE,
        reasons_buy=buy_reasons,
        reasons_sell=sell_reasons,
    )


if __name__ == "__main__":
    np.random.seed(7)
    n = 60
    flat = 100 + np.random.normal(0, 0.3, n - 2)
    breakout_candles = np.array([104.0, 106.0])
    close = np.concatenate([flat, breakout_candles])

    high = close + np.random.uniform(0.1, 0.5, n)
    low = close - np.random.uniform(0.1, 0.5, n)
    open_ = close - np.random.uniform(-0.3, 0.3, n)
    volume = np.random.uniform(1000, 2000, n)
    volume[-2:] *= 2.5

    df = pd.DataFrame({
        "open": open_, "high": high, "low": low,
        "close": close, "volume": volume,
    })

    result = breakout(df)
    print("Direction:", "BUY" if result.buy_score_raw > result.sell_score_raw else "SELL")
    print(f"Buy: {result.buy_score_raw}/{result.max_possible}")
    print(f"Sell: {result.sell_score_raw}/{result.max_possible}")