# ============================================================
#  TEST STRATEGIES - All 5 strategies
# ============================================================

import sqlite3
import pandas as pd
from src.strategies import (
    TrendFollowingStrategy,
    BreakoutStrategy,
    MACrossoverStrategy,
    MeanReversionStrategy,
    SMCStrategy,
)

def load_data(symbol, timeframe='5m', limit=200):
    conn = sqlite3.connect('crypto_bot.db')
    query = f"""
        SELECT timestamp, open, high, low, close, volume
        FROM price_data
        WHERE symbol = '{symbol}' AND timeframe = '{timeframe}'
        ORDER BY timestamp ASC
        LIMIT {limit}
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

print("=" * 60)
print("🧪 TESTING ALL 5 STRATEGIES")
print("=" * 60)

# Get first available coin
conn = sqlite3.connect('crypto_bot.db')
cursor = conn.cursor()
cursor.execute("SELECT DISTINCT symbol FROM price_data LIMIT 1;")
result = cursor.fetchone()
conn.close()

if not result:
    print("❌ No data found")
    exit()

symbol = result[0]
print(f"📈 Using coin: {symbol}")
print(f"📊 Timeframe: 5m")

data = load_data(symbol, '5m', 200)
print(f"✅ Loaded {len(data)} candles")

if len(data) < 50:
    print("❌ Not enough data")
    exit()

print("-" * 60)
print("📊 EVALUATING ALL 5 STRATEGIES")
print("-" * 60)

# Initialize all 5 strategies
strategies = [
    TrendFollowingStrategy(),
    BreakoutStrategy(),
    MACrossoverStrategy(),
    MeanReversionStrategy(),
    SMCStrategy(),
]

results = {}
for strategy in strategies:
    print(f"\n📈 {strategy.name}:")
    score, direction, details = strategy.evaluate(data)
    results[strategy.name] = {'score': score, 'direction': direction, 'details': details}
    
    print(f"   Score: {score:.2f}/10")
    print(f"   Direction: {direction}")
    print(f"   Reasons: {', '.join(details.get('reasons', ['No signal']))}")

print("\n" + "=" * 60)
print("📊 SUMMARY")
print("=" * 60)

# Find best score
best = max(results.items(), key=lambda x: x[1]['score'])
print(f"🏆 Best strategy: {best[0]} (Score: {best[1]['score']:.2f}, Direction: {best[1]['direction']})")

# Count directions
buy_count = sum(1 for r in results.values() if r['direction'] == 'BUY')
sell_count = sum(1 for r in results.values() if r['direction'] == 'SELL')
neutral_count = sum(1 for r in results.values() if r['direction'] == 'NEUTRAL')

print(f"📊 Votes: BUY: {buy_count}, SELL: {sell_count}, NEUTRAL: {neutral_count}")

if buy_count > sell_count and buy_count > neutral_count:
    print("✅ Overall Signal: BUY")
elif sell_count > buy_count and sell_count > neutral_count:
    print("✅ Overall Signal: SELL")
else:
    print("⏸️ Overall Signal: NEUTRAL")

print("=" * 60)