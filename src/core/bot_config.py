# ============================================================
#  BOT CONFIG - single source of truth for every tunable value
#  in the signal pipeline. Secrets/credentials stay in
#  src/core/config.py (.env-backed); this file is for numbers
#  you adjust while calibrating strategy behavior.
# ============================================================

# ------------------------------------------------------------
#  SCAN & ALERTING
# ------------------------------------------------------------
SCAN_INTERVAL_SECONDS = 900          # 15 min between scans
MIN_SIGNAL_SCORE = 6.0               # final boosted score required to alert
ALERT_COOLDOWN_SECONDS = 1800        # 30 min before re-alerting same symbol
MAX_SIGNALS_PER_DAY = 20

# ------------------------------------------------------------
#  COIN UNIVERSE
# ------------------------------------------------------------
TIER_1_MAJORS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
]

TIER_2_LARGE_CAP = [
    "XRPUSDT",
    "ADAUSDT",
    "AVAXUSDT",
    "DOGEUSDT",
    "DOTUSDT",
    "LINKUSDT",
    "LTCUSDT",
    "BCHUSDT",
    "ATOMUSDT",
    "UNIUSDT",
    "ETCUSDT",
    "XLMUSDT",
    "NEARUSDT",
    "APTUSDT",
    "ARBUSDT",
    "OPUSDT",
    "INJUSDT",
    "SUIUSDT",
    "TAOUSDT",
    "SEIUSDT",
    "TIAUSDT",
    "PYTHUSDT",
    "HBARUSDT",
    "ICPUSDT",
    "QNTUSDT",
    "RUNEUSDT",
    "LDOUSDT",
    "PENDLEUSDT",
    "TRXUSDT",
    "RENDERUSDT",
    "WLDUSDT",
    "GRAMUSDT",
    "KASUSDT",
]

TIER_3_MID_CAP = [
    "AAVEUSDT",
    "ALGOUSDT",
    "ANKRUSDT",
    "APEUSDT",
    "AXSUSDT",
    "CAKEUSDT",
    "COMPUSDT",
    "CRVUSDT",
    "DASHUSDT",
    "EGLDUSDT",
    "ENAUSDT",
    "ENJUSDT",
    "FETUSDT",
    "FILUSDT",
    "GRTUSDT",
    "IOTAUSDT",
    "KAVAUSDT",
    "MANAUSDT",
    "FETUSDT",
    "POLUSDT",
    "RLCUSDT",
    "SANDUSDT",
    "SNXUSDT",
    "STORJUSDT",
    "SUSHIUSDT",
    "THETAUSDT",
    "VETUSDT",
    "XMRUSDT",
    "XTZUSDT",
    "YFIUSDT",
    "ZECUSDT",
    "ZRXUSDT",
    "STRKUSDT",
    "JUPUSDT",
    "ONDOUSDT",
    "ETHFIUSDT",
    "EIGENUSDT",
]

# Active universe (Tier 1 + 2 + 3)
COIN_WHITELIST = TIER_1_MAJORS + TIER_2_LARGE_CAP + TIER_3_MID_CAP

# ------------------------------------------------------------
#  COIN TIER MAPPING (for Telegram alerts)
# ------------------------------------------------------------
COIN_TIERS = {}

# Add Tier 1 coins
for coin in TIER_1_MAJORS:
    COIN_TIERS[coin] = "⭐ MAJOR"

# Add Tier 2 coins
for coin in TIER_2_LARGE_CAP:
    COIN_TIERS[coin] = "🔷 TIER 1"

# Add Tier 3 coins
for coin in TIER_3_MID_CAP:
    COIN_TIERS[coin] = "🔶 TIER 2"

def get_coin_tier(symbol: str) -> str:
    """Return the tier label for a given symbol."""
    return COIN_TIERS.get(symbol, "⚪ UNKNOWN")

# ------------------------------------------------------------
#  STRATEGY WEIGHTS (3 core strategies - ma_crossover/smc on hold)
# ------------------------------------------------------------
STRATEGY_WEIGHTS = {
    "trend_following": 0.40,
    "breakout": 0.35,
    "mean_reversion": 0.25,
    "ma_crossover": 0.0,   # on hold
    "smc": 0.0,            # on hold
}

# ------------------------------------------------------------
#  SIGNAL COMBINER THRESHOLDS
# ------------------------------------------------------------
VOTE_EDGE = 1.5               # internal buy/sell gap needed for a strategy to "vote"
MIN_SCORE_EDGE = 1.0          # weighted buy/sell gap needed to pick a direction
MIN_ABSOLUTE_SCORE = 3.5      # minimum weighted score to consider a direction at all

CONFLUENCE_MULTIPLIER = {
    0: 0.0,
    1: 0.60,
    2: 0.85,
    3: 1.00,
}

# Confidence label thresholds (descriptive only - MIN_SIGNAL_SCORE
# above is the only real gate)
CONFIDENCE_HIGH_MIN_SCORE = 7.0
CONFIDENCE_HIGH_MIN_CONFLUENCE = 3
CONFIDENCE_MEDIUM_MIN_SCORE = 5.0
CONFIDENCE_MEDIUM_MIN_CONFLUENCE = 2

# ------------------------------------------------------------
#  MULTI-TIMEFRAME ALIGNMENT
# ------------------------------------------------------------
COUNTER_TREND_PENALTY = 0.7
FULL_ALIGN_BONUS = 1.3
PARTIAL_ALIGN_BONUS = 1.15
NO_READ_BONUS = 1.0

# ------------------------------------------------------------
#  RISK MANAGEMENT (ATR-based SL/TP)
# ------------------------------------------------------------
ATR_TIMEFRAME_FOR_RISK = "m15"
STOP_ATR_MULT = 1.5
TP_ATR_MULT = 3.0

# ------------------------------------------------------------
#  CANDLE HISTORY REQUIREMENTS
# ------------------------------------------------------------
MIN_CANDLES_TREND_FOLLOWING = 200
MIN_CANDLES_BREAKOUT = 25
MIN_CANDLES_MEAN_REVERSION = 35
COLLECTOR_FETCH_LIMIT = 250