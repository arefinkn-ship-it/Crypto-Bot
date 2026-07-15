# ============================================================
#  TEST SIGNAL FLOW - End-to-end signal generation
# ============================================================

from src.data.loader import DataLoader
from src.signals.scorer import SignalScorer
from src.signals.alert import AlertManager

print("=" * 60)
print("🧪 TESTING SIGNAL FLOW")
print("=" * 60)

# Initialize components
loader = DataLoader()
scorer = SignalScorer()
alerts = AlertManager()

# Load data
print("\n📊 Loading data...")
symbols_data = loader.load_all_symbols(timeframe='5m', limit=200, min_candles=50)

if not symbols_data:
    print("❌ No data found. Let the bot run for a while.")
    exit()

print(f"✅ Loaded {len(symbols_data)} symbols")

# Generate signals
print("\n📈 Generating signals...")
signals = scorer.evaluate_multiple(symbols_data)

# Filter strong signals
strong_signals = [s for s in signals if s['score'] >= 7.0 and s['signal'] != 'NEUTRAL']

if strong_signals:
    print(f"\n🔥 Found {len(strong_signals)} strong signals:")
    for signal in strong_signals[:10]:
        print(f"   {signal['symbol']}: {signal['signal']} ({signal['score']:.1f}/10) - {signal['confidence']}")
    
    # Send alert for the top signal
    print("\n📤 Sending alert for top signal...")
    top_signal = strong_signals[0]
    alerts.send_alert(top_signal)
    print("✅ Alert sent!")
else:
    print("\n⏸️ No strong signals found (score >= 7.0)")

print("\n" + "=" * 60)
print("✅ Test complete")