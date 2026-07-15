import sys
sys.path.insert(0, r'C:\Users\HP\OneDrive\Desktop\crypto-bot')

import sqlite3
import pandas as pd
from src.strategies.trend_following import trend_following
from src.strategies.breakout import breakout
from src.strategies.ma_crossover import ma_crossover
from src.strategies.mean_reversion import mean_reversion
from src.strategies.smc import smc
from src.signals.signal_combiner import combine_signals
from src.signals.multi_timeframe import get_trend_direction, get_multi_timeframe_signal

print("=" * 60)
print("🔍 CHECKING ALIGNED SIGNALS")
print("=" * 60)

conn = sqlite3.connect('crypto_bot.db')
cursor = conn.cursor()
cursor.execute('SELECT DISTINCT symbol FROM price_data WHERE timeframe="5m" LIMIT 30')
symbols = [row[0] for row in cursor.fetchall()]
conn.close()

print(f"📊 Checking {len(symbols)} coins...\n")

aligned_signals = []
total = 0

for symbol in symbols:
    try:
        # Load data
        conn = sqlite3.connect('crypto_bot.db')
        df_5m = pd.read_sql(f'SELECT * FROM price_data WHERE symbol="{symbol}" AND timeframe="5m" ORDER BY timestamp DESC LIMIT 300', conn)
        df_h1 = pd.read_sql(f'SELECT * FROM price_data WHERE symbol="{symbol}" AND timeframe="1h" ORDER BY timestamp DESC LIMIT 50', conn)
        df_15m = pd.read_sql(f'SELECT * FROM price_data WHERE symbol="{symbol}" AND timeframe="15m" ORDER BY timestamp DESC LIMIT 200', conn)
        conn.close()
        
        if len(df_5m) < 200 or len(df_h1) < 30:
            continue
        
        total += 1
        
        # Reverse to ascending
        df_5m = df_5m.sort_values('timestamp').reset_index(drop=True)
        df_h1 = df_h1.sort_values('timestamp').reset_index(drop=True)
        df_15m = df_15m.sort_values('timestamp').reset_index(drop=True)
        
        # Get H1 trend
        h1_trend = get_trend_direction(df_h1, lookback=30, ema_fast=20, ema_slow=50)
        
        # Evaluate 5m strategies
        tf = trend_following(df_5m)
        br = breakout(df_5m)
        mac = ma_crossover(df_5m)
        mr = mean_reversion(df_5m)
        smc_strat = smc(df_5m)
        
        combined = combine_signals([tf, br, mac, mr, smc_strat])
        
        # Check multi-timeframe
        mt_signal = get_multi_timeframe_signal(
            h1_data=df_h1,
            m15_data=df_15m,
            m5_data=df_5m,
            m5_signals=combined
        )
        
        if mt_signal['direction'] != 'NEUTRAL':
            aligned_signals.append({
                'symbol': symbol,
                'direction': mt_signal['direction'],
                'confidence': mt_signal['confidence'],
                'score': mt_signal['score_boosted'],
                'h1_trend': h1_trend['direction'],
                'reason': mt_signal['reason']
            })
            
    except Exception as e:
        pass

print(f"📊 Checked {total} coins with sufficient data\n")

if aligned_signals:
    print("=" * 60)
    print("✅ ALIGNED SIGNALS FOUND!")
    print("=" * 60)
    
    for signal in aligned_signals:
        print(f"\n📈 {signal['symbol']}")
        print(f"   Direction: {signal['direction']}")
        print(f"   Confidence: {signal['confidence']}")
        print(f"   Score: {signal['score']:.2f}/10")
        print(f"   H1 Trend: {signal['h1_trend']}")
        print(f"   Reason: {signal['reason']}")
        
        if signal['score'] >= 7.0:
            print("   ✅ Score is high enough for Telegram alert!")
        else:
            print(f"   ❌ Score {signal['score']:.2f} < 7.0 - would be filtered out")
else:
    print("❌ No aligned signals found.")
    print("   Try running the bot to collect more data, or check later.")

print("\n" + "=" * 60)
print("✅ Complete")
print("=" * 60)