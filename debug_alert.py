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
from src.signals.alert import AlertManager
from src.core.config import config
from src.utils.fibonacci_manager import FibonacciManager

print("=" * 60)
print("🔍 DEBUGGING ALLOUSDT ALERT")
print("=" * 60)

# Load ALLOUSDT data
conn = sqlite3.connect('crypto_bot.db')

df_5m = pd.read_sql("SELECT * FROM price_data WHERE symbol='ALLOUSDT' AND timeframe='5m' ORDER BY timestamp DESC LIMIT 300", conn)
df_h1 = pd.read_sql("SELECT * FROM price_data WHERE symbol='ALLOUSDT' AND timeframe='1h' ORDER BY timestamp DESC LIMIT 50", conn)
df_15m = pd.read_sql("SELECT * FROM price_data WHERE symbol='ALLOUSDT' AND timeframe='15m' ORDER BY timestamp DESC LIMIT 200", conn)
conn.close()

print(f"✅ 5m: {len(df_5m)} candles")
print(f"✅ H1: {len(df_h1)} candles")
print(f"✅ 15m: {len(df_15m)} candles")

# Reverse to ascending
df_5m = df_5m.sort_values('timestamp').reset_index(drop=True)
df_h1 = df_h1.sort_values('timestamp').reset_index(drop=True)
df_15m = df_15m.sort_values('timestamp').reset_index(drop=True)

# ===== H1 TREND =====
h1_trend = get_trend_direction(df_h1, lookback=30, ema_fast=20, ema_slow=50)
print(f"\n📊 H1 Trend: {h1_trend['direction']} (strength: {h1_trend['strength']})")

# ===== 15m TREND =====
m15_trend = get_trend_direction(df_15m, lookback=30, ema_fast=20, ema_slow=50)
print(f"📊 15m Trend: {m15_trend['direction']} (strength: {m15_trend['strength']})")

# ===== STRATEGY SCORES =====
print("\n📊 Strategy Scores (5m):")

tf = trend_following(df_5m)
br = breakout(df_5m)
mac = ma_crossover(df_5m)
mr = mean_reversion(df_5m)
smc_strat = smc(df_5m)

print(f"   Trend Following: BUY={tf.buy_score_raw:.2f}, SELL={tf.sell_score_raw:.2f}")
print(f"   Breakout:        BUY={br.buy_score_raw:.2f}, SELL={br.sell_score_raw:.2f}")
print(f"   MA Crossover:    BUY={mac.buy_score_raw:.2f}, SELL={mac.sell_score_raw:.2f}")
print(f"   Mean Reversion:  BUY={mr.buy_score_raw:.2f}, SELL={mr.sell_score_raw:.2f}")
print(f"   SMC:             BUY={smc_strat.buy_score_raw:.2f}, SELL={smc_strat.sell_score_raw:.2f}")

# ===== COMBINED SIGNAL =====
combined = combine_signals([tf, br, mac, mr, smc_strat])
print(f"\n📊 Combined Signal: {combined['direction']} (Score: {combined['total_score']:.2f})")
print(f"   Confluence count: {combined['confluence_count']}")
print(f"   Strategies agreeing: {combined.get('strategies_agreeing', [])}")

# ===== MULTI-TIMEFRAME SIGNAL =====
mt_signal = get_multi_timeframe_signal(
    h1_data=df_h1,
    m15_data=df_15m,
    m5_data=df_5m,
    m5_signals=combined
)

print(f"\n📊 Multi-Timeframe Signal: {mt_signal['direction']}")
print(f"   Confidence: {mt_signal['confidence']}")
print(f"   Score Boosted: {mt_signal['score_boosted']}")
print(f"   Reason: {mt_signal['reason']}")

# ===== CHECK SCORE AGAINST THRESHOLD =====
score = mt_signal['score_boosted']
threshold = config.MIN_SIGNAL_SCORE

print(f"\n📊 Score Check: {score} >= {threshold}? {score >= threshold}")

if score >= threshold:
    print("   ✅ Score passes threshold!")
else:
    print(f"   ❌ Score {score} < {threshold} - would be filtered out by main.py")

# ===== CHECK ALERT MANAGER =====
print("\n📊 Alert Manager Check:")
alerts = AlertManager()
print(f"   Token: {alerts.token[:10]}...{alerts.token[-4:] if alerts.token else 'None'}")
print(f"   Chat ID: {alerts.chat_id[:4] if alerts.chat_id else 'None'}...")

# ===== SIMULATE SENDING ALERT =====
if mt_signal['direction'] != 'NEUTRAL' and score >= threshold:
    print("\n📊 Attempting to send test alert...")
    
    # Build signal dict like main.py
    signal = {
        'symbol': 'ALLOUSDT',
        'signal': mt_signal['direction'],
        'confidence': mt_signal['confidence'],
        'score': score,
        'latest_price': df_5m['close'].iloc[-1],
        'timestamp': df_5m['timestamp'].iloc[-1],
        'reason': mt_signal['reason'],
        'h1_trend': h1_trend,
        'm15_trend': m15_trend,
        'alignment': mt_signal['alignment'],
        'strategies': combined.get('strategies', {}),
        'fibonacci_levels': FibonacciManager().get_trade_levels(
            direction=mt_signal['direction'],
            entry_price=df_5m['close'].iloc[-1],
            data=df_5m
        ),
    }
    
    print("   Signal dictionary built:")
    print(f"      Symbol: {signal['symbol']}")
    print(f"      Direction: {signal['signal']}")
    print(f"      Score: {signal['score']}")
    
    print("\n   Sending to Telegram...")
    result = alerts.send_alert(signal)
    if result:
        print("   ✅ Alert sent successfully! Check Telegram.")
    else:
        print("   ❌ Alert failed to send.")
        print("   Check Telegram token and chat ID in .env")
else:
    print("\n⏸️ Signal does not meet criteria for sending.")
    if mt_signal['direction'] == 'NEUTRAL':
        print("   - Direction is NEUTRAL")
    if score < threshold:
        print(f"   - Score {score} < threshold {threshold}")

print("\n" + "=" * 60)
print("✅ Debug complete")
print("=" * 60)