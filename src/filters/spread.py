# ============================================================
#  SPREAD / LIQUIDITY FILTER
#  Resolves: a high-score signal on a thin coin whose spread
#  eats the theoretical edge before a trade even fills.
# ============================================================

from typing import Optional, Tuple


def spread_is_acceptable(orderbook: dict, atr_value: float,
                          max_spread_atr_ratio: float = 0.15) -> Tuple[bool, Optional[float]]:
    """
    orderbook: output of BinanceClient.fetch_order_book()
    atr_value: current ATR for this symbol/timeframe

    Rejects signals where the bid-ask spread eats too much of the
    ATR-implied move.

    Returns (is_acceptable: bool, spread_pct_of_atr: float)
    """
    if not orderbook or not orderbook.get("bids") or not orderbook.get("asks"):
        return False, None

    best_bid = orderbook["bids"][0][0]
    best_ask = orderbook["asks"][0][0]
    spread = best_ask - best_bid

    if atr_value <= 0:
        return False, None

    spread_ratio = spread / atr_value
    return spread_ratio <= max_spread_atr_ratio, round(spread_ratio, 4)