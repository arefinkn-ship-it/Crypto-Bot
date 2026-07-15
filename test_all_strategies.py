# ============================================================
#  TEST ALL STRATEGIES - Run self-tests for all strategies
# ============================================================

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import numpy as np

from src.strategies.trend_following import trend_following
from src.strategies.breakout import breakout
from src.strategies.ma_crossover import ma_crossover
from src.strategies.mean_reversion import mean_reversion
from src.strategies.smc import smc
from src.signals.signal_combiner import combine_signals, StrategyResult, compute_risk_levels

print("=" * 60)
print("🧪 TESTING ALL 5 STRATEGIES")
print("=" * 60)

# Create a simple test dataframe
np.random.seed(42)
n = 250
close = 100 + np.cumsum(np.random.normal(0.15, 1.0, n))
high = close + np.random.uniform(0.1, 1.0, n)
low = close - np.random.uniform(0.1, 1.0, n)
open_ = close - np.random.uniform(-0.5, 0.5, n)
volume = np.random.uniform(1000, 5000, n)
volume[-1] *= 2.0

df = pd.DataFrame({
    "open": open_, "high": high, "low": low,
    "close": close, "volume": volume,
})

print("\n📊 Testing Trend Following...")
result = trend_following(df)
print(f"   Score: BUY={result.buy_score_raw:.2f}, SELL={result.sell_score_raw:.2f}")
print(f"   Reasons: {result.reasons_buy[:2] if result.reasons_buy else result.reasons_sell[:2]}")

print("\n📊 Testing Breakout...")
result = breakout(df)
print(f"   Score: BUY={result.buy_score_raw:.2f}, SELL={result.sell_score_raw:.2f}")

print("\n📊 Testing MA Crossover...")
result = ma_crossover(df)
print(f"   Score: BUY={result.buy_score_raw:.2f}, SELL={result.sell_score_raw:.2f}")

print("\n📊 Testing Mean Reversion...")
result = mean_reversion(df)
print(f"   Score: BUY={result.buy_score_raw:.2f}, SELL={result.sell_score_raw:.2f}")

print("\n📊 Testing SMC...")
result = smc(df)
print(f"   Score: BUY={result.buy_score_raw:.2f}, SELL={result.sell_score_raw:.2f}")

print("\n" + "=" * 60)
print("✅ ALL STRATEGIES TESTED SUCCESSFULLY!")
print("=" * 60)