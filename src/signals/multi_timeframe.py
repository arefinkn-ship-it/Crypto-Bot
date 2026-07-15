# ============================================================
#  MULTI-TIMEFRAME ALIGNMENT
# ============================================================

import pandas as pd
import ta
from typing import Dict

from src.core.bot_config import (
    COUNTER_TREND_PENALTY, FULL_ALIGN_BONUS, PARTIAL_ALIGN_BONUS, NO_READ_BONUS,
)


def get_trend_direction(df: pd.DataFrame, lookback: int = 50) -> Dict:
    if len(df) < lookback:
        return {'direction': 'NEUTRAL', 'strength': 0}

    close = df['close']
    ema_50 = ta.trend.ema_indicator(close, window=50)
    ema_200 = ta.trend.ema_indicator(close, window=200)
    ema50_val = ema_50.iloc[-1]
    ema200_val = ema_200.iloc[-1]
    close_val = close.iloc[-1]

    adx = ta.trend.adx(df['high'], df['low'], close, window=14)
    adx_val = adx.iloc[-1] if len(adx) > 0 else 0

    if pd.isna(ema200_val):
        return {'direction': 'NEUTRAL', 'strength': 0, 'note': 'insufficient history for EMA200'}

    if close_val > ema50_val > ema200_val:
        direction = 'BULLISH'
        strength = min(adx_val / 25 * 10, 10)
    elif close_val < ema50_val < ema200_val:
        direction = 'BEARISH'
        strength = min(adx_val / 25 * 10, 10)
    else:
        direction = 'NEUTRAL'
        strength = 0

    return {
        'direction': direction,
        'strength': round(strength, 2),
        'ema50': round(ema50_val, 4),
        'ema200': round(ema200_val, 4),
        'price': round(close_val, 4),
    }


def alignment_score(h1_trend: Dict, m15_trend: Dict, m5_direction: str) -> Dict:
    h1_dir = h1_trend.get('direction', 'NEUTRAL')
    m15_dir = m15_trend.get('direction', 'NEUTRAL')

    if m5_direction == 'NEUTRAL':
        return {'multiplier': 0.0, 'reason': '5m signal itself is neutral - nothing to boost'}

    h1_conflicts = (h1_dir == 'BULLISH' and m5_direction == 'SELL') or \
                   (h1_dir == 'BEARISH' and m5_direction == 'BUY')

    if h1_conflicts:
        return {
            'multiplier': COUNTER_TREND_PENALTY,
            'reason': f'5m {m5_direction} against established H1 {h1_dir} trend - discounted, not deleted',
        }

    if h1_dir == 'NEUTRAL':
        return {
            'multiplier': NO_READ_BONUS,
            'reason': 'H1 trend unclear - 5m signal evaluated on its own, no boost/penalty',
        }

    if (h1_dir == 'BULLISH' and m15_dir == 'BULLISH') or (h1_dir == 'BEARISH' and m15_dir == 'BEARISH'):
        return {
            'multiplier': FULL_ALIGN_BONUS,
            'reason': f'H1 {h1_dir}, 15m {m15_dir}, 5m {m5_direction} - full alignment',
        }
    elif m15_dir == 'NEUTRAL':
        return {
            'multiplier': PARTIAL_ALIGN_BONUS,
            'reason': f'H1 {h1_dir}, 15m neutral, 5m {m5_direction} - partial alignment',
        }
    else:
        return {
            'multiplier': NO_READ_BONUS,
            'reason': f'H1 {h1_dir} agrees with 5m {m5_direction}, but 15m {m15_dir} conflicts - no boost',
        }


def get_multi_timeframe_signal(
    h1_data: pd.DataFrame,
    m15_data: pd.DataFrame,
    m5_data: pd.DataFrame,
    m5_signals: Dict,
) -> Dict:
    h1_trend = get_trend_direction(h1_data)
    m15_trend = get_trend_direction(m15_data)

    m5_direction = m5_signals.get('direction', 'NEUTRAL')
    m5_score = m5_signals.get('total_score', 0)

    align = alignment_score(h1_trend, m15_trend, m5_direction)
    multiplier = align['multiplier']

    score_boosted = round(min(m5_score * multiplier, 10), 2)
    final_direction = m5_direction if score_boosted > 0 else 'NEUTRAL'

    return {
        'direction': final_direction,
        'confidence': m5_signals.get('confidence', 'NONE'),
        'reason': align['reason'],
        'h1_trend': h1_trend,
        'm15_trend': m15_trend,
        'alignment_multiplier': multiplier,
        'signal_score': m5_score,
        'score_boosted': score_boosted,
    }