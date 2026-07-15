# ============================================================
#  DATA QUALITY GUARD
#  Resolves: a single bad/stale indicator quietly corrupting
#  multiple strategies at once.
# ============================================================

import pandas as pd
import numpy as np


def is_data_healthy(df: pd.DataFrame, lookback: int = 20) -> tuple:
    """
    Returns (is_healthy: bool, reason: str).
    Call this BEFORE running any strategy on a symbol's dataframe.
    """
    if len(df) < lookback:
        return False, f"Insufficient data: {len(df)} candles, need {lookback}"

    window = df.iloc[-lookback:]

    # 1. Flat/dead price feed - no real price movement at all
    price_range_pct = (window["close"].max() - window["close"].min()) / window["close"].mean() * 100
    if price_range_pct < 0.01:
        return False, f"Price essentially flat ({price_range_pct:.4f}% range) - likely stale feed"

    # 2. Zero or near-zero volume - illiquid, spreads probably unusable
    if window["volume"].mean() < 1e-6 or (window["volume"] == 0).sum() > lookback * 0.5:
        return False, "Volume too low/zero for reliable signal"

    # 3. Suspicious repeated identical closes (duplicate/cached candles)
    if window["close"].nunique() <= 2:
        return False, "Close price barely changing - suspect duplicate/cached candles"

    # 4. Gaps in timestamp sequence (if timestamp column present)
    if "timestamp" in df.columns:
        try:
            ts = pd.to_datetime(df["timestamp"].iloc[-lookback:])
            diffs = ts.diff().dropna()
            if len(diffs) > 0:
                median_gap = diffs.median()
                max_gap = diffs.max()
                if max_gap > median_gap * 5 and median_gap.total_seconds() > 0:
                    return False, f"Timestamp gap detected (max {max_gap} vs median {median_gap})"
        except Exception:
            pass  # If timestamp parsing fails, skip this check

    return True, "OK"