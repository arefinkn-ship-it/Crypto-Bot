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
print("🔍 DEBUG - MULTI-TIMEFRAME CHECK")
print("=" * 60)

# Load data
conn = sqlite3.connect('crypto_bot.db')

df_5m = pd.read_sql("SELECT * FROM price_data WHERE symbol='BTCUSDT' AND timeframe='5m' ORDER BY timestamp DESC LIMIT 300", conn)
df_h1 = pd.read_sql("SELECT * FROM price_data WHERE symbol='BTCUSDT' AND timeframe='1h' ORDER BY timestamp DESC LIMIT 200", conn)
df_15m = pd.read_sql("SELECT * FROM price_data WHERE symbol='BTCUSDT' AND timeframe='15m' ORDER BY timestamp DESC LIMIT 200", conn)
conn.close()

print(f"✅ 5m: {len(df_5m)} candles")
print(f"✅ H1: {len(df_h1)} candles")
print(f"✅ 15m: {len(df_15m)} candles")

# Reverse to ascending
df_5m = df_5m.sort_values('timestamp').reset_index(drop=True)
df_h1 = df_h1.sort_values('timestamp').reset_index(drop=True)
df_15m = df_15m.sort_values('timestamp').reset_index(drop=True)

# ===== CHECK H1 TREND =====
print("\n" + "=" * 60)
print("📊 H1 TREND")
print("=" * 60)

h1_trend = get_trend_direction(df_h1)
print(f"Direction: {h1_trend['direction']}")
print(f"Strength: {h1_trend.get('strength', 0)}")
print(f"EMA50: {h1_trend.get('ema50', 0)}")
print(f"EMA200: {h1_trend.get('ema200', 0)}")
print(f"Price: {h1_trend.get('price', 0)}")
if 'reason' in h1_trend:
    print(f"Reason: {h1_trend['reason']}")

# ===== CHECK 15m TREND =====
print("\n" + "=" * 60)
print("📊 15m TREND")
print("=" * 60)

m15_trend = get_trend_direction(df_15m)
print(f"Direction: {m15_trend['direction']}")
print(f"Strength: {m15_trend.get('strength', 0)}")
print(f"EMA50: {m15_trend.get('ema50', 0)}")
print(f"EMA200: {m15_trend.get('ema200', 0)}")
print(f"Price: {m15_trend.get('price', 0)}")
if 'reason' in m15_trend:
    print(f"Reason: {m15_trend['reason']}")

# ===== STRATEGY SCORES (5m) =====
print("\n" + "=" * 60)
print("📊 STRATEGY SCORES (5m)")
print("=" * 60)

tf = trend_following(df_5m)
br = breakout(df_5m)
mac = ma_crossover(df_5m)
mr = mean_reversion(df_5m)
smc_strat = smc(df_5m)

print(f"Trend Following: BUY={tf.buy_score_raw:.2f}, SELL={tf.sell_score_raw:.2f}")
print(f"Breakout:        BUY={br.buy_score_raw:.2f}, SELL={br.sell_score_raw:.2f}")
print(f"MA Crossover:    BUY={mac.buy_score_raw:.2f}, SELL={mac.sell_score_raw:.2f}")
print(f"Mean Reversion:  BUY={mr.buy_score_raw:.2f}, SELL={mr.sell_score_raw:.2f}")
print(f"SMC:             BUY={smc_strat.buy_score_raw:.2f}, SELL={smc_strat.sell_score_raw:.2f}")

# ===== COMBINED SIGNAL (5m only) =====
combined = combine_signals([tf, br, mac, mr, smc_strat])
print(f"\n📊 Combined Signal (5m only): {combined['direction']} (Score: {combined['total_score']:.2f})")
print(f"   Confluence count: {combined['confluence_count']}")
print(f"   Strategies agreeing: {combined.get('strategies_agreeing', [])}")

# ===== MULTI-TIMEFRAME SIGNAL =====
print("\n" + "=" * 60)
print("📊 MULTI-TIMEFRAME SIGNAL (H1 → 15m → 5m)")
print("=" * 60)

mt_signal = get_multi_timeframe_signal(
    h1_data=df_h1,
    m15_data=df_15m,
    m5_data=df_5m,
    m5_signals=combined
)

print(f"Direction: {mt_signal['direction']}")
print(f"Confidence: {mt_signal['confidence']}")
print(f"Score Boosted: {mt_signal['score_boosted']}")
print(f"Reason: {mt_signal['reason']}")
print(f"Alignment: {mt_signal['alignment']}")

# ===== FINAL VERDICT =====
print("\n" + "=" * 60)
print("📊 FINAL VERDICT")
print("=" * 60)

if combined['direction'] != 'NEUTRAL' and mt_signal['direction'] == 'NEUTRAL':
    print("❌ Multi-timeframe filter is BLOCKING this signal!")
    print(f"   Reason: {mt_signal['reason']}")
elif combined['direction'] != 'NEUTRAL' and mt_signal['direction'] != 'NEUTRAL':
    print(f"✅ Multi-timeframe PASSED: {mt_signal['direction']}")
    if mt_signal['score_boosted'] >= 7.0:
        print("   ✅ Score is high enough for Telegram alert!")
    else:
        print(f"   ❌ Score {mt_signal['score_boosted']:.2f} < 7.0 - would be filtered out")
        print("   → Try lowering MIN_SIGNAL_SCORE in .env")
else:
    print("No signal from 5m strategies.")

print("\n" + "=" * 60)
print("✅ Debug complete")
print("=" * 60)