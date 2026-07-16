# ============================================================
#  BTC TREND GATE
#  Resolves: live results showed SELL signals on altcoins losing
#  badly (10% win rate) and clustering in time - multiple alts
#  simultaneously signaling SELL on what was really one BTC-led
#  dip within a broader uptrend, then getting stopped out together
#  when the uptrend resumed. Alts are largely beta plays on BTC;
#  fighting BTC's own trend on an altcoin is a structurally weak bet
#  regardless of how clean the 5m technical setup looks in isolation.
#
#  Applied symmetrically (blocks counter-BTC-trend BUY too), even
#  though the live data specifically showed the SELL side as the
#  broken one - the underlying logic (don't fight BTC's trend on
#  an alt) applies either direction.
# ============================================================

from typing import Dict, Optional
from src.signals.multi_timeframe import get_trend_direction


def get_btc_trend(loader) -> Dict:
    """Call ONCE per scan cycle, not per symbol - reused across
    every altcoin's gate check."""
    btc_h1 = loader.load_ohlcv("BTCUSDT", "1h", limit=250)
    if btc_h1.empty:
        return {'direction': 'NEUTRAL', 'strength': 0}
    return get_trend_direction(btc_h1)


def passes_btc_trend_gate(symbol: str, direction: str, btc_trend: Dict) -> Optional[str]:
    """
    Returns None if the signal is allowed through, or a string
    reason if it should be blocked.

    BTC itself is exempt (can't fight its own trend).
    """
    if symbol == "BTCUSDT":
        return None

    btc_dir = btc_trend.get('direction', 'NEUTRAL')

    if btc_dir == 'NEUTRAL':
        return None  # no clear BTC read - don't block, alt stands on its own

    if btc_dir == 'BULLISH' and direction == 'SELL':
        return f"blocked: {symbol} SELL against bullish BTC H1 trend"
    if btc_dir == 'BEARISH' and direction == 'BUY':
        return f"blocked: {symbol} BUY against bearish BTC H1 trend"

    return None