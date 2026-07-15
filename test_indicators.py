# ============================================================
#  TEST INDICATORS - Using the first available coin
# ============================================================

import sqlite3
import pandas as pd
from src.indicators import RSI, MACD, EMA, SuperTrend, BollingerBands

# Load data from database
def load_data(symbol, timeframe='1h', limit=200):
    """
    Load OHLCV data for a specific symbol and timeframe.
    
    Args:
        symbol: Trading pair (e.g., 'BTCUSDT', 'DOGEUSDT')
        timeframe: Candle timeframe ('5m', '15m', '1h', '4h', '1d')
        limit: Number of candles to load
    
    Returns:
        DataFrame with columns: timestamp, open, high, low, close, volume
    """
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

def get_first_coin():
    """Get the first available coin from the database."""
    conn = sqlite3.connect('crypto_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT symbol FROM price_data LIMIT 1;")
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def get_coin_count():
    """Get the number of unique coins in the database."""
    conn = sqlite3.connect('crypto_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT symbol) FROM price_data;")
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

print("=" * 60)
print("🧪 TESTING INDICATORS")
print("=" * 60)

# Get the first available coin
symbol = get_first_coin()
total_coins = get_coin_count()

if not symbol:
    print("❌ No data found in database.")
    print("💡 Let the bot run for a few minutes to collect data first.")
    print("   Then run: python test_indicators.py")
    exit()

print(f"📊 Found {total_coins} coins in database")
print(f"📈 Using coin: {symbol}")
print("-" * 60)

# Load data for different timeframes
timeframes = ['5m', '15m', '1h']
data_loaded = {}

for tf in timeframes:
    data = load_data(symbol, tf, 200)
    if len(data) > 0:
        data_loaded[tf] = data
        print(f"✅ Loaded {len(data)} candles for {symbol} ({tf})")
    else:
        print(f"⚠️ No data for {symbol} ({tf})")

if not data_loaded:
    print("❌ No data found for any timeframe.")
    print("💡 Make sure the bot is running and collecting data.")
    exit()

print("-" * 60)
print("📊 CALCULATING INDICATORS")
print("-" * 60)

# Test indicators on the first available timeframe
tf = list(data_loaded.keys())[0]
data = data_loaded[tf]
print(f"Using timeframe: {tf}")
print(f"Data points: {len(data)}")

try:
    # Test RSI
    rsi = RSI(period=14)
    rsi_result = rsi.calculate(data)
    print(f"✅ RSI (14): {rsi_result.iloc[-1]:.2f}")

    # Test MACD
    macd = MACD()
    macd_result = macd.calculate(data)
    print(f"✅ MACD Histogram: {macd_result.iloc[-1]:.6f}")

    # Test EMA (20)
    ema_20 = EMA(period=20)
    ema_20_result = ema_20.calculate(data)
    print(f"✅ EMA (20): {ema_20_result.iloc[-1]:.4f}")

    # Test EMA (50)
    ema_50 = EMA(period=50)
    ema_50_result = ema_50.calculate(data)
    print(f"✅ EMA (50): {ema_50_result.iloc[-1]:.4f}")

    # Test SuperTrend
    st = SuperTrend(period=10, multiplier=3.0)
    st_result = st.calculate(data)
    trend = "UPTREND" if st_result.iloc[-1] == 1 else "DOWNTREND" if st_result.iloc[-1] == -1 else "NEUTRAL"
    print(f"✅ SuperTrend: {st_result.iloc[-1]} ({trend})")

    # Test Bollinger Bands
    bb = BollingerBands(period=20, std_dev=2.0)
    bb_result = bb.calculate(data)
    print(f"✅ Bollinger Bands Position: {bb_result.iloc[-1]:.2f} (0=lower, 1=upper)")

    print("-" * 60)
    print("✅ ALL INDICATORS CALCULATED SUCCESSFULLY!")
    
    # Show summary of current market state
    print("\n📊 MARKET STATE SUMMARY")
    print("-" * 60)
    
    # Determine trend direction
    ema_20_val = ema_20_result.iloc[-1]
    ema_50_val = ema_50_result.iloc[-1]
    ema_trend = "BULLISH" if ema_20_val > ema_50_val else "BEARISH"
    
    rsi_val = rsi_result.iloc[-1]
    rsi_status = "Overbought" if rsi_val > 70 else "Oversold" if rsi_val < 30 else "Neutral"
    
    macd_val = macd_result.iloc[-1]
    macd_status = "Bullish" if macd_val > 0 else "Bearish"
    
    print(f"💰 Symbol: {symbol}")
    print(f"📅 Latest Price: {data['close'].iloc[-1]:.4f}")
    print(f"📈 Trend: {ema_trend} (EMA20 {ema_20_val:.4f} > EMA50 {ema_50_val:.4f})")
    print(f"📊 RSI: {rsi_val:.2f} ({rsi_status})")
    print(f"📉 MACD: {macd_status} ({macd_val:.6f})")
    print(f"📈 SuperTrend: {trend}")
    
    print("\n" + "=" * 60)
    print("🎉 INDICATORS ARE WORKING PROPERLY!")
    print("=" * 60)
    
except Exception as e:
    print(f"❌ Error calculating indicators: {e}")
    import traceback
    traceback.print_exc()