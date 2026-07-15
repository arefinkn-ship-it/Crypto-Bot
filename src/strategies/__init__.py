# ============================================================
#  STRATEGIES MODULE - Function-based strategies
#  Fibonacci removed from all strategies
# ============================================================

from src.strategies.trend_following import trend_following
from src.strategies.breakout import breakout
from src.strategies.ma_crossover import ma_crossover
from src.strategies.mean_reversion import mean_reversion
from src.strategies.smc import smc

__all__ = [
    'trend_following',
    'breakout',
    'ma_crossover',
    'mean_reversion',
    'smc',
]