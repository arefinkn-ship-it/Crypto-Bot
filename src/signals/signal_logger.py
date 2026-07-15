# ============================================================
#  SIGNAL LOGGER - persists every scored signal to CSV
# ============================================================

import csv
from pathlib import Path
from datetime import datetime
from typing import Dict


class SignalLogger:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.fieldnames = [
            "logged_at", "candle_timestamp", "symbol", "direction",
            "score_boosted", "confidence", "confluence_count",
            "alignment_multiplier", "reason", "alerted",
        ]

    def _current_filepath(self) -> Path:
        today = datetime.now().strftime("%Y-%m-%d")
        return self.log_dir / f"signals_{today}.csv"

    def log(self, symbol: str, m5_data_timestamp, mt_signal: Dict, alerted: bool = False):
        filepath = self._current_filepath()
        file_exists = filepath.exists()

        row = {
            "logged_at": datetime.now().isoformat(timespec="seconds"),
            "candle_timestamp": m5_data_timestamp,
            "symbol": symbol,
            "direction": mt_signal.get("direction"),
            "score_boosted": mt_signal.get("score_boosted"),
            "confidence": mt_signal.get("confidence"),
            "confluence_count": mt_signal.get("confluence_count", ""),
            "alignment_multiplier": mt_signal.get("alignment_multiplier"),
            "reason": mt_signal.get("reason"),
            "alerted": alerted,
        }

        with open(filepath, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)