# ============================================================
#  TEST BINANCE FUTURES CONNECTION
#  Use this to verify your API connection works
# ============================================================

import ccxt
import socket
import time
import requests.packages.urllib3.util.connection as urllib3_cn

# Force Python to use IPv4 (fixes many connection issues)
def allowed_gateways():
    return socket.AF_INET

urllib3_cn.allowed_gateways = allowed_gateways

print("=" * 60)
print("🔌 TESTING BINANCE FUTURES CONNECTION")
print("=" * 60)

# Test 1: Basic connection to Binance
print("\n📡 Test 1: Basic connection...")
try:
    import requests
    response = requests.get('https://fapi.binance.com/fapi/v1/ping', timeout=10)
    print(f"   ✅ Binance ping: {response.status_code}")
except Exception as e:
    print(f"   ❌ Ping failed: {e}")

# Test 2: CCXT connection with futures
print("\n📡 Test 2: CCXT Futures connection...")

try:
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'timeout': 60000,  # 60 second timeout
        'options': {
            'defaultType': 'future',  # Use futures API
            'adjustForTimeDifference': True,
        }
    })
    
    print("   Loading futures markets...")
    start = time.time()
    
    # Load markets with timeout handling
    markets = exchange.load_markets()
    
    elapsed = time.time() - start
    print(f"   ✅ Loaded {len(markets)} futures markets in {elapsed:.1f} seconds")
    
    # Test 3: Fetch BTCUSDT ticker
    print("\n📡 Test 3: Fetch BTCUSDT futures price...")
    ticker = exchange.fetch_ticker('BTC/USDT')
    print(f"   ✅ BTC Futures Price: ${ticker['last']}")
    print(f"   📊 24h High: ${ticker['high']} | 24h Low: ${ticker['low']}")
    print(f"   📈 24h Change: {ticker['percentage']}%")
    
    # Test 4: Fetch funding rate
    print("\n📡 Test 4: Fetch funding rate...")
    funding = exchange.fetch_funding_rate('BTC/USDT')
    if funding:
        rate = funding.get('fundingRate', 0) * 100
        print(f"   ✅ Current funding rate: {rate:.4f}%")
    
    # Test 5: Fetch order book
    print("\n📡 Test 5: Fetch order book...")
    orderbook = exchange.fetch_order_book('BTC/USDT', limit=5)
    if orderbook:
        print(f"   ✅ Best bid: ${orderbook['bids'][0][0] if orderbook['bids'] else 'N/A'}")
        print(f"   ✅ Best ask: ${orderbook['asks'][0][0] if orderbook['asks'] else 'N/A'}")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - Connection is working!")
    print("=" * 60)
    
except ccxt.RequestTimeout as e:
    print(f"❌ TIMEOUT: {e}")
    print("\n💡 TROUBLESHOOTING:")
    print("   1. Check your internet connection")
    print("   2. Try adding your IP to Binance API whitelist")
    print("   3. Check if firewall is blocking the connection")
    print("   4. Try using a VPN if your ISP is blocking Binance")
    
except ccxt.NetworkError as e:
    print(f"❌ NETWORK ERROR: {e}")
    print("\n💡 TROUBLESHOOTING:")
    print("   1. Check if you can access: https://fapi.binance.com")
    print("   2. Your ISP might be blocking Binance")
    print("   3. Try using a different network")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    print(f"   Error type: {type(e).__name__}")
    
    # Show more details
    import traceback
    print("\n📋 Full traceback:")
    traceback.print_exc()
    
    print("\n💡 TROUBLESHOOTING:")
    print("   1. Make sure your Binance API key is valid")
    print("   2. Enable Futures permissions in API settings")
    print("   3. Add your IP to Binance API whitelist")
    print("   4. Check if you need to verify your Binance account")

print("\n" + "=" * 60)
print("🏁 Test complete")
print("=" * 60)