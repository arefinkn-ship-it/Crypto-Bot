# ============================================================
#  ON-CHAIN CLIENT - CoinGecko API wrapper with better rate limiting
# ============================================================

import time
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from src.core.logger import logger
from src.core.config import config


class OnChainClient:
    """
    CoinGecko API client for on-chain data.
    Free tier: 50 requests/min, no API key required.
    """
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    # CoinGecko ID mapping for common symbols
    COIN_IDS = {
        'BTC': 'bitcoin',
        'ETH': 'ethereum',
        'SOL': 'solana',
        'BNB': 'binancecoin',
        'XRP': 'ripple',
        'ADA': 'cardano',
        'DOGE': 'dogecoin',
        'AVAX': 'avalanche-2',
        'LINK': 'chainlink',
        'MATIC': 'matic-network',
        'DOT': 'polkadot',
        'UNI': 'uniswap',
        'ATOM': 'cosmos',
        'LTC': 'litecoin',
        'BCH': 'bitcoin-cash',
        'NEAR': 'near',
        'APT': 'aptos',
        'ARB': 'arbitrum',
        'OP': 'optimism',
        'INJ': 'injective-protocol',
        'SUI': 'sui',
        'RENDER': 'render-token',
        'TAO': 'bittensor',
        'ONDO': 'ondo-finance',
        'PEPE': 'pepe',
        'WIF': 'dogwifcoin',
        'SHIB': 'shiba-inu',
    }
    
    def __init__(self):
        self.last_request_time = 0
        self.min_request_interval = 2.0  # 2 seconds between requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CryptoBot/1.0',
            'Accept': 'application/json',
        })
    
    def _rate_limit(self):
        """Enforce rate limiting for free tier."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def _get_coin_id(self, symbol: str) -> Optional[str]:
        """Convert symbol to CoinGecko ID."""
        clean_symbol = symbol.replace('USDT', '').replace('USDC', '').replace('BUSD', '')
        return self.COIN_IDS.get(clean_symbol.upper())
    
    def _make_request(self, endpoint: str, params: Dict = None, max_retries: int = 3) -> Optional[Dict]:
        """Make an API request with rate limiting and retries."""
        for attempt in range(max_retries):
            try:
                self._rate_limit()
                
                url = f"{self.BASE_URL}{endpoint}"
                response = self.session.get(url, params=params, timeout=30)
                
                if response.status_code == 429:
                    wait_time = (attempt + 1) * 5  # 5, 10, 15 seconds
                    logger.warning(f"Rate limited (429). Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    logger.debug(f"Request failed (attempt {attempt+1}): {e}")
                    time.sleep(1)
                else:
                    logger.error(f"OnChain API error: {e}")
                    return None
        
        return None
    
    def get_coin_market_data(self, symbol: str) -> Optional[Dict]:
        """Get market data for a coin."""
        coin_id = self._get_coin_id(symbol)
        if not coin_id:
            return None
        
        data = self._make_request(f"/coins/{coin_id}")
        if not data:
            return None
        
        market_data = data.get('market_data', {})
        
        return {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'price_usd': market_data.get('current_price', {}).get('usd'),
            'market_cap_usd': market_data.get('market_cap', {}).get('usd'),
            'volume_24h_usd': market_data.get('total_volume', {}).get('usd'),
            'circulating_supply': market_data.get('circulating_supply'),
            'total_supply': market_data.get('total_supply'),
            'ath_price': market_data.get('ath', {}).get('usd'),
            'atl_price': market_data.get('atl', {}).get('usd'),
        }
    
    def get_coin_ohlcv(self, symbol: str, vs_currency: str = 'usd', days: int = 30) -> Optional[List[Dict]]:
        """Get OHLCV data for a coin (daily)."""
        coin_id = self._get_coin_id(symbol)
        if not coin_id:
            return None
        
        data = self._make_request(
            f"/coins/{coin_id}/ohlc",
            params={'vs_currency': vs_currency, 'days': days}
        )
        
        if not data:
            return None
        
        result = []
        for candle in data:
            result.append({
                'timestamp': datetime.fromtimestamp(candle[0] / 1000),
                'open': candle[1],
                'high': candle[2],
                'low': candle[3],
                'close': candle[4],
            })
        
        return result