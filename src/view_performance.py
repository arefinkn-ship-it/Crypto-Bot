#!/usr/bin/env python3
# ============================================================
#  PERFORMANCE REPORT - run this anytime to see how the bot's
#  actual alerted signals have performed.
#  Usage: python view_performance.py
# ============================================================

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.data.loader import DataLoader
from src.signals.trade_tracker import TradeTracker


def main():
    loader = DataLoader()
    tracker = TradeTracker()

    print("Checking open trades against latest price data...")
    updated = tracker.check_and_update(loader)
    print(f"Closed {updated} trade(s) this check.\n")

    summary = tracker.summary()

    print("=" * 50)
    print("PERFORMANCE SUMMARY")
    print("=" * 50)

    if summary["total_closed"] == 0:
        print(summary.get("message", "No closed trades yet"))
        print(f"Open trades still tracking: {summary['open']}")
        return

    print(f"Closed trades:  {summary['total_closed']}")
    print(f"Open trades:    {summary['open']}")
    print(f"Win rate:       {summary['win_rate_pct']}%")
    print(f"Avg return:     {summary['avg_return_pct']:+.3f}%")
    print(f"TP hit:         {summary['tp_hit_count']}")
    print(f"SL hit:         {summary['sl_hit_count']}")
    print(f"Timeout:        {summary['timeout_count']}")

    if summary.get("by_confidence"):
        print("\n--- By confidence tier ---")
        for tier, stats in summary["by_confidence"].items():
            print(f"{tier:8s} n={stats['n']:3d}  win_rate={stats['win_rate_pct']:5.1f}%  "
                  f"avg_return={stats['avg_return_pct']:+.3f}%")

    print("=" * 50)
    print(f"Full trade log: logs/trades.csv")


if __name__ == "__main__":
    main()