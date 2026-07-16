# ============================================================
#  BINANCE API CLIENT - WITH RETRY LOGIC & SYMBOL CLEANING
#  Fixed: Symbol format cleaned to remove :USDT suffix
# ============================================================

import ccxt
import time
from datetime import datetime
from typing import Dict, List, Optional
from src.core.config import config
from src.core.logger import logger

# Force IPv4
import socket
import requests.packages.urllib3.util.connection as urllib3_cn

def allowed_gateways():
    return socket.AF_INET

urllib3_cn.allowed_gateways = allowed_gateways


class BinanceClient:
    """Binance Futures API client with retry logic for network issues"""
    
    def __init__(self, retries: int = 3):
        """
        Initialize Binance Futures client with retry logic
        
        Args:
            retries: Number of connection attempts (default: 3)
        """
        self.exchange = None
        last_error = None
        
        for attempt in range(retries):
            try:
                logger.info(f"🔄 Connecting to Binance Futures (attempt {attempt+1}/{retries})...")
                
                self.exchange = ccxt.binance({
                    'enableRateLimit': True,
                    'timeout': 60000,
                    'options': {
                        'defaultType': 'future',
                    }
                })
                
                self.exchange.load_markets()
                logger.info("✅ Binance Futures client initialized successfully")
                return
                
            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ Attempt {attempt+1} failed: {e}")
                
                if attempt < retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.info(f"⏳ Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
        
        # If all retries failed
        logger.error(f"❌ Failed to initialize after {retries} attempts")
        raise last_error
    
    def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 500) -> List[Dict]:
        """Fetch OHLCV data for a symbol"""
        try:
            # Clean the symbol (remove any :USDT suffix and format correctly)
            clean_symbol = symbol.replace(':USDT', '').replace('/USDT', 'USDT')
            
            data = self.exchange.fetch_ohlcv(clean_symbol, timeframe, limit=limit)
            
            result = []
            for candle in data:
                result.append({
                    'timestamp': datetime.fromtimestamp(candle[0] / 1000),
                    'open': candle[1],
                    'high': candle[2],
                    'low': candle[3],
                    'close': candle[4],
                    'volume': candle[5],
                })
            return result
            
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV for {symbol}: {e}")
            return []
    
    def fetch_ticker(self, symbol: str) -> Optional[Dict]:
        """Fetch current ticker data"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'bid': ticker.get('bid', 0),
                'ask': ticker.get('ask', 0),
                'last': ticker.get('last', 0),
                'high': ticker.get('high', 0),
                'low': ticker.get('low', 0),
                'volume': ticker.get('quoteVolume', 0),
                'change_24h': ticker.get('percentage', 0),
            }
        except Exception as e:
            logger.error(f"Failed to fetch ticker for {symbol}: {e}")
            return None
    
    def fetch_funding_rate(self, symbol: str) -> Optional[Dict]:
        """Fetch current funding rate for futures"""
        try:
            funding = self.exchange.fetch_funding_rate(symbol)
            if funding:
                return {
                    'symbol': symbol,
                    'timestamp': datetime.now(),
                    'funding_rate': funding.get('fundingRate', 0),
                }
            return None
        except Exception as e:
            logger.debug(f"Funding rate not available for {symbol}: {e}")
            return None
    
    def fetch_open_interest(self, symbol: str) -> Optional[Dict]:
        """Fetch open interest for futures"""
        try:
            # Clean the symbol (remove any :USDT suffix)
            clean_symbol = symbol.replace(':USDT', '').replace('/USDT', 'USDT')
            oi = self.exchange.fetch_open_interest(clean_symbol)
            if oi:
                return {
                    'symbol': symbol,
                    'timestamp': datetime.now(),
                    'open_interest': oi.get('openInterestAmount', 0),
                    'open_interest_value': oi.get('openInterestValue', 0),
                }
            return None
        except Exception as e:
            logger.debug(f"Open interest not available for {symbol}: {e}")
            return None
    
    def fetch_order_book(self, symbol: str, depth: int = 20) -> Optional[Dict]:
        """Fetch order book depth"""
        try:
            orderbook = self.exchange.fetch_order_book(symbol, limit=depth)
            return {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'bids': orderbook['bids'][:depth],
                'asks': orderbook['asks'][:depth],
            }
        except Exception as e:
            logger.debug(f"Order book not available for {symbol}: {e}")
            return None
    
    def get_top_coins_by_volume(self, limit: int = 150) -> List[str]:
        """
        Get top N coins by 24h volume from futures market
        IMPORTANT: Returns clean symbols WITHOUT ":USDT" suffix
        """
        try:
            tickers = self.exchange.fetch_tickers()
            
            usdt_pairs = []
            for symbol, data in tickers.items():
                if '/USDT' in symbol:
                    volume = data.get('quoteVolume', 0)
                    if volume and volume > 0:
                        # Clean symbol: remove slash AND any :USDT suffix
                        # Binance futures unified symbols look like "BTC/USDT:USDT"
                        # We want just "BTCUSDT" for the database
                        clean_symbol = symbol.replace('/', '').split(':')[0]
                        usdt_pairs.append({
                            'symbol': clean_symbol,
                            'volume': volume
                        })
            
            usdt_pairs.sort(key=lambda x: x['volume'], reverse=True)
            top_symbols = [p['symbol'] for p in usdt_pairs[:limit]]
            
            if top_symbols:
                logger.info(f"✅ Retrieved top {len(top_symbols)} coins by volume")
                return top_symbols
            
            # Fallback if empty
            return ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']
            
        except Exception as e:
            logger.error(f"Failed to get top coins: {e}")
            return ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']