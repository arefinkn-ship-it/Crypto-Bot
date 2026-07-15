import sys
sys.path.insert(0, r'C:\Users\HP\OneDrive\Desktop\crypto-bot')

import sqlite3
import pandas as pd
from src.signals.multi_timeframe import get_trend_direction

print("=" * 60)
print("🔍 CHECKING ALL COINS FOR H1 TREND ALIGNMENT")
print("=" * 60)

conn = sqlite3.connect('crypto_bot.db')
cursor = conn.cursor()
cursor.execute('SELECT DISTINCT symbol FROM price_data WHERE timeframe="5m" LIMIT 30')
symbols = [row[0] for row in cursor.fetchall()]
conn.close()

print(f"📊 Checking {len(symbols)} coins...\n")

found = 0
for symbol in symbols:
    try:
        conn = sqlite3.connect('crypto_bot.db')
        df = pd.read_sql(f'SELECT * FROM price_data WHERE symbol="{symbol}" AND timeframe="1h" ORDER BY timestamp DESC LIMIT 50', conn)
        conn.close()
        if len(df) >= 30:
            trend = get_trend_direction(df, lookback=30, ema_fast=20, ema_slow=50)
            if trend['direction'] != 'NEUTRAL':
                print(f"  {symbol}: {trend['direction']} (strength: {trend['strength']})")
                found += 1
    except Exception as e:
        pass

if found == 0:
    print("❌ No coins with clear H1 trend found.")
    print("   Try running the bot to collect more data first.")
else:
    print(f"\n✅ Found {found} coins with clear H1 trend")

print("\n" + "=" * 60)
print("✅ Complete")
print("=" * 60)