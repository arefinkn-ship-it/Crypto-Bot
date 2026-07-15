# ============================================================
#  DYNAMIC THRESHOLDS - per-symbol, percentile-based
#  Resolves: fixed global thresholds applied identically across
#  a 150-coin universe with very different volatility/liquidity.
# ============================================================

import pandas as pd
from typing import Optional, Tuple


def dynamic_threshold(series: pd.Series, lookback: int = 200,
                       lower_pct: float = 0.15, upper_pct: float = 0.85) -> Tuple[Optional[float], Optional[float]]:
    """
    Returns (lower_threshold, upper_threshold) computed from this
    SYMBOL's own recent distribution, not a hardcoded global number.

    Example: instead of "RSI < 30 = oversold" for every coin,
    lower_thresh, upper_thresh = dynamic_threshold(df['rsi'])
    "RSI < lower_thresh = oversold FOR THIS COIN'S OWN RSI RANGE"

    A choppy small-cap whose RSI naturally swings 20-80 gets a
    different oversold line than a calm major whose RSI rarely
    leaves 40-60.
    """
    window = series.iloc[-lookback:].dropna()
    if len(window) < 30:
        # not enough history - caller should fall back to a fixed default
        return None, None
    return window.quantile(lower_pct), window.quantile(upper_pct)


def dynamic_volume_multiplier(volume: pd.Series, lookback: int = 200,
                                percentile: float = 0.85) -> float:
    """
    Returns a "spike" volume level for THIS symbol, as a multiple
    of its own rolling average, instead of a flat 1.5x for every coin.
    """
    window = volume.iloc[-lookback:].dropna()
    avg = window.mean()
    if avg == 0 or len(window) < 30:
        return 1.5  # fallback to the old fixed default
    spike_level = window.quantile(percentile)
    return round(spike_level / avg, 2)