# ============================================================
#  PORTFOLIO CORRELATION FILTER
#  Resolves: 5 "independent" altcoin signals that are all just
#  riding the same BTC-led market move.
# ============================================================

import pandas as pd
import numpy as np
from typing import List, Dict


def compute_returns_matrix(price_data: Dict[str, pd.Series], lookback: int = 50) -> pd.DataFrame:
    """
    price_data: {symbol: close_price_series} for each candidate symbol
    Returns a DataFrame of pct-change returns, aligned by index.
    """
    returns = {}
    for symbol, closes in price_data.items():
        if len(closes) < lookback:
            continue
        returns[symbol] = closes.iloc[-lookback:].pct_change().dropna().reset_index(drop=True)
    
    if not returns:
        return pd.DataFrame()
    
    return pd.DataFrame(returns)


def dedupe_correlated_signals(signals: List[dict], price_data: Dict[str, pd.Series],
                                correlation_threshold: float = 0.75,
                                lookback: int = 50) -> List[dict]:
    """
    signals: list of signal dicts, each with a 'symbol' and 'score' key,
             already sorted by score descending (as main.py already does).
    price_data: {symbol: recent close price Series} for symbols in `signals`

    Keeps the highest-scored signal within each correlated cluster,
    drops the rest as redundant rather than genuinely independent.
    """
    if len(signals) <= 1:
        return signals

    symbols = [s["symbol"] for s in signals]
    returns_df = compute_returns_matrix(
        {sym: price_data[sym] for sym in symbols if sym in price_data}, lookback
    )
    
    if returns_df.empty or returns_df.shape[1] < 2:
        return signals  # not enough data to compute correlation

    corr_matrix = returns_df.corr()

    kept = []
    dropped_symbols = set()

    for signal in signals:  # already sorted best-score-first by caller
        sym = signal["symbol"]
        if sym in dropped_symbols or sym not in corr_matrix.columns:
            if sym not in corr_matrix.columns:
                kept.append(signal)  # no correlation data - keep by default
            continue

        kept.append(signal)

        # drop any lower-ranked symbol highly correlated with this one
        for other in corr_matrix.columns:
            if other == sym or other in dropped_symbols:
                continue
            if abs(corr_matrix.loc[sym, other]) >= correlation_threshold:
                dropped_symbols.add(other)

    return kept