import sqlite3
from datetime import datetime

def check_database():
    conn = sqlite3.connect('crypto_bot.db')
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("📊 DATABASE STATUS")
    print("="*60)
    
    # Count price data
    cursor.execute("SELECT COUNT(*) FROM price_data;")
    total_candles = cursor.fetchone()[0]
    print(f"📈 Total candles stored: {total_candles:,}")
    
    # Count market data
    cursor.execute("SELECT COUNT(*) FROM market_data;")
    total_market = cursor.fetchone()[0]
    print(f"📊 Market updates: {total_market:,}")
    
    # Top 10 coins
    cursor.execute("""
        SELECT symbol, COUNT(*) 
        FROM price_data 
        GROUP BY symbol 
        ORDER BY COUNT(*) DESC 
        LIMIT 10;
    """)
    print("\n🏆 Top 10 coins by data:")
    for symbol, count in cursor.fetchall():
        print(f"   {symbol}: {count:,} candles")
    
    # Latest data
    cursor.execute("""
        SELECT symbol, MAX(timestamp), COUNT(*) 
        FROM price_data 
        GROUP BY symbol 
        ORDER BY MAX(timestamp) DESC 
        LIMIT 5;
    """)
    print("\n🕐 Latest data:")
    for symbol, timestamp, count in cursor.fetchall():
        print(f"   {symbol}: {timestamp} ({count} candles)")
    
    conn.close()

if __name__ == "__main__":
    check_database()