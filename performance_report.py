#!/usr/bin/env python3
# ============================================================
#  PERFORMANCE REPORT - View bot performance
# ============================================================

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.performance.tracker import PerformanceTracker
import argparse


def main():
    parser = argparse.ArgumentParser(description='View bot performance')
    parser.add_argument('--days', type=int, default=7, help='Days to look back')
    parser.add_argument('--symbol', type=str, help='Filter by symbol')
    parser.add_argument('--recent', type=int, default=10, help='Recent trades to show')
    parser.add_argument('--by-symbol', action='store_true', help='Show performance by symbol')
    parser.add_argument('--by-confidence', action='store_true', help='Show performance by confidence')
    args = parser.parse_args()
    
    tracker = PerformanceTracker()
    
    print("=" * 60)
    print(f"📊 PERFORMANCE SUMMARY (Last {args.days} days)")
    if args.symbol:
        print(f"   Symbol: {args.symbol}")
    print("=" * 60)
    
    summary = tracker.get_summary(args.days, args.symbol)
    
    if summary.get('total_trades', 0) == 0:
        print("\n❌ No closed trades in this period")
        return
    
    print(f"\n📈 Total Trades: {summary['total_trades']}")
    print(f"   Wins: {summary['wins']}")
    print(f"   Losses: {summary['losses']}")
    print(f"   Win Rate: {summary['win_rate']:.1f}%")
    print(f"   Total P&L: ${summary['total_pnl']:.2f}")
    print(f"   Avg Return: {summary['avg_return']:.2f}%")
    print(f"   Avg Signal Score: {summary.get('avg_score', 0):.1f}/10")
    print(f"   Best Trade: {summary['best_trade']:.2f}%")
    print(f"   Worst Trade: {summary['worst_trade']:.2f}%")
    
    if args.recent > 0:
        print("\n" + "=" * 60)
        print(f"📋 RECENT TRADES (Last {args.recent})")
        print("=" * 60)
        
        df = tracker.get_recent_trades(args.recent)
        if not df.empty:
            print(f"\n{'ID':<5} {'Symbol':<10} {'Direction':<8} {'Entry':<12} {'Exit':<12} {'P&L %':<8} {'Outcome':<8} {'Score':<6}")
            print("-" * 80)
            for _, row in df.iterrows():
                pnl_str = f"{row['pnl_pct']:+.2f}%" if row['pnl_pct'] else "N/A"
                score_str = f"{row['score']:.1f}" if row['score'] else "N/A"
                print(f"{row['id']:<5} {row['symbol']:<10} {row['direction']:<8} ${row['entry_price']:<11.2f} ${row['exit_price']:<11.2f} {pnl_str:<8} {row['outcome']:<8} {score_str:<6}")
    
    if args.by_symbol:
        print("\n" + "=" * 60)
        print("📊 PERFORMANCE BY SYMBOL")
        print("=" * 60)
        
        df = tracker.get_performance_by_symbol(args.days)
        if not df.empty:
            print(f"\n{'Symbol':<10} {'Trades':<8} {'Wins':<6} {'Win Rate':<10} {'Avg Return':<12} {'Total P&L':<12}")
            print("-" * 65)
            for _, row in df.iterrows():
                print(f"{row['symbol']:<10} {row['trades']:<8} {row['wins']:<6} {row['win_rate']:<9.1f}% {row['avg_return']:<11.2f}% ${row['total_pnl']:<11.2f}")
    
    if args.by_confidence:
        print("\n" + "=" * 60)
        print("📊 PERFORMANCE BY CONFIDENCE")
        print("=" * 60)
        
        df = tracker.get_performance_by_confidence(args.days)
        if not df.empty:
            print(f"\n{'Confidence':<10} {'Trades':<8} {'Wins':<6} {'Win Rate':<10} {'Avg Return':<12} {'Total P&L':<12}")
            print("-" * 65)
            for _, row in df.iterrows():
                print(f"{row['confidence']:<10} {row['trades']:<8} {row['wins']:<6} {row['win_rate']:<9.1f}% {row['avg_return']:<11.2f}% ${row['total_pnl']:<11.2f}")


if __name__ == "__main__":
    main()