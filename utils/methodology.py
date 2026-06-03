"""
Core analysis logic from BETTING_METHODOLOGY.md
Pitcher tiers, edge calculations, structural play detection.
"""


# ── Edge / EV ─────────────────────────────────────────────────

def implied_probability(odds: int) -> float:
    """American odds → implied probability (0-100)."""
    if odds < 0:
        return abs(odds) / (abs(odds) + 100) * 100
    return 100 / (odds + 100) * 100


def calculate_edge(odds: int, real_prob_pct: float) -> float:
    """Edge = real_prob_pct − implied_prob. Positive = +EV."""
    return round(real_prob_pct - implied_probability(odds), 1)


def ev_dollar(odds: int, real_prob_pct: float, stake: float = 100) -> float:
    """Expected value in dollars for a given stake."""
    p = real_prob_pct / 100
    if odds >= 0:
        profit = odds / 100 * stake
    else:
        profit = 100 / abs(odds) * stake
    return round(p * profit - (1 - p) * stake, 2)


# ── Pitcher Tiers ─────────────────────────────────────────────

def classify_pitcher(era: float, xera: float | None = None) -> tuple[str, bool, str]:
    """
    Returns (tier_label, should_back_ml, description).

    Tier 1  — back ML at any reasonable price
    Tier 2  — back ML to -160
    Tier 3  — back ML to -130, watch regression
    Tier 4  — caution, xERA > ERA by 1.0+
    AVOID   — ERA or xERA > 5.00
    """
    if xera is not None and xera > 5.0:
        return "AVOID", False, f"xERA {xera:.2f} > 5.00 — regression incoming"
    if era > 5.0:
        return "AVOID", False, f"ERA {era:.2f} > 5.00 — liability"
    if era < 2.5 and (xera is None or xera < 3.0):
        return "TIER 1 — ELITE", True, "Back ML at any reasonable price"
    if era < 3.5 and (xera is None or xera < 3.75):
        return "TIER 2 — STRONG", True, "Back ML up to -160"
    if era < 4.5:
        if xera is not None and (xera - era) > 1.0:
            return "TIER 4 — REGRESSION RISK", True, f"xERA ({xera:.2f}) beats ERA ({era:.2f}) by {xera-era:.1f}+ — luck-driven ERA, decline ahead"
        return "TIER 3 — SOLID", True, "Back ML up to -130"
    return "TIER 4 — CAUTION", False, "ERA 4.5-5.0 — marginal starter"


TIER_COLORS = {
    "TIER 1 — ELITE":           "#1A6B3C",
    "TIER 2 — STRONG":          "#2E7D32",
    "TIER 3 — SOLID":           "#558B2F",
    "TIER 4 — REGRESSION RISK": "#E65100",
    "TIER 4 — CAUTION":         "#BF360C",
    "AVOID":                    "#8B1A1A",
}


# ── K Prop Analysis ───────────────────────────────────────────

def k_prop_ev_flag(k_per_9: float, prop_line: float, odds: int) -> dict:
    """
    Flag K prop as +EV if:
    - Line is AT or BELOW the pitcher's K/9 average per 9 innings
    - And/or odds are plus-money
    """
    k_per_27_outs = k_per_9  # same as per 9 innings
    # Estimate expected Ks over a 6-inning start
    expected_6ip = round(k_per_27_outs * 6 / 9, 1)

    edge_raw = expected_6ip - prop_line
    at_or_below_avg = prop_line <= expected_6ip
    plus_money = odds > 0

    if plus_money and at_or_below_avg:
        signal = "🔥 AUTO +EV — Plus-money at/below average"
        priority = "BEST VALUE"
    elif at_or_below_avg:
        signal = "✅ +EV — Line below K/9 average"
        priority = "STRONG"
    elif plus_money:
        signal = "⚡ VALUE — Plus-money regardless of line"
        priority = "VALUE"
    else:
        signal = "— Line above average, negative odds"
        priority = "SKIP"

    implied_pct = round(implied_probability(odds), 1)
    real_pct = round(min(max(40 + edge_raw * 8, 30), 95), 1)
    edge = calculate_edge(odds, real_pct)

    return {
        "k_per_9":       k_per_9,
        "expected_6ip":  expected_6ip,
        "prop_line":     prop_line,
        "odds":          odds,
        "signal":        signal,
        "priority":      priority,
        "implied_pct":   implied_pct,
        "real_pct":      real_pct,
        "edge":          edge,
    }


# ── Structural Play Detection ─────────────────────────────────

def check_ml_structural(odds: int, sport: str) -> dict | None:
    """
    Returns a warning dict if the ML violates methodology rules.
    Returns None if play is structurally sound.
    """
    rules = {
        "MLB": 200,
        "NHL": 200,
        "NBA": 225,
        "NFL": 300,
    }
    threshold = rules.get(sport.upper(), 200)
    if odds < 0 and abs(odds) >= threshold:
        return {
            "trap": True,
            "reason": f"Never lay {threshold}+ straight on {sport} ML — use as parlay/SGP leg only",
            "suggestion": "Convert to parlay leg or use alternate market (puck line, run line, spread)",
        }
    return None


# ── Parlay Odds Calculator ────────────────────────────────────

def american_to_decimal(odds: int) -> float:
    if odds >= 0:
        return 1 + odds / 100
    return 1 + 100 / abs(odds)


def decimal_to_american(dec: float) -> int:
    if dec >= 2.0:
        return round((dec - 1) * 100)
    return round(-100 / (dec - 1))


def parlay_odds(legs: list[int]) -> int:
    """Combine list of American odds into a parlay American odds value."""
    combined = 1.0
    for o in legs:
        combined *= american_to_decimal(o)
    return decimal_to_american(combined)


def parlay_ev(legs: list[tuple[int, float]]) -> float:
    """
    legs: list of (american_odds, real_prob_pct)
    Returns combined EV on $100 stake.
    """
    combined_prob = 1.0
    combined_dec = 1.0
    for odds, real_pct in legs:
        combined_prob *= real_pct / 100
        combined_dec *= american_to_decimal(odds)
    profit = (combined_dec - 1) * 100
    return round(combined_prob * profit - (1 - combined_prob) * 100, 2)


# ── Slip Type Classification ──────────────────────────────────

SLIP_TYPES = {
    "ANCHOR":      {"stake": "$50–$75",  "target": "+300 to +500"},
    "VALUE MIX":   {"stake": "$30–$50",  "target": "+450 to +750"},
    "SWING":       {"stake": "$15–$25",  "target": "+900 to +1400"},
    "SGP":         {"stake": "$20–$40",  "target": "+400 to +700"},
    "CROSS-SPORT": {"stake": "$25–$35",  "target": "+600 to +900"},
}
