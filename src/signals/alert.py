# ============================================================
#  ALERT MANAGER
# ============================================================

from typing import Dict
from datetime import datetime
from src.core.config import config
from src.core.bot_config import ALERT_COOLDOWN_SECONDS, MAX_SIGNALS_PER_DAY, get_coin_tier
from src.core.logger import logger
from src.utils.fibonacci_manager import FibonacciManager

try:
    import requests
except ImportError:
    requests = None


class AlertManager:
    def __init__(self):
        self.token = config.TELEGRAM_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.cooldown_seconds = ALERT_COOLDOWN_SECONDS
        self.last_alert_time = {}
        self.daily_count = 0
        self.last_reset_date = datetime.now().date()

        if not self.token or not self.chat_id:
            logger.warning("⚠️ Telegram credentials not set. Alerts disabled.")
        if requests is None:
            logger.warning("⚠️ requests library not installed. Alerts disabled.")

    def _reset_daily_count(self):
        today = datetime.now().date()
        if today != self.last_reset_date:
            self.daily_count = 0
            self.last_reset_date = today

    def _can_send_alert(self, symbol: str) -> bool:
        self._reset_daily_count()

        if self.daily_count >= MAX_SIGNALS_PER_DAY:
            logger.debug(f"Daily alert limit reached ({MAX_SIGNALS_PER_DAY})")
            return False

        last_time = self.last_alert_time.get(symbol)
        if last_time:
            elapsed = (datetime.now() - last_time).total_seconds()
            if elapsed < self.cooldown_seconds:
                logger.debug(f"Cooldown active for {symbol} ({elapsed:.0f}s remaining)")
                return False

        return True

    def _format_signal_message(self, signal: Dict) -> str:
        symbol = signal.get('symbol', 'UNKNOWN')
        signal_type = signal.get('signal', 'NEUTRAL')
        confidence = signal.get('confidence', 'LOW')
        score = signal.get('score', 0)
        price = signal.get('latest_price', 0)
        timestamp = signal.get('timestamp', datetime.now())

        if isinstance(timestamp, str):
            try:
                if 'T' in timestamp:
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                else:
                    timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            except Exception:
                timestamp = datetime.now()

        def fmt_price(p):
            if p is None:
                return "N/A"
            if p >= 1:
                return f"${p:.4f}"
            elif p >= 0.01:
                return f"${p:.6f}"
            else:
                return f"${p:.8f}"

        if signal_type == 'BUY':
            emoji, action = "🟢", "BUY"
        elif signal_type == 'SELL':
            emoji, action = "🔴", "SELL"
        else:
            emoji, action = "⚪", "NEUTRAL"

        if confidence == 'HIGH':
            confidence_emoji = "🔥"
        elif confidence == 'MEDIUM':
            confidence_emoji = "📊"
        else:
            confidence_emoji = "ℹ️"

        # Get coin tier
        tier_label = get_coin_tier(symbol)

        lines = [
            f"{emoji} {action} SIGNAL - {symbol}",
            f"🏷️ {tier_label}",
            "",
            f"Score: {score:.1f}/10",
            f"{confidence_emoji} Confidence: {confidence}",
            f"Price: {fmt_price(price)}",
            f"Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        h1_trend = signal.get('h1_trend')
        m15_trend = signal.get('m15_trend')
        alignment = signal.get('alignment')

        if h1_trend and m15_trend:
            lines.append("")
            lines.append("Multi-Timeframe Alignment:")
            lines.append(f"  H1: {h1_trend.get('direction', 'NEUTRAL')}")
            lines.append(f"  15m: {m15_trend.get('direction', 'NEUTRAL')}")
            lines.append(f"  5m: {signal_type}")
            if alignment == 'ALIGNED':
                lines.append("  ✅ FULL ALIGNMENT")
            else:
                lines.append("  ⚠️ PARTIAL ALIGNMENT")

        lines.append("")
        lines.append("Strategy Breakdown:")

        for name, result in signal.get('strategies', {}).items():
            strategy_score = result.get('score', 0)
            strategy_dir = result.get('direction', 'NEUTRAL')
            dir_emoji = "🟢" if strategy_dir == 'BUY' else "🔴" if strategy_dir == 'SELL' else "⚪"
            lines.append(f"  {dir_emoji} {name}: {strategy_score:.1f}/10 ({strategy_dir})")

        best_strategy = max(
            signal.get('strategies', {}).items(),
            key=lambda x: x[1].get('score', 0),
            default=(None, {})
        )
        if best_strategy[0]:
            reasons = best_strategy[1].get('details', {}).get('reasons', [])
            if reasons:
                lines.append("")
                lines.append(f"Key Reasons ({best_strategy[0]}):")
                for reason in reasons[:3]:
                    lines.append(f"  - {reason}")

        stop_loss = signal.get('stop_loss')
        take_profit = signal.get('take_profit')
        risk_reward = signal.get('risk_reward')

        if stop_loss and take_profit:
            lines.append("")
            lines.append("ATR-Based Risk Management:")
            lines.append(f"  Stop Loss: {fmt_price(stop_loss)}")
            lines.append(f"  Take Profit: {fmt_price(take_profit)}")
            if risk_reward:
                lines.append(f"  Risk:Reward: 1:{risk_reward:.1f}")

        fib_data = signal.get('fibonacci_levels')
        if fib_data:
            lines.append("")
            fib_manager = FibonacciManager()
            lines.append(fib_manager.format_for_alert(fib_data))

        lines.append("")
        lines.append("-" * 30)
        lines.append("Not financial advice. DYOR.")

        return "\n".join(lines)

    def send_alert(self, signal: Dict) -> bool:
        if not self.token or not self.chat_id:
            logger.debug("Telegram credentials missing")
            return False
        if requests is None:
            logger.error("requests library not installed - cannot send alert")
            return False

        symbol = signal.get('symbol', 'UNKNOWN')

        if not self._can_send_alert(symbol):
            return False

        message = self._format_signal_message(signal)
        if len(message) > 4000:
            message = message[:4000] + "\n\n... (truncated)"

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {'chat_id': self.chat_id, 'text': message}

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()

            self.last_alert_time[symbol] = datetime.now()
            self.daily_count += 1

            logger.info(f"✅ Alert sent for {symbol} ({signal.get('signal', 'NEUTRAL')})")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to send alert: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Telegram response: {e.response.text}")
            return False

    def send_test_message(self) -> bool:
        if not self.token or not self.chat_id:
            logger.warning("⚠️ Telegram credentials missing")
            return False
        if requests is None:
            logger.error("requests library not installed - cannot send test")
            return False

        test_message = (
            "🤖 Crypto Bot Test Message\n\n"
            "✅ Your bot is connected and ready!\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {'chat_id': self.chat_id, 'text': test_message}
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("✅ Test message sent to Telegram")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send test message: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Telegram response: {e.response.text}")
            return False