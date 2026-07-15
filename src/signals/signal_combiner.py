# ============================================================
#  SIGNAL COMBINER
# ============================================================

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List

from src.core.bot_config import (
    STRATEGY_WEIGHTS, VOTE_EDGE, MIN_SCORE_EDGE, MIN_ABSOLUTE_SCORE,
    CONFLUENCE_MULTIPLIER, CONFIDENCE_HIGH_MIN_SCORE, CONFIDENCE_HIGH_MIN_CONFLUENCE,
    CONFIDENCE_MEDIUM_MIN_SCORE, CONFIDENCE_MEDIUM_MIN_CONFLUENCE,
)


class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


@dataclass
class StrategyResult:
    name: str
    buy_score_raw: float
    sell_score_raw: float
    max_possible: float
    reasons_buy: List[str] = field(default_factory=list)
    reasons_sell: List[str] = field(default_factory=list)

    def normalized(self) -> "StrategyResult":
        scale = 10.0 / self.max_possible if self.max_possible > 0 else 0
        return StrategyResult(
            name=self.name,
            buy_score_raw=min(self.buy_score_raw * scale, 10.0),
            sell_score_raw=min(self.sell_score_raw * scale, 10.0),
            max_possible=10.0,
            reasons_buy=self.reasons_buy,
            reasons_sell=self.reasons_sell,
        )


def _confluence_multiplier(count: int) -> float:
    return CONFLUENCE_MULTIPLIER.get(count, 1.0 if count >= 3 else 0.0)


def combine_signals(results: List[StrategyResult]) -> Dict:
    normalized = {r.name: r.normalized() for r in results}

    weighted_buy = 0.0
    weighted_sell = 0.0
    buy_votes: List[str] = []
    sell_votes: List[str] = []
    all_reasons_buy: List[str] = []
    all_reasons_sell: List[str] = []

    for name, r in normalized.items():
        w = STRATEGY_WEIGHTS.get(name, 0.0)
        weighted_buy += r.buy_score_raw * w
        weighted_sell += r.sell_score_raw * w

        if r.buy_score_raw - r.sell_score_raw >= VOTE_EDGE:
            buy_votes.append(name)
            all_reasons_buy.extend(f"[{name}] {x}" for x in r.reasons_buy)
        elif r.sell_score_raw - r.buy_score_raw >= VOTE_EDGE:
            sell_votes.append(name)
            all_reasons_sell.extend(f"[{name}] {x}" for x in r.reasons_sell)

    buy_confluence = len(buy_votes)
    sell_confluence = len(sell_votes)

    edge = weighted_buy - weighted_sell
    raw_direction = Direction.NEUTRAL
    confluence_count = 0

    if abs(edge) >= MIN_SCORE_EDGE:
        if edge > 0 and weighted_buy >= MIN_ABSOLUTE_SCORE:
            raw_direction = Direction.BUY
            confluence_count = buy_confluence
        elif edge < 0 and weighted_sell >= MIN_ABSOLUTE_SCORE:
            raw_direction = Direction.SELL
            confluence_count = sell_confluence

    multiplier = _confluence_multiplier(confluence_count)
    raw_score = max(weighted_buy, weighted_sell)
    final_score = round(raw_score * multiplier, 2)

    direction = raw_direction if multiplier > 0 else Direction.NEUTRAL

    if direction == Direction.NEUTRAL or final_score == 0:
        confidence = Confidence.NONE
    elif confluence_count >= CONFIDENCE_HIGH_MIN_CONFLUENCE and final_score >= CONFIDENCE_HIGH_MIN_SCORE:
        confidence = Confidence.HIGH
    elif confluence_count >= CONFIDENCE_MEDIUM_MIN_CONFLUENCE and final_score >= CONFIDENCE_MEDIUM_MIN_SCORE:
        confidence = Confidence.MEDIUM
    else:
        confidence = Confidence.LOW

    return {
        "direction": direction.value,
        "confidence": confidence.value,
        "total_score": final_score,
        "raw_score_before_confluence": round(raw_score, 2),
        "confluence_multiplier": multiplier,
        "weighted_buy": round(weighted_buy, 2),
        "weighted_sell": round(weighted_sell, 2),
        "confluence_count": confluence_count,
        "strategies_agreeing": buy_votes if direction == Direction.BUY else sell_votes,
        "reasons": all_reasons_buy if direction == Direction.BUY else all_reasons_sell,
        "per_strategy_scores": {
            name: {"buy": round(r.buy_score_raw, 2), "sell": round(r.sell_score_raw, 2)}
            for name, r in normalized.items()
        },
    }


def compute_risk_levels(
    entry_price: float,
    atr_value: float,
    direction: str,
) -> Dict[str, float]:
    from src.core.bot_config import STOP_ATR_MULT, TP_ATR_MULT

    if direction == Direction.BUY.value:
        stop_loss = entry_price - (atr_value * STOP_ATR_MULT)
        take_profit = entry_price + (atr_value * TP_ATR_MULT)
    elif direction == Direction.SELL.value:
        stop_loss = entry_price + (atr_value * STOP_ATR_MULT)
        take_profit = entry_price - (atr_value * TP_ATR_MULT)
    else:
        return {"stop_loss": None, "take_profit": None, "risk_reward_ratio": None}

    return {
        "stop_loss": round(stop_loss, 8),
        "take_profit": round(take_profit, 8),
        "risk_reward_ratio": round(TP_ATR_MULT / STOP_ATR_MULT, 2),
    }