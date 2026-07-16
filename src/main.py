#!/usr/bin/env python3
# ============================================================
#  CRYPTO BOT V2 - MAIN ENTRY POINT
#  CHANGES FROM PREVIOUS VERSION:
#   - BTC H1 trend fetched once per scan cycle, used to gate
#     altcoin signals fighting the dominant BTC trend (live data
#     showed SELL signals at 10% win rate, clustering exactly at
#     BTC-led dips within a broader uptrend).
#   - Correlation dedup applied to strong_signals before alerting -
#     simultaneous correlated signals (one market move counted many
#     times) now collapse to the single highest-scored alert.
# ============================================================

import sys
import time
from pathlib import Path
from typing import Dict
from datetime import datetime, timedelta  # ADDED BACK

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.core.logger import logger
from src.core.config import config
from src.core.bot_config import (
    SCAN_INTERVAL_SECONDS, MIN_SIGNAL_SCORE, COIN_WHITELIST,
)
from src.core.database import init_database
from src.data.collector import DataCollector
from src.data.loader import DataLoader
from src.signals.signal_combiner import combine_signals, StrategyResult, compute_risk_levels
from src.signals.alert import AlertManager
from src.signals.multi_timeframe import get_multi_timeframe_signal
from src.signals.signal_logger import SignalLogger
from src.signals.trade_tracker import TradeTracker
from src.signals.btc_trend_filter import get_btc_trend, passes_btc_trend_gate
from src.signals.correlation_filter import dedupe_correlated_signals

from src.strategies.trend_following import trend_following
from src.strategies.breakout import breakout
from src.strategies.mean_reversion import mean_reversion
# from src.strategies.ma_crossover import ma_crossover   # on hold
# from src.strategies.smc import smc                     # on hold


def get_atr(data: pd.DataFrame) -> float:
    import ta
    try:
        return ta.volatility.average_true_range(
            data['high'], data['low'], data['close'], window=14
        ).iloc[-1]
    except Exception:
        return data['close'].iloc[-1] * 0.02


def evaluate_strategies(data: pd.DataFrame) -> Dict:
    results = [
        trend_following(data),
        breakout(data),
        mean_reversion(data),
    ]
    combined = combine_signals(results)
    combined['strategies'] = {
        r.name: {
            'score': max(r.buy_score_raw, r.sell_score_raw),
            'direction': (
                'BUY' if r.buy_score_raw > r.sell_score_raw
                else 'SELL' if r.sell_score_raw > r.buy_score_raw
                else 'NEUTRAL'
            ),
            'details': {
                'reasons': r.reasons_buy if r.buy_score_raw >= r.sell_score_raw else r.reasons_sell
            },
        }
        for r in results
    }
    return combined


def log_diagnostics(symbol: str, m5_signal: Dict, mt_signal: Dict, btc_block_reason: str = None):
    logger.debug(
        f"[diag] {symbol}: 5m_dir={m5_signal['direction']} "
        f"5m_score={m5_signal['total_score']} "
        f"confluence={m5_signal['confluence_count']} "
        f"mult={m5_signal['confluence_multiplier']} "
        f"per_strategy={m5_signal['per_strategy_scores']} "
        f"| mt_dir={mt_signal['direction']} "
        f"boosted={mt_signal['score_boosted']} "
        f"align_mult={mt_signal['alignment_multiplier']} "
        f"reason='{mt_signal['reason']}'"
        + (f" | btc_gate='{btc_block_reason}'" if btc_block_reason else "")
    )


def main():
    logger.info("🚀 Starting Crypto Bot V2")
    logger.info(f"📁 Project: {config.BASE_DIR}")

    try:
        init_database()
        logger.info("✅ Database ready")

        collector = DataCollector()
        loader = DataLoader()
        alerts = AlertManager()
        signal_logger = SignalLogger()
        tracker = TradeTracker()

        logger.info(f"📊 Config: SCAN_INTERVAL_SECONDS={SCAN_INTERVAL_SECONDS}s, "
                    f"MIN_SIGNAL_SCORE={MIN_SIGNAL_SCORE}")
        logger.info(f"📊 Coin universe: {len(COIN_WHITELIST)} whitelisted symbols")
        logger.info("📊 3 core strategies active: trend_following, breakout, mean_reversion")
        logger.info("📊 BTC trend gate + correlation dedup active")

        logger.info("✅ Bot initialized successfully!")
        logger.info("📊 Ready to scan for signals...")

        scan_count = 0
        while True:
            scan_count += 1
            logger.info(f"🔄 Starting scan cycle #{scan_count}")

            try:
                coins = COIN_WHITELIST
                logger.info(f"📈 Scanning {len(coins)} coins")

                collector.collect_all(coins)

                # Fetch BTC's H1 trend ONCE per cycle - reused as the
                # gate for every altcoin below, not recomputed per symbol.
                btc_trend = get_btc_trend(loader)
                logger.info(f"📊 BTC H1 trend: {btc_trend.get('direction')} "
                            f"(strength={btc_trend.get('strength', 0)})")

                strong_signals = []
                all_scores = []

                for symbol in coins:
                    try:
                        timeframes = loader.load_multi_timeframe_data(symbol)
                        if not all(k in timeframes for k in ['h1', 'm15', 'm5']):
                            continue

                        h1_data = timeframes['h1']
                        m15_data = timeframes['m15']
                        m5_data = timeframes['m5']

                        m5_signal = evaluate_strategies(m5_data)
                        mt_signal = get_multi_timeframe_signal(
                            h1_data=h1_data, m15_data=m15_data,
                            m5_data=m5_data, m5_signals=m5_signal,
                        )

                        # BTC trend gate - blocks alts fighting BTC's own trend
                        btc_block_reason = None
                        if mt_signal['direction'] != 'NEUTRAL':
                            btc_block_reason = passes_btc_trend_gate(
                                symbol, mt_signal['direction'], btc_trend
                            )
                            if btc_block_reason:
                                mt_signal['score_boosted'] = 0
                                mt_signal['direction'] = 'NEUTRAL'
                                mt_signal['reason'] = btc_block_reason

                        log_diagnostics(symbol, m5_signal, mt_signal, btc_block_reason)
                        all_scores.append({
                            'symbol': symbol,
                            'score_boosted': mt_signal['score_boosted'],
                            'direction': mt_signal['direction'],
                        })

                        clears_threshold = (
                            mt_signal['direction'] != 'NEUTRAL' and
                            mt_signal['score_boosted'] >= MIN_SIGNAL_SCORE
                        )

                        signal_logger.log(
                            symbol=symbol,
                            m5_data_timestamp=m5_data['timestamp'].iloc[-1],
                            mt_signal=mt_signal,
                            alerted=clears_threshold,
                        )

                        if clears_threshold:
                            latest_price = m5_data['close'].iloc[-1]
                            atr_value = get_atr(m15_data)
                            risk = compute_risk_levels(
                                entry_price=latest_price, atr_value=atr_value,
                                direction=mt_signal['direction'],
                            )
                            strong_signals.append({
                                'symbol': symbol,
                                'signal': mt_signal['direction'],
                                'confidence': mt_signal['confidence'],
                                'score': mt_signal['score_boosted'],
                                'reason': mt_signal['reason'],
                                'h1_trend': mt_signal['h1_trend'],
                                'm15_trend': mt_signal['m15_trend'],
                                'timestamp': m5_data['timestamp'].iloc[-1],
                                'latest_price': latest_price,
                                'stop_loss': risk['stop_loss'],
                                'take_profit': risk['take_profit'],
                                'risk_reward': risk['risk_reward_ratio'],
                                'strategies': m5_signal.get('strategies', {}),
                            })

                    except Exception as e:
                        logger.error(f"Error evaluating {symbol}: {e}")

                if all_scores:
                    top5 = sorted(all_scores, key=lambda x: x['score_boosted'], reverse=True)[:5]
                    logger.info("📊 Top 5 scores this scan (regardless of alert threshold):")
                    for s in top5:
                        logger.info(f"   {s['symbol']}: {s['direction']} {s['score_boosted']}/10")

                # ---- Correlation dedup: collapse simultaneous correlated
                # signals down to the single highest-scored one per cluster ----
                if strong_signals:
                    strong_signals.sort(key=lambda x: x['score'], reverse=True)

                    price_data = {}
                    for s in strong_signals:
                        try:
                            price_data[s['symbol']] = loader.load_ohlcv(
                                s['symbol'], '5m', limit=50
                            )['close']
                        except Exception:
                            pass

                    before_count = len(strong_signals)
                    strong_signals = dedupe_correlated_signals(strong_signals, price_data)
                    deduped_count = before_count - len(strong_signals)
                    if deduped_count > 0:
                        logger.info(f"📊 Correlation dedup: dropped {deduped_count} "
                                    f"correlated duplicate signal(s)")

                if strong_signals:
                    logger.info(f"📊 Found {len(strong_signals)} signals clearing threshold "
                                f"({MIN_SIGNAL_SCORE}) after dedup")
                    for signal in strong_signals[:5]:
                        logger.info(f"   {signal['symbol']}: {signal['signal']} "
                                    f"({signal['score']:.1f}/10) - {signal['confidence']}")
                        logger.info(f"      Reason: {signal['reason']}")
                        sent = alerts.send_alert(signal)
                        if sent:
                            tracker.open_trade(
                                symbol=signal['symbol'], direction=signal['signal'],
                                confidence=signal['confidence'], score=signal['score'],
                                entry_price=signal['latest_price'],
                                stop_loss=signal['stop_loss'],
                                take_profit=signal['take_profit'],
                                entry_time=signal['timestamp'],
                            )
                else:
                    logger.info(f"🔍 No signals cleared threshold ({MIN_SIGNAL_SCORE}) this scan")

                closed_count = tracker.check_and_update(loader)
                if closed_count > 0:
                    logger.info(f"📉 {closed_count} trade(s) closed this cycle")

                logger.info("✅ Scan complete")

            except Exception as e:
                logger.error(f"❌ Scan error: {e}")
                import traceback
                traceback.print_exc()

            # Calculate and display next scan time (ADDED BACK)
            next_scan_time = datetime.now() + timedelta(seconds=SCAN_INTERVAL_SECONDS)
            next_scan_str = next_scan_time.strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"⏳ Waiting {SCAN_INTERVAL_SECONDS}s for next scan... (next scan at {next_scan_str})")
            time.sleep(SCAN_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        logger.info("👋 Shutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()