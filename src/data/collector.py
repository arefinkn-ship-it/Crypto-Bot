# ============================================================
#  DATA COLLECTOR - Fetch and store market data
# ============================================================

from typing import Dict, List, Optional
from src.core.logger import logger
from src.core.database import get_db
from src.core.bot_config import COLLECTOR_FETCH_LIMIT
from src.models import PriceData, MarketData
from src.data.binance_client import BinanceClient


class DataCollector:
    def __init__(self):
        self.client = BinanceClient()

    def _clean_symbol(self, symbol: str) -> str:
        cleaned = symbol.replace(':USDT', '')
        cleaned = cleaned.replace('/USDT', 'USDT')
        if not cleaned.endswith('USDT'):
            cleaned = cleaned + 'USDT'
        return cleaned

    def collect_ohlcv(self, symbol: str, timeframe: str = '1h') -> int:
        try:
            clean_symbol = self._clean_symbol(symbol)
            data = self.client.fetch_ohlcv(clean_symbol, timeframe, limit=COLLECTOR_FETCH_LIMIT)

            if not data:
                return 0

            stored = 0
            with get_db() as db:
                for candle in data:
                    existing = db.query(PriceData).filter(
                        PriceData.symbol == clean_symbol,
                        PriceData.timestamp == candle['timestamp'],
                        PriceData.timeframe == timeframe
                    ).first()

                    if existing:
                        continue

                    price_data = PriceData(
                        symbol=clean_symbol,
                        timestamp=candle['timestamp'],
                        timeframe=timeframe,
                        open=candle['open'],
                        high=candle['high'],
                        low=candle['low'],
                        close=candle['close'],
                        volume=candle['volume'],
                    )
                    db.add(price_data)
                    stored += 1

                db.commit()

            if stored > 0:
                logger.debug(f"📊 Stored {stored} candles for {clean_symbol} ({timeframe})")

            return stored

        except Exception as e:
            logger.error(f"Failed to collect OHLCV for {symbol}: {e}")
            return 0

    def collect_market_data(self, symbol: str) -> bool:
        try:
            clean_symbol = self._clean_symbol(symbol)

            with get_db() as db:
                funding = self.client.fetch_funding_rate(clean_symbol)
                if funding:
                    market_data = MarketData(
                        symbol=clean_symbol,
                        timestamp=funding['timestamp'],
                        funding_rate=funding.get('funding_rate'),
                    )
                    db.add(market_data)

                oi = self.client.fetch_open_interest(clean_symbol)
                if oi:
                    market_data = MarketData(
                        symbol=clean_symbol,
                        timestamp=oi['timestamp'],
                        open_interest=oi.get('open_interest'),
                        open_interest_value=oi.get('open_interest_value'),
                    )
                    db.add(market_data)

                db.commit()
                return True

        except Exception as e:
            logger.debug(f"Market data not available for {symbol}: {e}")
            return False

    def collect_all(self, symbols: List[str]) -> Dict[str, int]:
        results = {'ohlcv': 0, 'market': 0, 'errors': 0}

        for symbol in symbols:
            try:
                if not symbol.endswith('USDT'):
                    logger.debug(f"Skipping non-USDT symbol: {symbol}")
                    continue

                for tf in ['5m', '15m', '1h']:
                    results['ohlcv'] += self.collect_ohlcv(symbol, tf)

                if self.collect_market_data(symbol):
                    results['market'] += 1

            except Exception as e:
                logger.error(f"Error collecting data for {symbol}: {e}")
                results['errors'] += 1

        logger.info(f"📊 Collection complete: {results['ohlcv']} candles, {results['market']} market updates")
        return results