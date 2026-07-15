# ============================================================
#  BACKTEST HARNESS - With Testing toggles and per-strategy tracking
#  Resolves: every weight, threshold, and multiplier in the system
#  is currently a guess. This replays your OWN collected price_data
#  history, generates signals exactly as the live bot would, and
#  measures actual forward returns - so decisions can be made on
#  evidence instead of intuition.
#
#  Usage:
#      python backtest.py --symbol BTCUSDT --timeframe 5m
#      python backtest.py --symbol BTCUSDT --timeframe 5m --step 1 --horizon 24
# ============================================================

import argparse
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.config import config
from src.strategies.trend_following import trend_following
from src.strategies.breakout import breakout
from src.strategies.ma_crossover import ma_crossover
from src.strategies.mean_reversion import mean_reversion
from src.strategies.smc import smc
from src.signals.signal_combiner import combine_signals, StrategyResult


def load_history(db_path: str, symbol: str, timeframe: str) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql(
        "SELECT * FROM price_data WHERE symbol = ? AND timeframe = ? ORDER BY timestamp ASC",
        conn, params=(symbol, timeframe),
    )
    conn.close()
    return df


def evaluate_at(df_slice: pd.DataFrame, use_fib: bool = True) -> dict:
    """Evaluate all strategies at a point in time with optional Fibonacci toggle."""
    # Temporarily override config for backtesting
    original_fib = config.USE_FIBONACCI
    config.USE_FIBONACCI = use_fib
    
    results = [
        trend_following(df_slice), 
        breakout(df_slice), 
        ma_crossover(df_slice),
        mean_reversion(df_slice), 
        smc(df_slice),
    ]
    
    # Restore original config
    config.USE_FIBONACCI = original_fib
    
    return combine_signals(results)


def forward_return(df: pd.DataFrame, entry_idx: int, direction: str,
                    horizon: int, stop_loss: float, take_profit: float) -> dict:
    """
    Walk forward `horizon` candles from entry_idx and check which
    hits first: stop_loss, take_profit, or neither (return at horizon end).
    """
    entry_price = df["close"].iloc[entry_idx]
    end_idx = min(entry_idx + horizon, len(df) - 1)
    path = df.iloc[entry_idx + 1: end_idx + 1]

    outcome = "TIMEOUT"
    exit_price = df["close"].iloc[end_idx]

    for _, row in path.iterrows():
        if direction == "BUY":
            if row["low"] <= stop_loss:
                outcome, exit_price = "STOP", stop_loss
                break
            if row["high"] >= take_profit:
                outcome, exit_price = "TARGET", take_profit
                break
        else:  # SELL
            if row["high"] >= stop_loss:
                outcome, exit_price = "STOP", stop_loss
                break
            if row["low"] <= take_profit:
                outcome, exit_price = "TARGET", take_profit
                break

    pct_return = ((exit_price - entry_price) / entry_price * 100
                  if direction == "BUY"
                  else (entry_price - exit_price) / entry_price * 100)

    return {"outcome": outcome, "pct_return": round(pct_return, 3)}


def run_backtest(df: pd.DataFrame, min_candles: int = 205, horizon: int = 12,
                  stop_atr_mult: float = 1.5, tp_atr_mult: float = 3.0,
                  step: int = 5, use_fib: bool = True) -> pd.DataFrame:
    """
    step: evaluate every Nth candle instead of every single one, to
    keep runtime reasonable on long histories. Reduce to 1 for a
    full replay once you're ready for a final validation pass.
    """
    import ta
    atr_series = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)

    records = []
    for i in range(min_candles, len(df) - horizon, step):
        df_slice = df.iloc[: i + 1]
        signal = evaluate_at(df_slice, use_fib)

        if signal["direction"] == "NEUTRAL":
            continue

        atr_val = atr_series.iloc[i]
        if pd.isna(atr_val) or atr_val <= 0:
            continue

        entry_price = df["close"].iloc[i]
        if signal["direction"] == "BUY":
            stop_loss = entry_price - atr_val * stop_atr_mult
            take_profit = entry_price + atr_val * tp_atr_mult
        else:
            stop_loss = entry_price + atr_val * stop_atr_mult
            take_profit = entry_price - atr_val * tp_atr_mult

        result = forward_return(df, i, signal["direction"], horizon, stop_loss, take_profit)

        records.append({
            "index": i,
            "timestamp": df["timestamp"].iloc[i],
            "direction": signal["direction"],
            "confidence": signal["confidence"],
            "total_score": signal["total_score"],
            "confluence_count": signal["confluence_count"],
            "strategies_agreeing": signal.get("strategies_agreeing", []),
            "outcome": result["outcome"],
            "pct_return": result["pct_return"],
        })

    return pd.DataFrame(records)


def summarize(results: pd.DataFrame, symbol: str, use_fib: bool):
    if results.empty:
        print("No signals generated in this window.")
        return

    print(f"\n{'='*60}")
    print(f"📊 BACKTEST RESULTS: {symbol} {'(WITH FIBONACCI)' if use_fib else '(WITHOUT FIBONACCI)'}")
    print(f"{'='*60}")

    print(f"\nTotal signals: {len(results)}")
    print(f"  BUY: {(results['direction']=='BUY').sum()}  SELL: {(results['direction']=='SELL').sum()}")

    # Overall performance
    win_rate = (results["pct_return"] > 0).mean() * 100
    avg_return = results["pct_return"].mean()
    total_return = results["pct_return"].sum()
    target_rate = (results["outcome"] == "TARGET").mean() * 100
    stop_rate = (results["outcome"] == "STOP").mean() * 100
    timeout_rate = (results["outcome"] == "TIMEOUT").mean() * 100

    print(f"\n📈 Overall Performance:")
    print(f"  Win Rate: {win_rate:.1f}%")
    print(f"  Avg Return: {avg_return:+.3f}%")
    print(f"  Total Return: {total_return:+.3f}%")
    print(f"  Hit Target: {target_rate:.1f}%")
    print(f"  Hit Stop: {stop_rate:.1f}%")
    print(f"  Timeout: {timeout_rate:.1f}%")

    print("\n--- By confidence tier ---")
    for conf in ["HIGH", "MEDIUM", "LOW"]:
        subset = results[results["confidence"] == conf]
        if subset.empty:
            continue
        win_rate = (subset["pct_return"] > 0).mean() * 100
        avg_return = subset["pct_return"].mean()
        target_rate = (subset["outcome"] == "TARGET").mean() * 100
        stop_rate = (subset["outcome"] == "STOP").mean() * 100
        print(f"{conf:8s} n={len(subset):4d}  win_rate={win_rate:5.1f}%  "
              f"avg_return={avg_return:+.3f}%  hit_target={target_rate:.1f}%  hit_stop={stop_rate:.1f}%")

    print("\n--- By strategy contribution ---")
    strategy_counts = {}
    for strategies in results["strategies_agreeing"]:
        for s in strategies:
            strategy_counts[s] = strategy_counts.get(s, 0) + 1
    
    for strategy, count in sorted(strategy_counts.items(), key=lambda x: x[1], reverse=True):
        pct = count / len(results) * 100
        print(f"  {strategy}: {count} ({pct:.1f}%)")

    print("\n--- Sanity check: does higher confidence actually mean better outcomes? ---")
    tier_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    results["tier_rank"] = results["confidence"].map(tier_order)
    corr = results["tier_rank"].corr(results["pct_return"])
    
    if corr > 0.1:
        print(f"✅ Correlation(confidence tier, return): {corr:.3f} - GOOD - higher confidence tracks better returns")
    elif corr > -0.1:
        print(f"⚠️ Correlation(confidence tier, return): {corr:.3f} - WEAK - confidence tiers may not be meaningful yet")
    else:
        print(f"❌ Correlation(confidence tier, return): {corr:.3f} - NEGATIVE - higher confidence tracks worse returns!")

    # Export results to CSV for analysis
    export_path = f"backtest_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    results.to_csv(export_path, index=False)
    print(f"\n📁 Results exported to: {export_path}")


def compare_fib_vs_no_fib(df: pd.DataFrame, args):
    """Run backtest with and without Fibonacci and compare."""
    print("\n" + "="*60)
    print("📊 COMPARING FIBONACCI: WITH vs WITHOUT")
    print("="*60)
    
    # Run with Fibonacci
    print("\n🔄 Running with Fibonacci...")
    results_with = run_backtest(
        df, 
        horizon=args.horizon, 
        step=args.step, 
        use_fib=True
    )
    
    # Run without Fibonacci
    print("\n🔄 Running without Fibonacci...")
    results_without = run_backtest(
        df, 
        horizon=args.horizon, 
        step=args.step, 
        use_fib=False
    )
    
    # Compare
    print("\n" + "="*60)
    print("📊 COMPARISON RESULTS")
    print("="*60)
    
    if results_with.empty and results_without.empty:
        print("❌ No signals in either run.")
        return
    
    def get_stats(df):
        if df.empty:
            return {"signals": 0, "win_rate": 0, "avg_return": 0, "total_return": 0}
        return {
            "signals": len(df),
            "win_rate": (df["pct_return"] > 0).mean() * 100,
            "avg_return": df["pct_return"].mean(),
            "total_return": df["pct_return"].sum(),
        }
    
    with_stats = get_stats(results_with)
    without_stats = get_stats(results_without)
    
    print(f"\n{'Metric':<20} {'With Fibonacci':<20} {'Without Fibonacci':<20} {'Difference':<15}")
    print("-" * 75)
    print(f"{'Signals':<20} {with_stats['signals']:<20} {without_stats['signals']:<20} {with_stats['signals'] - without_stats['signals']:<+15}")
    print(f"{'Win Rate':<20} {with_stats['win_rate']:<19.1f}% {without_stats['win_rate']:<19.1f}% {with_stats['win_rate'] - without_stats['win_rate']:<+14.1f}%")
    print(f"{'Avg Return':<20} {with_stats['avg_return']:<19.3f}% {without_stats['avg_return']:<19.3f}% {with_stats['avg_return'] - without_stats['avg_return']:<+15.3f}%")
    print(f"{'Total Return':<20} {with_stats['total_return']:<19.3f}% {without_stats['total_return']:<19.3f}% {with_stats['total_return'] - without_stats['total_return']:<+15.3f}%")
    
    # Determine which is better
    if with_stats['total_return'] > without_stats['total_return']:
        print("\n✅ Fibonacci IMPROVES performance")
    elif with_stats['total_return'] < without_stats['total_return']:
        print("\n❌ Fibonacci HURTS performance")
    else:
        print("\n⚠️ Fibonacci makes no significant difference")


def run_per_strategy_backtest(df: pd.DataFrame, args):
    """Run each strategy individually and report performance."""
    print("\n" + "="*60)
    print("📊 PER-STRATEGY BACKTEST")
    print("="*60)
    
    strategies = [
        ("trend_following", trend_following),
        ("breakout", breakout),
        ("ma_crossover", ma_crossover),
        ("mean_reversion", mean_reversion),
        ("smc", smc),
    ]
    
    import ta
    atr_series = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
    min_candles = 205
    horizon = args.horizon
    step = args.step
    
    all_results = {}
    
    for name, strategy_func in strategies:
        print(f"\n🔄 Testing {name}...")
        records = []
        
        for i in range(min_candles, len(df) - horizon, step):
            df_slice = df.iloc[: i + 1]
            
            try:
                result = strategy_func(df_slice)
                
                if result.buy_score_raw == 0 and result.sell_score_raw == 0:
                    continue
                
                # Determine direction
                if result.buy_score_raw > result.sell_score_raw:
                    direction = "BUY"
                    score = result.buy_score_raw
                elif result.sell_score_raw > result.buy_score_raw:
                    direction = "SELL"
                    score = result.sell_score_raw
                else:
                    continue
                
                atr_val = atr_series.iloc[i]
                if pd.isna(atr_val) or atr_val <= 0:
                    continue
                
                entry_price = df["close"].iloc[i]
                if direction == "BUY":
                    stop_loss = entry_price - atr_val * 1.5
                    take_profit = entry_price + atr_val * 3.0
                else:
                    stop_loss = entry_price + atr_val * 1.5
                    take_profit = entry_price - atr_val * 3.0
                
                fwd = forward_return(df, i, direction, horizon, stop_loss, take_profit)
                
                records.append({
                    "index": i,
                    "direction": direction,
                    "score": score,
                    "outcome": fwd["outcome"],
                    "pct_return": fwd["pct_return"],
                })
                
            except Exception as e:
                continue
        
        if records:
            results_df = pd.DataFrame(records)
            win_rate = (results_df["pct_return"] > 0).mean() * 100
            avg_return = results_df["pct_return"].mean()
            total_return = results_df["pct_return"].sum()
            all_results[name] = {
                "signals": len(records),
                "win_rate": win_rate,
                "avg_return": avg_return,
                "total_return": total_return,
            }
            print(f"   Signals: {len(records)}, Win Rate: {win_rate:.1f}%, Avg Return: {avg_return:+.3f}%")
        else:
            print(f"   No signals generated")
            all_results[name] = {"signals": 0, "win_rate": 0, "avg_return": 0, "total_return": 0}
    
    # Summary
    print("\n" + "="*60)
    print("📊 PER-STRATEGY SUMMARY")
    print("="*60)
    print(f"\n{'Strategy':<20} {'Signals':<10} {'Win Rate':<12} {'Avg Return':<15} {'Total Return':<15}")
    print("-" * 75)
    for name, stats in all_results.items():
        print(f"{name:<20} {stats['signals']:<10} {stats['win_rate']:<11.1f}% {stats['avg_return']:<14.3f}% {stats['total_return']:<14.3f}%")
    
    # Best strategy
    best = max(all_results.items(), key=lambda x: x[1]['total_return'] if x[1]['signals'] > 0 else -999)
    if best[1]['signals'] > 0:
        print(f"\n🏆 Best strategy: {best[0]} (Total Return: {best[1]['total_return']:.3f}%)")
    else:
        print("\n❌ No strategy generated any signals")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backtest the crypto bot")
    parser.add_argument("--symbol", default="BTCUSDT", help="Trading pair")
    parser.add_argument("--timeframe", default="5m", help="Timeframe")
    parser.add_argument("--db", default="crypto_bot.db", help="Database path")
    parser.add_argument("--horizon", type=int, default=12, help="Candles to hold")
    parser.add_argument("--step", type=int, default=5, help="Evaluate every Nth candle")
    parser.add_argument("--compare-fib", action="store_true", help="Compare Fibonacci on/off")
    parser.add_argument("--per-strategy", action="store_true", help="Test each strategy individually")
    args = parser.parse_args()

    df = load_history(args.db, args.symbol, args.timeframe)
    print(f"📊 Loaded {len(df)} candles for {args.symbol} {args.timeframe}")

    if len(df) < 250:
        print("❌ Not enough history yet for a meaningful backtest - keep collecting data and retry later.")
        sys.exit(0)

    if args.compare_fib:
        compare_fib_vs_no_fib(df, args)
    elif args.per_strategy:
        run_per_strategy_backtest(df, args)
    else:
        # Standard backtest with Fibonacci (default)
        print(f"\n📊 Running backtest with Fibonacci {'ENABLED' if config.USE_FIBONACCI else 'DISABLED'}")
        results = run_backtest(df, horizon=args.horizon, step=args.step, use_fib=config.USE_FIBONACCI)
        summarize(results, args.symbol, config.USE_FIBONACCI)