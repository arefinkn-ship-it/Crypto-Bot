# ============================================================
#  FILTERS MODULE - Data quality, spread, correlation
# ============================================================

from src.filters.data_quality import is_data_healthy
from src.filters.spread import spread_is_acceptable
from src.filters.correlation import dedupe_correlated_signals
from src.filters.dynamic_thresholds import dynamic_threshold, dynamic_volume_multiplier
from src.filters.funding import funding_rate_modifier

__all__ = [
    'is_data_healthy',
    'spread_is_acceptable',
    'dedupe_correlated_signals',
    'dynamic_threshold',
    'dynamic_volume_multiplier',
    'funding_rate_modifier',
]