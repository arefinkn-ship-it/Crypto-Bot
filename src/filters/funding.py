# ============================================================
#  FUNDING RATE MODIFIER
#  Resolves: funding rate collected but never used to adjust
#  signal conviction.
# ============================================================

def funding_rate_modifier(funding_rate: float, direction: str) -> float:
    """
    Returns a score multiplier (0.7-1.0) based on how expensive it
    is to hold the proposed position. Positive funding = longs pay
    shorts (expensive to hold long); negative = shorts pay longs.
    """
    if funding_rate is None:
        return 1.0
    
    EXTREME_FUNDING = 0.0005  # ~0.05% per 8h is already elevated for majors

    if direction == "BUY" and funding_rate > EXTREME_FUNDING:
        return 0.8  # longing into expensive-to-hold funding - discount conviction
    if direction == "SELL" and funding_rate < -EXTREME_FUNDING:
        return 0.8  # shorting into expensive-to-hold funding
    return 1.0