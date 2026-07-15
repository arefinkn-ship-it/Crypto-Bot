# ============================================================
#  Fix: Add project root to path for self-test
# ============================================================
import sys
from pathlib import Path
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# ============================================================
#  STRATEGY: SMART MONEY CONCEPTS (SMC) - Reference implementation
#  Same pattern as the other 4 strategies, deliberately conservative.
# ============================================================

import pandas as pd
import numpy as np
import ta

from src.signals.signal_combiner import StrategyResult


# ------------------------------------------------------------
#  PATTERN DEFINITIONS
# ------------------------------------------------------------
def find_order_blocks(df: pd.DataFrame, lookback: int = 50,
                       volume_mult: float = 1.2, impulse_pct: float = 1.5):
    """
    Bullish order block: the last DOWN candle immediately before an
    UP move that closes above the down candle's high and moves at
    least `impulse_pct`% in the following 1-3 candles, on volume
    > volume_mult x the 20-period average.

    Bearish order block: mirror.

    Returns the single MOST RECENT bullish and bearish order block.
    """
    window = df.iloc[-lookback:].reset_index(drop=True)
    vol_avg = window["volume"].rolling(20).mean()

    bullish_ob = None
    bearish_ob = None

    for i in range(1, len(window) - 3):
        candle = window.iloc[i]
        is_down_candle = candle["close"] < candle["open"]
        is_up_candle = candle["close"] > candle["open"]

        future = window.iloc[i + 1: i + 4]
        if future.empty or pd.isna(vol_avg.iloc[i]):
            continue

        move_pct = (future["close"].iloc[-1] - candle["close"]) / candle["close"] * 100
        impulse_volume = future["volume"].max()

        if (is_down_candle and move_pct > impulse_pct
                and impulse_volume > vol_avg.iloc[i] * volume_mult
                and future["close"].iloc[-1] > candle["high"]):
            bullish_ob = {
                "high": candle["high"], "low": candle["low"],
                "index_from_end": len(window) - i,
            }

        if (is_up_candle and move_pct < -impulse_pct
                and impulse_volume > vol_avg.iloc[i] * volume_mult
                and future["close"].iloc[-1] < candle["low"]):
            bearish_ob = {
                "high": candle["high"], "low": candle["low"],
                "index_from_end": len(window) - i,
            }

    return bullish_ob, bearish_ob


def find_fair_value_gap(df: pd.DataFrame, lookback: int = 10, min_gap_atr: float = 0.3):
    """3-candle FVG detection sized relative to ATR."""
    window = df.iloc[-lookback:].reset_index(drop=True)
    atr = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
    atr_val = atr.iloc[-1]
    if pd.isna(atr_val) or atr_val == 0:
        return None, None

    bullish_fvg = None
    bearish_fvg = None

    for i in range(2, len(window)):
        c0, c2 = window.iloc[i - 2], window.iloc[i]
        gap_up = c2["low"] - c0["high"]
        gap_down = c0["low"] - c2["high"]

        if gap_up > atr_val * min_gap_atr:
            bullish_fvg = {"top": c2["low"], "bottom": c0["high"]}
        if gap_down > atr_val * min_gap_atr:
            bearish_fvg = {"top": c0["low"], "bottom": c2["high"]}

    return bullish_fvg, bearish_fvg


def detect_break_of_structure(df: pd.DataFrame, lookback: int = 20) -> str:
    """BOS: current close breaks above prior high or below prior low."""
    if len(df) < lookback + 1:
        return None
    prior = df.iloc[-(lookback + 1):-1]
    current_close = df.iloc[-1]["close"]

    if current_close > prior["high"].max():
        return "bullish"
    if current_close < prior["low"].min():
        return "bearish"
    return None


def detect_liquidity_sweep(df: pd.DataFrame, lookback: int = 20) -> str:
    """Liquidity sweep: wick breaks prior level, close snaps back inside."""
    if len(df) < lookback + 1:
        return None
    prior = df.iloc[-(lookback + 1):-1]
    current = df.iloc[-1]

    prior_low = prior["low"].min()
    prior_high = prior["high"].max()

    swept_low = current["low"] < prior_low and current["close"] > prior_low
    swept_high = current["high"] > prior_high and current["close"] < prior_high

    if swept_low and current["close"] > current["open"]:
        return "buy_side_sweep"
    if swept_high and current["close"] < current["open"]:
        return "sell_side_sweep"
    return None


# ------------------------------------------------------------
#  STRATEGY SCORING
# ------------------------------------------------------------
SMC_MAX_SCORE = 10.0
OB_MAX_AGE_CANDLES = 40


def smc(df: pd.DataFrame, min_candles: int = 55) -> StrategyResult:
    """Evaluate SMC conditions."""
    if len(df) < min_candles:
        return StrategyResult(
            name="smc",
            buy_score_raw=0.0, sell_score_raw=0.0,
            max_possible=SMC_MAX_SCORE,
            reasons_sell=["Insufficient history"],
        )

    close = df.iloc[-1]["close"]
    atr = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
    atr_val = atr.iloc[-1]
    if pd.isna(atr_val) or atr_val == 0:
        return StrategyResult(
            name="smc",
            buy_score_raw=0.0, sell_score_raw=0.0,
            max_possible=SMC_MAX_SCORE,
            reasons_sell=["ATR unavailable"],
        )

    buy_score = 0.0
    sell_score = 0.0
    buy_reasons: list[str] = []
    sell_reasons: list[str] = []

    # --- Order blocks: nearest only, age-capped ---
    bullish_ob, bearish_ob = find_order_blocks(df)

    if bullish_ob and bullish_ob["index_from_end"] <= OB_MAX_AGE_CANDLES:
        if bullish_ob["low"] <= close <= bullish_ob["high"] * 1.01:
            buy_score += 3
            buy_reasons.append(f"Trading inside/near bullish order block ({bullish_ob['index_from_end']} candles ago)")
        elif close > bullish_ob["high"] and (close - bullish_ob["high"]) / atr_val < 1.0:
            buy_score += 1
            buy_reasons.append("Near bullish order block (within 1x ATR above)")

    if bearish_ob and bearish_ob["index_from_end"] <= OB_MAX_AGE_CANDLES:
        if bearish_ob["low"] * 0.99 <= close <= bearish_ob["high"]:
            sell_score += 3
            sell_reasons.append(f"Trading inside/near bearish order block ({bearish_ob['index_from_end']} candles ago)")
        elif close < bearish_ob["low"] and (bearish_ob["low"] - close) / atr_val < 1.0:
            sell_score += 1
            sell_reasons.append("Near bearish order block (within 1x ATR below)")

    # --- Fair value gap ---
    bullish_fvg, bearish_fvg = find_fair_value_gap(df)

    if bullish_fvg and bullish_fvg["bottom"] <= close <= bullish_fvg["top"]:
        buy_score += 2
        buy_reasons.append("Trading inside bullish fair value gap")
    if bearish_fvg and bearish_fvg["bottom"] <= close <= bearish_fvg["top"]:
        sell_score += 2
        sell_reasons.append("Trading inside bearish fair value gap")

    # --- Break of structure ---
    bos = detect_break_of_structure(df)
    if bos == "bullish":
        buy_score += 3
        buy_reasons.append("Bullish break of structure (closed above prior 20-bar high)")
    elif bos == "bearish":
        sell_score += 3
        sell_reasons.append("Bearish break of structure (closed below prior 20-bar low)")

    # --- Liquidity sweep ---
    sweep = detect_liquidity_sweep(df)
    if sweep == "buy_side_sweep":
        buy_score += 2
        buy_reasons.append("Buy-side liquidity sweep (swept lows, closed back above)")
    elif sweep == "sell_side_sweep":
        sell_score += 2
        sell_reasons.append("Sell-side liquidity sweep (swept highs, closed back below)")

    return StrategyResult(
        name="smc",
        buy_score_raw=round(min(buy_score, SMC_MAX_SCORE), 2),
        sell_score_raw=round(min(sell_score, SMC_MAX_SCORE), 2),
        max_possible=SMC_MAX_SCORE,
        reasons_buy=buy_reasons,
        reasons_sell=sell_reasons,
    )


# ------------------------------------------------------------
#  SELF-TEST
# ------------------------------------------------------------
if __name__ == "__main__":
    np.random.seed(21)
    n = 55
    base = 100 + np.cumsum(np.random.normal(0, 0.1, n))

    ob_idx = n - 18
    base[ob_idx] = base[ob_idx - 1] - 1.0
    base[ob_idx + 1] = base[ob_idx] + 2.0
    base[ob_idx + 2] = base[ob_idx + 1] + 0.8
    for k in range(ob_idx + 3, n - 1):
        base[k] = base[ob_idx + 2] + np.random.normal(0, 0.15)
    base[-1] = max(base[ob_idx: n - 1]) + 1.0

    close = base
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    open_[ob_idx] = open_[ob_idx - 1] + 0.3
    high = np.maximum(open_, close) + np.random.uniform(0.05, 0.2, n)
    low = np.minimum(open_, close) - np.random.uniform(0.05, 0.2, n)
    volume = np.random.uniform(1000, 1500, n)
    volume[ob_idx + 1] *= 3.0

    df = pd.DataFrame({
        "open": open_, "high": high, "low": low,
        "close": close, "volume": volume,
    })

    result = smc(df)
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
    
    np.random.seed(21)
    n = 55
    base = 100 + np.cumsum(np.random.normal(0, 0.1, n))

    ob_idx = n - 18
    base[ob_idx] = base[ob_idx - 1] - 1.0
    base[ob_idx + 1] = base[ob_idx] + 2.0
    base[ob_idx + 2] = base[ob_idx + 1] + 0.8
    for k in range(ob_idx + 3, n - 1):
        base[k] = base[ob_idx + 2] + np.random.normal(0, 0.15)
    base[-1] = max(base[ob_idx: n - 1]) + 1.0

    close = base
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    open_[ob_idx] = open_[ob_idx - 1] + 0.3
    high = np.maximum(open_, close) + np.random.uniform(0.05, 0.2, n)
    low = np.minimum(open_, close) - np.random.uniform(0.05, 0.2, n)
    volume = np.random.uniform(1000, 1500, n)
    volume[ob_idx + 1] *= 3.0

    df = pd.DataFrame({
        "open": open_, "high": high, "low": low,
        "close": close, "volume": volume,
    })

    result = smc(df)
    print("Direction lean:", "BUY" if result.buy_score_raw > result.sell_score_raw else "SELL")
    print("Buy score:", result.buy_score_raw, "/", result.max_possible)
    print("Sell score:", result.sell_score_raw, "/", result.max_possible)
    print("Buy reasons:", result.reasons_buy)
    print("Sell reasons:", result.reasons_sell)