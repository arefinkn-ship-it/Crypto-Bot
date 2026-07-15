import sys
sys.path.insert(0, r'C:\Users\HP\OneDrive\Desktop\crypto-bot')

from src.core.config import config
from src.signals.alert import AlertManager
from src.data.loader import DataLoader
from src.strategies.trend_following import trend_following
from src.strategies.breakout import breakout
from src.strategies.mean_reversion import mean_reversion
from src.signals.signal_combiner import combine_signals
from src.signals.multi_timeframe import get_multi_timeframe_signal

print("=" * 60)
print("🔍 DEBUGGING ALERT FLOW")
print("=" * 60)

# Load data for DRAMUSDT (which had a signal earlier)
loader = DataLoader()
df_5m = loader.load_ohlcv('DRAMUSDT', '5m', limit=200)
df_h1 = loader.load_ohlcv('DRAMUSDT', '1h', limit=200)
df_15m = loader.load_ohlcv('DRAMUSDT', '15m', limit=200)

if len(df_5m) < 50:
    print("❌ Not enough data for DRAMUSDT")
    print("   Trying BTCUSDT instead...")
    df_5m = loader.load_ohlcv('BTCUSDT', '5m', limit=200)
    df_h1 = loader.load_ohlcv('BTCUSDT', '1h', limit=200)
    df_15m = loader.load_ohlcv('BTCUSDT', '15m', limit=200)

print(f"✅ Loaded {len(df_5m)} candles (5m)")

# Evaluate strategies
results = [
    trend_following(df_5m),
    breakout(df_5m),
    mean_reversion(df_5m),
]
combined = combine_signals(results)
print(f"\n📊 Combined Signal: {combined['direction']} (Score: {combined['total_score']})")

# Multi-timeframe
mt_signal = get_multi_timeframe_signal(
    h1_data=df_h1,
    m15_data=df_15m,
    m5_data=df_5m,
    m5_signals=combined
)
print(f"📊 Multi-Timeframe: {mt_signal['direction']} (Score: {mt_signal['score_boosted']})")

# Check if it would trigger an alert
if mt_signal['direction'] != 'NEUTRAL' and mt_signal['score_boosted'] >= config.MIN_SIGNAL_SCORE:
    print(f"\n✅ Signal would trigger alert! ({mt_signal['score_boosted']} >= {config.MIN_SIGNAL_SCORE})")
    
    # Build signal dict like main.py
    signal = {
        'symbol': 'DRAMUSDT',
        'signal': mt_signal['direction'],
        'confidence': mt_signal['confidence'],
        'score': mt_signal['score_boosted'],
        'latest_price': df_5m['close'].iloc[-1],
        'timestamp': df_5m['timestamp'].iloc[-1],
        'reason': mt_signal['reason'],
        'h1_trend': mt_signal['h1_trend'],
        'm15_trend': mt_signal['m15_trend'],
        'strategies': combined.get('strategies', {}),
    }
    
    # Send alert
    alerts = AlertManager()
    print("\n📤 Attempting to send alert...")
    result = alerts.send_alert(signal)
    print(f"📊 Result: {result}")
else:
    print(f"\n❌ Signal would NOT trigger alert ({mt_signal['score_boosted']} < {config.MIN_SIGNAL_SCORE})")
    print("   Check if the signal is above the threshold.")

print("\n" + "=" * 60)
print("✅ Debug complete")
print("=" * 60)