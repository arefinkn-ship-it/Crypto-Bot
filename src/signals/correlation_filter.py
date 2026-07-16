# ============================================================
#  PORTFOLIO CORRELATION FILTER
#  Resolves: live data showed clusters of simultaneous signals
#  (e.g. 5 SELL alerts firing in the same 15-min scan cycle) that
#  weren't independent - they were one market move counted multiple
#  times, and lost together as a bloc.
# ============================================================

import pandas as pd
from typing import List, Dict


def compute_returns_matrix(price_data: Dict[str, pd.Series], lookback: int = 50) -> pd.DataFrame:
    returns = {}
    for symbol, closes in price_data.items():
        returns[symbol] = closes.iloc[-lookback:].pct_change().dropna().reset_index(drop=True)
    return pd.DataFrame(returns)


def dedupe_correlated_signals(signals: List[dict], price_data: Dict[str, pd.Series],
                                correlation_threshold: float = 0.75,
                                lookback: int = 50) -> List[dict]:
    """
    signals: list of signal dicts (already sorted by score descending),
    each with a 'symbol' key.
    price_data: {symbol: recent close price Series}

    Keeps the highest-scored signal within each correlated cluster,
    drops the rest as redundant rather than genuinely independent.
    """
    if len(signals) <= 1:
        return signals

    symbols = [s["symbol"] for s in signals]
    returns_df = compute_returns_matrix(
        {sym: price_data[sym] for sym in symbols if sym in price_data}, lookback
    )
    if returns_df.shape[1] < 2:
        return signals

    corr_matrix = returns_df.corr()

    kept = []
    dropped_symbols = set()

    for signal in signals:
        sym = signal["symbol"]
        if sym in dropped_symbols:
            continue
        if sym not in corr_matrix.columns:
            kept.append(signal)
            continue

        kept.append(signal)

        for other in corr_matrix.columns:
            if other == sym or other in dropped_symbols:
                continue
            if abs(corr_matrix.loc[sym, other]) >= correlation_threshold:
                dropped_symbols.add(other)

    return kept