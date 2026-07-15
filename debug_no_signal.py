import sys
sys.path.insert(0, r'C:\Users\HP\OneDrive\Desktop\crypto-bot')

import sqlite3
import pandas as pd
from src.strategies.trend_following import trend_following
from src.strategies.breakout import breakout
from src.strategies.ma_crossover import ma_crossover
from src.strategies.mean_reversion import mean_reversion
from src.strategies.smc import smc

print("=" * 60)
print("🔍 DEBUG - CHECKING SIGNAL GENERATION")
print("=" * 60)

# Check database for signals
conn = sqlite3.connect('crypto_bot.db')
cursor = conn.cursor()

# Count signals
cursor.execute("SELECT COUNT(*) FROM signals")
signal_count = cursor.fetchone()[0]
print(f"📊 Total signals in database: {signal_count}")

# Get latest signals
cursor.execute("SELECT symbol, direction, total_score, confidence FROM signals ORDER BY timestamp DESC LIMIT 5")
rows = cursor.fetchall()
if rows:
    print("📊 Latest signals:")
    for row in rows:
        print(f"   {row[0]}: {row[1]} ({row[2]:.2f}/10) - {row[3]}")
else:
    print("📊 No signals found")

# Check strategy scores on BTCUSDT
print("\n" + "=" * 60)
print("📊 STRATEGY SCORES ON BTCUSDT")
print("=" * 60)

df = pd.read_sql("SELECT * FROM price_data WHERE symbol='BTCUSDT' AND timeframe='5m' ORDER BY timestamp DESC LIMIT 300", conn)
conn.close()

if len(df) >= 200:
    print(f"✅ Loaded {len(df)} candles")
    
    # Reverse to ascending for strategies
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    tf = trend_following(df)
    br = breakout(df)
    mac = ma_crossover(df)
    mr = mean_reversion(df)
    smc_strat = smc(df)
    
    print(f"\n📈 Strategy Scores:")
    print(f"   Trend Following: BUY={tf.buy_score_raw:.2f}, SELL={tf.sell_score_raw:.2f}")
    print(f"   Breakout:        BUY={br.buy_score_raw:.2f}, SELL={br.sell_score_raw:.2f}")
    print(f"   MA Crossover:    BUY={mac.buy_score_raw:.2f}, SELL={mac.sell_score_raw:.2f}")
    print(f"   Mean Reversion:  BUY={mr.buy_score_raw:.2f}, SELL={mr.sell_score_raw:.2f}")
    print(f"   SMC:             BUY={smc_strat.buy_score_raw:.2f}, SELL={smc_strat.sell_score_raw:.2f}")
    
    # Combine signals
    from src.signals.signal_combiner import combine_signals
    combined = combine_signals([tf, br, mac, mr, smc_strat])
    print(f"\n📊 Combined Signal: {combined['direction']} (Score: {combined['total_score']:.2f})")
else:
    print(f"❌ Not enough data: {len(df)} candles needed 200+")

print("\n" + "=" * 60)
print("✅ Debug complete")
print("=" * 60)