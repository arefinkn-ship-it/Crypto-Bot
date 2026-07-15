# ============================================================
#  TEST RUNNER - Runs Tests 1, 2, and 3
#  Usage: py test_runner.py --symbol BTCUSDT --all
# ============================================================

import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import sqlite3
import pandas as pd
from datetime import datetime

from src.strategies.trend_following import trend_following
from src.strategies.breakout import breakout
from src.strategies.ma_crossover import ma_crossover
from src.strategies.mean_reversion import mean_reversion
from src.strategies.smc import smc
from src.signals.signal_combiner import combine_signals
from src.core.config import config


def load_history(symbol: str, timeframe: str = '5m') -> pd.DataFrame:
    """Load historical data for testing."""
    conn = sqlite3.connect('crypto_bot.db')
    df = pd.read_sql(
        "SELECT * FROM price_data WHERE symbol = ? AND timeframe = ? ORDER BY timestamp ASC",
        conn, params=(symbol, timeframe),
    )
    conn.close()
    return df


def evaluate_all_strategies(df_slice: pd.DataFrame) -> dict:
    """Evaluate all 5 strategies on a data slice."""
    results = [
        trend_following(df_slice),
        breakout(df_slice),
        ma_crossover(df_slice),
        mean_reversion(df_slice),
        smc(df_slice),
    ]
    return combine_signals(results)


def test1_fibonacci(df: pd.DataFrame, min_candles: int = 205) -> dict:
    """
    TEST 1: Remove Fibonacci
    Compare signals with and without Fibonacci.
    """
    print("\n" + "=" * 60)
    print("🧪 TEST 1: Fibonacci ON vs OFF")
    print("=" * 60)
    
    # Test with Fibonacci ON
    print("\n📊 Running with Fibonacci ON...")
    config.USE_FIBONACCI = True
    
    with_fib = []
    for i in range(min_candles, len(df)):
        slice_df = df.iloc[:i+1]
        signal = evaluate_all_strategies(slice_df)
        if signal['direction'] != 'NEUTRAL':
            with_fib.append(signal['total_score'])
    
    # Test with Fibonacci OFF
    print("\n📊 Running with Fibonacci OFF...")
    config.USE_FIBONACCI = False
    
    without_fib = []
    for i in range(min_candles, len(df)):
        slice_df = df.iloc[:i+1]
        signal = evaluate_all_strategies(slice_df)
        if signal['direction'] != 'NEUTRAL':
            without_fib.append(signal['total_score'])
    
    # Restore config
    config.USE_FIBONACCI = True
    
    # Results
    print("\n" + "=" * 60)
    print("📊 TEST 1 RESULTS")
    print("=" * 60)
    
    avg_with = sum(with_fib) / len(with_fib) if with_fib else 0
    avg_without = sum(without_fib) / len(without_fib) if without_fib else 0
    
    print(f"\n{'Metric':<20} {'With Fibonacci':<20} {'Without Fibonacci':<20}")
    print("-" * 60)
    print(f"{'Signals':<20} {len(with_fib):<20} {len(without_fib):<20}")
    print(f"{'Avg Score':<20} {avg_with:<19.2f} {avg_without:<19.2f}")
    
    if avg_with > avg_without:
        print("\n✅ Fibonacci IMPROVES average signal score")
    elif avg_with < avg_without:
        print("\n❌ Fibonacci HURTS average signal score")
    else:
        print("\n⚠️ Fibonacci makes no significant difference")
    
    return {
        'with_fib_count': len(with_fib),
        'without_fib_count': len(without_fib),
        'with_fib_avg': avg_with,
        'without_fib_avg': avg_without,
    }


def test2_mean_reversion_divergence(df: pd.DataFrame, min_candles: int = 205) -> dict:
    """
    TEST 2: Remove Divergence in Mean Reversion
    Compare Mean Reversion with and without divergence.
    """
    print("\n" + "=" * 60)
    print("🧪 TEST 2: Mean Reversion - Divergence ON vs OFF")
    print("=" * 60)
    
    # We need to test mean_reversion with and without divergence
    # Since we already removed divergence, this test is informational
    # The divergence was removed from mean_reversion.py
    
    print("\n📊 Mean Reversion currently has DIVERGENCE REMOVED")
    print("   To test with divergence, you would need to add it back.")
    
    # Let's check how many signals Mean Reversion generates
    mr_signals = []
    for i in range(min_candles, len(df)):
        slice_df = df.iloc[:i+1]
        result = mean_reversion(slice_df)
        if result.buy_score_raw > 0 or result.sell_score_raw > 0:
            mr_signals.append({
                'buy': result.buy_score_raw,
                'sell': result.sell_score_raw,
                'max': max(result.buy_score_raw, result.sell_score_raw),
            })
    
    print(f"\n📊 Mean Reversion generated {len(mr_signals)} signals")
    if mr_signals:
        avg_score = sum(s['max'] for s in mr_signals) / len(mr_signals)
        print(f"   Average score: {avg_score:.2f}/10")
    
    return {'signals': len(mr_signals)}


def test3_per_strategy_backtest(df: pd.DataFrame, min_candles: int = 205) -> dict:
    """
    TEST 3: Backtest Each Strategy
    Compare performance of each strategy individually.
    """
    print("\n" + "=" * 60)
    print("🧪 TEST 3: Per-Strategy Backtest")
    print("=" * 60)
    
    strategies = [
        ('Trend Following', trend_following),
        ('Breakout', breakout),
        ('MA Crossover', ma_crossover),
        ('Mean Reversion', mean_reversion),
        ('SMC', smc),
    ]
    
    results = {}
    
    for name, strategy_func in strategies:
        print(f"\n📊 Testing {name}...")
        
        signal_count = 0
        total_score = 0
        
        for i in range(min_candles, len(df)):
            slice_df = df.iloc[:i+1]
            try:
                result = strategy_func(slice_df)
                score = max(result.buy_score_raw, result.sell_score_raw)
                if score > 0:
                    signal_count += 1
                    total_score += score
            except:
                continue
        
        avg_score = total_score / signal_count if signal_count > 0 else 0
        results[name] = {
            'signals': signal_count,
            'avg_score': avg_score,
        }
        print(f"   Signals: {signal_count}, Avg Score: {avg_score:.2f}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST 3 SUMMARY")
    print("=" * 60)
    
    print(f"\n{'Strategy':<20} {'Signals':<15} {'Avg Score':<15}")
    print("-" * 50)
    for name, data in results.items():
        print(f"{name:<20} {data['signals']:<15} {data['avg_score']:<14.2f}")
    
    # Find best
    best = max(results.items(), key=lambda x: x[1]['avg_score'] if x[1]['signals'] > 0 else 0)
    print(f"\n🏆 Best strategy by average score: {best[0]} ({best[1]['avg_score']:.2f})")
    
    return results


def run_all_tests(symbol: str, timeframe: str = '5m'):
    """Run all three tests."""
    print("\n" + "=" * 60)
    print(f"🧪 RUNNING ALL TESTS - {symbol} ({timeframe})")
    print("=" * 60)
    
    # Load data
    df = load_history(symbol, timeframe)
    print(f"\n📊 Loaded {len(df)} candles for {symbol}")
    
    if len(df) < 205:
        print(f"❌ Not enough data. Need 205+ candles, have {len(df)}")
        return
    
    min_candles = min(205, len(df))
    
    # Run tests
    results = {}
    results['test1'] = test1_fibonacci(df, min_candles)
    results['test2'] = test2_mean_reversion_divergence(df, min_candles)
    results['test3'] = test3_per_strategy_backtest(df, min_candles)
    
    # Final summary
    print("\n" + "=" * 60)
    print("📊 FINAL SUMMARY - ALL TESTS COMPLETE")
    print("=" * 60)
    
    print("\n📈 Test 1 (Fibonacci):")
    print(f"   With Fib: {results['test1']['with_fib_count']} signals, Avg Score: {results['test1']['with_fib_avg']:.2f}")
    print(f"   Without Fib: {results['test1']['without_fib_count']} signals, Avg Score: {results['test1']['without_fib_avg']:.2f}")
    
    print("\n📈 Test 2 (Mean Reversion):")
    print(f"   Divergence removed: {results['test2']['signals']} signals")
    
    print("\n📈 Test 3 (Per-Strategy):")
    for name, data in results['test3'].items():
        print(f"   {name}: {data['signals']} signals, Avg Score: {data['avg_score']:.2f}")
    
    print("\n" + "=" * 60)
    print("✅ All tests complete")
    print("   Recommendations:")
    print("   - Check avg scores to decide if Fibonacci should stay")
    print("   - Check which strategy performs best")
    print("   - Consider removing weak strategies")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run tests 1, 2, and 3")
    parser.add_argument("--symbol", default="BTCUSDT", help="Trading pair")
    parser.add_argument("--timeframe", default="5m", help="Timeframe")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    args = parser.parse_args()
    
    run_all_tests(args.symbol, args.timeframe)