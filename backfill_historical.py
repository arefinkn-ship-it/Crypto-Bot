import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.core.logger import logger
from src.data.binance_client import BinanceClient
from src.data.collector import DataCollector
from src.data.loader import DataLoader
from src.core.database import init_database

print("=" * 60)
print("📊 ONE-TIME HISTORICAL BACKFILL")
print("=" * 60)

# Initialize database
init_database()

# Get coins
loader = DataLoader()
client = BinanceClient()

# Get top 20 coins
coins = client.get_top_coins_by_volume(limit=20)
print(f"\n📈 Backfilling {len(coins)} coins...")

# Temporarily increase limit in collector
collector = DataCollector()

for symbol in coins:
    print(f"\n🔄 Backfilling {symbol}...")
    try:
        # For each timeframe
        for tf in ['5m', '15m', '1h']:
            print(f"   Fetching {tf}...")
            # Directly fetch and store
            data = client.fetch_ohlcv(symbol, tf, limit=500)
            if data:
                # Store using collector
                collector.collect_ohlcv(symbol, tf)
        print(f"   ✅ Done")
    except Exception as e:
        print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
print("✅ Backfill complete")
print("=" * 60)