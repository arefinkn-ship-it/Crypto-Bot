# ============================================================
#  SIGNALS MODULE - Signal scoring and alerts
# ============================================================

from src.signals.signal_combiner import combine_signals, StrategyResult, compute_risk_levels
from src.signals.multi_timeframe import get_multi_timeframe_signal, get_trend_direction

__all__ = [
    'combine_signals',
    'StrategyResult',
    'compute_risk_levels',
    'get_multi_timeframe_signal',
    'get_trend_direction',
]