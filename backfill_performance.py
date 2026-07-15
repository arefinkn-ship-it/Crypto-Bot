#!/usr/bin/env python3
# ============================================================
#  BACKFILL PERFORMANCE - Simulate past signals
# ============================================================

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import sqlite3
from src.performance.tracker import PerformanceTracker
from src.core.logger import logger

print("=" * 60)
print("🔄 BACKFILLING PAST SIGNALS")
print("=" * 60)

tracker = PerformanceTracker()
conn = sqlite3.connect('crypto_bot.db')
cursor = conn.cursor()

# Get signals from the last 30 days with entry prices
cursor.execute("""
    SELECT id, symbol, direction, entry_price, timestamp, total_score, confidence, signal_data
    FROM signals
    WHERE direction != 'NEUTRAL' AND entry_price IS NOT NULL
    ORDER BY timestamp DESC
    LIMIT 500
""")
signals = cursor.fetchall()
conn.close()

print(f"📊 Found {len(signals)} past signals")

processed = 0
errors = 0

for signal in signals:
    try:
        # Parse strategies from signal_data if available
        strategies = []
        if signal[7]:
            import json
            try:
                data = json.loads(signal[7])
                strategies = data.get('strategies_agreeing', [])
            except:
                pass
        
        signal_dict = {
            'symbol': signal[1],
            'signal': signal[2],
            'latest_price': signal[3],
            'timestamp': signal[4],
            'score': signal[5] if signal[5] else 0,
            'confidence': signal[6] if signal[6] else 'LOW',
            'strategies_agreeing': strategies,
        }
        
        trade_id = tracker.record_signal(signal_dict)
        result = tracker.simulate_forward(signal[1], trade_id, horizon=24)
        
        if 'error' not in result:
            processed += 1
            if processed % 10 == 0:
                print(f"   Processed {processed} signals...")
        else:
            errors += 1
            
    except Exception as e:
        errors += 1
        logger.debug(f"Error processing signal {signal[0]}: {e}")

print(f"\n✅ Backfill complete!")
print(f"   Processed: {processed}")
print(f"   Errors: {errors}")
print("=" * 60)