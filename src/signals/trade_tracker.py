#!/usr/bin/env python3
# ============================================================
#  TRADE TRACKER - automatic outcome tracking for every alert
#  Records entry/SL/TP at alert time, then checks REAL subsequent
#  price data (already being collected anyway) to determine if
#  SL or TP was hit first - no manual screenshot comparison needed.
#  Persists to CSV so it survives restarts and can be reviewed
#  anytime independent of the bot running.
# ============================================================

import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd

from src.core.logger import logger


class TradeTracker:
    FIELDNAMES = [
        "trade_id", "symbol", "direction", "confidence", "score",
        "entry_price", "stop_loss", "take_profit", "entry_time",
        "status", "exit_price", "exit_time", "pct_return", "outcome",
    ]

    def __init__(self, filepath: str = "logs/trades.csv"):
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(exist_ok=True)
        if not self.filepath.exists():
            self._write_all([])
        logger.info(f"📊 TradeTracker initialized: {self.filepath}")

    # ---------------------------------------------------------
    #  Internal CSV helpers
    # ---------------------------------------------------------
    def _read_all(self) -> List[Dict]:
        if not self.filepath.exists():
            return []
        with open(self.filepath, "r", newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def _write_all(self, rows: List[Dict]):
        with open(self.filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

    # ---------------------------------------------------------
    #  Open a new trade when an alert fires
    # ---------------------------------------------------------
    def open_trade(self, symbol: str, direction: str, confidence: str, score: float,
                   entry_price: float, stop_loss: float, take_profit: float,
                   entry_time: Any) -> str:
        """
        Record a new trade when an alert fires
        
        Args:
            symbol: Trading pair symbol
            direction: 'BUY' or 'SELL'
            confidence: 'HIGH', 'MEDIUM', or 'LOW'
            score: Signal score (0-10)
            entry_price: Price at entry
            stop_loss: Stop loss level
            take_profit: Take profit level
            entry_time: Timestamp of entry
            
        Returns:
            trade_id: Unique trade identifier
        """
        rows = self._read_all()
        
        # Convert entry_time to string if it's a pandas Timestamp
        if isinstance(entry_time, pd.Timestamp):
            entry_time_str = entry_time.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(entry_time, datetime):
            entry_time_str = entry_time.strftime("%Y-%m-%d %H:%M:%S")
        else:
            entry_time_str = str(entry_time)
            
        trade_id = f"{symbol}_{entry_time_str}".replace(" ", "_").replace(":", "").replace("-", "")

        # avoid duplicate trades for the same symbol+entry_time (e.g. if
        # main.py retries or logs twice in edge cases)
        if any(r["trade_id"] == trade_id for r in rows):
            logger.debug(f"⚠️ Trade {trade_id} already exists, skipping")
            return trade_id

        rows.append({
            "trade_id": trade_id,
            "symbol": symbol,
            "direction": direction,
            "confidence": confidence,
            "score": str(round(score, 2)),
            "entry_price": str(round(entry_price, 8)),
            "stop_loss": str(round(stop_loss, 8)),
            "take_profit": str(round(take_profit, 8)),
            "entry_time": entry_time_str,
            "status": "OPEN",
            "exit_price": "",
            "exit_time": "",
            "pct_return": "",
            "outcome": "",
        })
        self._write_all(rows)
        logger.info(f"📊 Trade opened: {trade_id} ({symbol} {direction})")
        return trade_id

    # ---------------------------------------------------------
    #  Check all OPEN trades against real subsequent price data
    # ---------------------------------------------------------
    def check_and_update(self, loader, max_age_hours: int = 48) -> int:
        """
        Check all open trades against real price data
        
        Args:
            loader: Your DataLoader instance
            max_age_hours: Trades open longer than this are marked TIMEOUT
            
        Returns:
            Number of trades updated (closed) this call
        """
        rows = self._read_all()
        updated = 0

        for row in rows:
            if row["status"] != "OPEN":
                continue

            symbol = row["symbol"]
            direction = row["direction"]
            entry_price = float(row["entry_price"])
            stop_loss = float(row["stop_loss"])
            take_profit = float(row["take_profit"])
            entry_time = pd.to_datetime(row["entry_time"])

            # Load 5m data for this symbol
            df = loader.load_ohlcv(symbol, "5m", limit=500)
            if df.empty:
                logger.debug(f"⚠️ No data for {symbol}, skipping update")
                continue
            df["timestamp"] = pd.to_datetime(df["timestamp"])

            # Get candles after entry
            path = df[df["timestamp"] > entry_time]
            if path.empty:
                logger.debug(f"⚠️ No candles after entry for {symbol}, skipping")
                continue

            age_hours = (datetime.now() - entry_time).total_seconds() / 3600

            outcome = None
            exit_price = None
            exit_time = None

            # Check each candle for SL or TP hit
            for _, candle in path.iterrows():
                if direction == "BUY":
                    if candle["low"] <= stop_loss:
                        outcome, exit_price = "SL_HIT", stop_loss
                    elif candle["high"] >= take_profit:
                        outcome, exit_price = "TP_HIT", take_profit
                else:  # SELL
                    if candle["high"] >= stop_loss:
                        outcome, exit_price = "SL_HIT", stop_loss
                    elif candle["low"] <= take_profit:
                        outcome, exit_price = "TP_HIT", take_profit

                if outcome:
                    exit_time = candle["timestamp"]
                    break

            # Timeout if trade is too old
            if outcome is None and age_hours >= max_age_hours:
                outcome = "TIMEOUT"
                exit_price = path["close"].iloc[-1]
                exit_time = path["timestamp"].iloc[-1]

            # Update trade if we have an outcome
            if outcome:
                pct_return = (
                    (exit_price - entry_price) / entry_price * 100
                    if direction == "BUY"
                    else (entry_price - exit_price) / entry_price * 100
                )
                row["status"] = "CLOSED"
                row["exit_price"] = str(round(exit_price, 8))
                row["exit_time"] = exit_time.strftime("%Y-%m-%d %H:%M:%S")
                row["pct_return"] = str(round(pct_return, 3))
                row["outcome"] = outcome
                updated += 1
                logger.info(f"📊 Trade closed: {row['trade_id']} - {outcome} ({pct_return:.2f}%)")

        if updated > 0:
            self._write_all(rows)
            
        return updated

    # ---------------------------------------------------------
    #  Performance summary - call anytime, independent of main.py
    # ---------------------------------------------------------
    def summary(self) -> Dict:
        """Get performance summary of all tracked trades"""
        rows = self._read_all()
        closed = [r for r in rows if r["status"] == "CLOSED"]
        open_trades = [r for r in rows if r["status"] == "OPEN"]

        if not closed:
            return {
                "total_closed": 0, 
                "open": len(open_trades), 
                "message": "No closed trades yet"
            }

        returns = [float(r["pct_return"]) for r in closed if r["pct_return"]]
        wins = [r for r in returns if r > 0]

        result = {
            "total_closed": len(closed),
            "open": len(open_trades),
            "win_rate_pct": round(len(wins) / len(returns) * 100, 1) if returns else 0,
            "avg_return_pct": round(sum(returns) / len(returns), 3) if returns else 0,
            "tp_hit_count": sum(1 for r in closed if r["outcome"] == "TP_HIT"),
            "sl_hit_count": sum(1 for r in closed if r["outcome"] == "SL_HIT"),
            "timeout_count": sum(1 for r in closed if r["outcome"] == "TIMEOUT"),
        }

        # breakdown by confidence tier
        by_confidence = {}
        for conf in ["HIGH", "MEDIUM", "LOW"]:
            tier_rows = [r for r in closed if r["confidence"] == conf]
            if tier_rows:
                tier_returns = [float(r["pct_return"]) for r in tier_rows if r["pct_return"]]
                if tier_returns:
                    tier_wins = sum(1 for r in tier_returns if r > 0)
                    by_confidence[conf] = {
                        "n": len(tier_rows),
                        "win_rate_pct": round(tier_wins / len(tier_rows) * 100, 1),
                        "avg_return_pct": round(sum(tier_returns) / len(tier_returns), 3),
                    }
        result["by_confidence"] = by_confidence

        return result