# ============================================================
#  DATA LOADER
# ============================================================

import sqlite3
import pandas as pd
from typing import Dict, Optional
from src.core.logger import logger


class DataLoader:
    def __init__(self, db_path: str = 'crypto_bot.db'):
        self.db_path = db_path

    def load_ohlcv(self, symbol: str, timeframe: str = '5m', limit: int = 200) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT timestamp, open, high, low, close, volume
            FROM price_data
            WHERE symbol = ? AND timeframe = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """
        df = pd.read_sql(query, conn, params=(symbol, timeframe, limit))
        conn.close()
        return df.sort_values('timestamp').reset_index(drop=True)

    def load_multi_timeframe_data(self, symbol: str) -> Dict[str, pd.DataFrame]:
        result = {}

        h1 = self.load_ohlcv(symbol, '1h', limit=250)
        if len(h1) >= 50:
            result['h1'] = h1
        else:
            logger.debug(f"Not enough H1 data for {symbol}: {len(h1)} candles")

        m15 = self.load_ohlcv(symbol, '15m', limit=250)
        if len(m15) >= 50:
            result['m15'] = m15
        else:
            logger.debug(f"Not enough 15m data for {symbol}: {len(m15)} candles")

        m5 = self.load_ohlcv(symbol, '5m', limit=250)
        if len(m5) >= 50:
            result['m5'] = m5
        else:
            logger.debug(f"Not enough 5m data for {symbol}: {len(m5)} candles")

        return result

    def load_all_symbols(self, timeframe: str = '5m', limit: int = 200,
                          min_candles: int = 50) -> Dict[str, pd.DataFrame]:
        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT symbol, COUNT(*) as count
            FROM price_data
            WHERE timeframe = ?
            GROUP BY symbol
            HAVING COUNT(*) >= ?
        """
        symbols_df = pd.read_sql(query, conn, params=(timeframe, min_candles))
        symbols = symbols_df['symbol'].tolist()
        conn.close()

        if not symbols:
            logger.warning(f"No symbols found with {min_candles}+ candles")
            return {}

        logger.info(f"📊 Loading data for {len(symbols)} symbols ({timeframe})")

        result = {}
        for symbol in symbols:
            df = self.load_ohlcv(symbol, timeframe, limit)
            if len(df) >= min_candles:
                result[symbol] = df

        return result

    def get_latest_price(self, symbol: str) -> Optional[float]:
        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT close FROM price_data
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """
        df = pd.read_sql(query, conn, params=(symbol,))
        conn.close()
        if len(df) > 0:
            return df['close'].iloc[0]
        return None

    def get_latest_funding_rate(self, symbol: str) -> Optional[float]:
        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT funding_rate FROM market_data
            WHERE symbol = ? AND funding_rate IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT 1
        """
        df = pd.read_sql(query, conn, params=(symbol,))
        conn.close()
        if len(df) > 0:
            return df['funding_rate'].iloc[0]
        return None