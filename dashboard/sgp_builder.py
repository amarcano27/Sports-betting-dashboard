"""
APEX ANALYTICS - SGP Builder
Same-Game Parlay construction with correlation detection and EV calculation.
"""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.model import (
    american_to_decimal, decimal_to_american, american_to_prob,
    quarter_kelly, devig, parlay_odds,
)
from dashboard.premium_styles import TOKENS
from dashboard.mobile_utils import inject_mobile_css

inject_mobile_css()

# ─────────────────────────────────────────────────────────────
# CORRELATION ENGINE
# ─────────────────────────────────────────────────────────────

# Correlation map: (leg_type_a, leg_type_b) → boost factor
# Positive = legs move together (boost EV), Negative = opposite (reduce EV)
CORRELATION_MAP = {
    # MLB
    ("ml_win",      "pitcher_ks"):    +0.25,  # team wins → starter pitches more
    ("ml_win",      "run_line_cover"):+0.55,  # winning → covers spread
    ("ml_win",      "first_5_win"):   +0.60,  # winning game → winning F5
    ("ml_win",      "over_total"):    +0.10,  # win correlates weakly with scoring
    ("ml_win",      "under_total"):   -0.10,  # inverse
    ("first_5_win", "pitcher_ks"):    +0.30,  # F5 win → starter dominant
    ("first_5_win", "run_line_cover"):+0.35,
    ("over_total",  "ml_win"):        +0.10,
    ("over_total",  "under_total"):   -1.00,  # impossible combo
    # NBA
    ("ml_win",      "spread_cover"):  +0.65,
    ("ml_win",      "player_pts_o"):  +0.15,  # team scoring → player scores
    ("player_pts_o","player_pts_o"):  +0.20,  # two scorers on same team
    ("player_pts_o","player_ast_o"):  +0.15,  # scoring and assists correlate
    # NHL
    ("ml_win",      "puck_line"):     +0.45,
    ("ml_win",      "goal_scorer"):   +0.25,
    ("over_total",  "goal_scorer"):   +0.20,  # high-scoring game → scorer props hit
}

LEG_TYPES = [
    "ML Win", "Spread/Puck Cover", "First 5 Win (MLB)", "Over Total",
    "Under Total", "Run Line Cover (MLB)", "Player PTS Over",
    "Player REB Over", "Player AST Over", "Player 3PM Over",
    "Pitcher K's Over", "Anytime Goal Scorer (NHL)",
]

TYPE_TO_KEY = {
    "ML Win":                    "ml_win",
    "Spread/Puck Cover":         "spread_cover",
    "First 5 Win (MLB)":         "first_5_win",
    "Over Total":                "over_total",
    "Under Total":               "under_total",
    "Run Line Cover (MLB)":      "run_line_cover",
    "Player PTS Over":           "player_pts_o",
    "Player REB Over":           "player_reb_o",
    "Player AST Over":           "player_ast_o",
    "Player 3PM Over":           "player_3pm_o",
    "Pitcher K's Over":          "pitcher_ks",
    "Anytime Goal Scorer (NHL)": "goal_scorer",
}


def get_correlation(type_a: str, type_b: str) -> float:
    ka = TYPE_TO_KEY.get(type_a, type_a.lower().replace(" ", "_"))
    kb = TYPE_TO_KEY.get(type_b, type_b.lower().replace(" ", "_"))
    return (CORRELATION_MAP.get((ka, kb)) or
            CORRELATION_MAP.get((kb, ka)) or 0.0)


def adjusted_joint_prob(legs: list[dict]) -> float:
    """
    Estimate true joint probability accounting for pairwise correlations.
    Uses additive correlation adjustment on log-odds.
    """
    if not legs:
        return 0.0
    # Start with independent joint prob
    joint = 1.0
    for leg in legs:
        joint *= leg["prob"]

    # Apply pairwise correlation adjustments
    n = len(legs)
    for i in range(n):
        for j in range(i + 1, n):
            corr = get_correlation(legs[i]["leg_type"], legs[j]["leg_type"])
            if corr != 0:
                # Adjustment: corr > 0 boosts joint prob, < 0 reduces
                joint *= (1.0 + corr * 0.3)  # dampened to avoid over-adjustment

    return min(0.95, max(0.005, joint))


def sgp_ev(combined_odds: int, joint_prob: float, stake: float) -> float:
    if combined_odds >= 0:
        payout = combined_odds / 100 * stake
    else:
        payout = 100 / abs(combined_odds) * stake
    return round(joint_prob * payout - (1 - joint_prob) * stake, 2)


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
st.title("🔗 SGP Builder")
st.caption("Same-Game Parlay · Correlation-adjusted EV · Works for MLB, NBA, NHL")

if "sgp_legs" not in st.session_state:
    st.session_state.sgp_legs = [
        {"desc": "White Sox ML Win",    "leg_type": "ML Win",            "odds": -120, "prob": 60.0},
        {"desc": "Martin O6.5 K's",     "leg_type": "Pitcher K's Over",  "odds":  115, "prob": 68.0},
        {"desc": "Sox/Twins Over 8.5",  "leg_type": "Over Total",        "odds": -108, "prob": 50.0},
    ]

# ── Leg editor ────────────────────────────────────────────────
st.markdown("#### Add Legs")
for i, leg in enumerate(st.session_state.sgp_legs):
    c1, c2, c3, c4, c5 = st.columns([4, 3, 2, 2, 1])
    leg["desc"]     = c1.text_input("Leg", value=leg["desc"], key=f"sd_{i}",
                                     label_visibility="collapsed", placeholder="Describe leg…")
    leg["leg_type"] = c2.selectbox("Type", LEG_TYPES,
                                    index=LEG_TYPES.index(leg["leg_type"]) if leg["leg_type"] in LEG_TYPES else 0,
                                    key=f"st_{i}", label_visibility="collapsed")
    leg["odds"]     = c3.number_input("Odds", -2000, 3000, int(leg["odds"]), 5,
                                       key=f"so_{i}", label_visibility="collapsed")
    leg["prob"]     = c4.number_input("True %", 1.0, 99.0, float(leg["prob"]), 1.0,
                                       key=f"sp_{i}", label_visibility="collapsed")
    if c5.button("✕", key=f"srm_{i}") and len(st.session_state.sgp_legs) > 1:
        st.session_state.sgp_legs.pop(i); st.rerun()

if st.button("➕ Add Leg"):
    st.session_state.sgp_legs.append(
        {"desc": "", "leg_type": "ML Win", "odds": -110, "prob": 55.0})
    st.rerun()

legs = st.session_state.sgp_legs
if len(legs) < 2:
    st.info("Add at least 2 legs to build an SGP.")
    st.stop()

stake = st.slider("Stake ($)", 5, 500, 25, 5, key="sgp_stake")

# ── Calculate ─────────────────────────────────────────────────
leg_dicts = [{"leg_type": l["leg_type"], "prob": l["prob"] / 100} for l in legs]
joint_prob_indep = 1.0
for l in leg_dicts:
    joint_prob_indep *= l["prob"]
joint_prob_adj = adjusted_joint_prob(leg_dicts)

odds_list = [int(l["odds"]) for l in legs]
dec_combined = 1.0
for o in odds_list:
    dec_combined *= american_to_decimal(o)
combined_american = decimal_to_american(dec_combined)
fair_combined_american = decimal_to_american(1.0 / joint_prob_adj)

book_payout_dec = dec_combined       # book offers this
true_ev = sgp_ev(combined_american, joint_prob_adj, stake)

# ── Display results ───────────────────────────────────────────
st.markdown("---")
m1, m2, m3, m4, m5 = st.columns(5)
pfx = "+" if combined_american > 0 else ""
fpfx = "+" if fair_combined_american > 0 else ""
ev_color = TOKENS["green"] if true_ev > 0 else TOKENS["red"]

m1.metric("SGP Odds",        f"{pfx}{combined_american}")
m2.metric("Fair Odds",       f"{fpfx}{fair_combined_american}")
m3.metric("Indep Win Prob",  f"{joint_prob_indep*100:.1f}%")
m4.metric("Corr-Adj Prob",   f"{joint_prob_adj*100:.1f}%")
m5.metric(f"EV / ${stake}",  f"${true_ev:+.2f}")

ev_label = "✅ Positive EV" if true_ev > 0 else "🚫 Negative EV — book edge too high"
st.markdown(f"""
<div style="background:{ev_color}15;border-left:4px solid {ev_color};
            padding:12px 16px;border-radius:6px;margin:12px 0">
  <span style="font-weight:800;color:{ev_color};font-size:14px">{ev_label}</span>
  <span style="color:{TOKENS['text_secondary']};font-size:13px;margin-left:12px">
    Payout if wins: ${(dec_combined-1)*stake:.0f}
    · Book implied: {american_to_prob(combined_american)*100:.1f}%
    · Our model: {joint_prob_adj*100:.1f}%
  </span>
</div>""", unsafe_allow_html=True)

# ── Per-leg breakdown + correlation warnings ──────────────────
st.markdown("#### Leg Breakdown + Correlations")
leg_rows = []
for l in legs:
    imp  = american_to_prob(int(l["odds"])) * 100
    edge = l["prob"] - imp
    leg_rows.append({
        "Leg":      l["desc"] or "(unnamed)",
        "Type":     l["leg_type"],
        "Odds":     f"+{int(l['odds'])}" if l["odds"] > 0 else str(int(l["odds"])),
        "True %":   f"{l['prob']:.0f}%",
        "Implied":  f"{imp:.0f}%",
        "Leg Edge": f"{edge:+.1f}%",
        "Status":   "✅" if edge >= 2 else "⚡" if edge >= 0 else "⚠️ drag",
    })
st.dataframe(pd.DataFrame(leg_rows), use_container_width=True, hide_index=True)

# Correlation matrix
n = len(legs)
if n >= 2:
    st.markdown("#### Correlation Matrix")
    matrix_rows = []
    for i, la in enumerate(legs):
        row = {"Leg": la["desc"][:25] or f"Leg {i+1}"}
        for j, lb in enumerate(legs):
            if i == j:
                row[lb["desc"][:15] or f"L{j+1}"] = "—"
            else:
                c = get_correlation(la["leg_type"], lb["leg_type"])
                if c > 0.3:
                    row[lb["desc"][:15] or f"L{j+1}"] = f"✅ +{c:.2f}"
                elif c < -0.3:
                    row[lb["desc"][:15] or f"L{j+1}"] = f"🚫 {c:.2f}"
                elif c != 0:
                    row[lb["desc"][:15] or f"L{j+1}"] = f"≈ {c:+.2f}"
                else:
                    row[lb["desc"][:15] or f"L{j+1}"] = "0"
        matrix_rows.append(row)
    st.dataframe(pd.DataFrame(matrix_rows), use_container_width=True, hide_index=True)

# Key correlations narrative
st.markdown("**📖 Key correlation insights for this SGP:**")
found_any = False
for i in range(n):
    for j in range(i + 1, n):
        c = get_correlation(legs[i]["leg_type"], legs[j]["leg_type"])
        if abs(c) >= 0.2:
            found_any = True
            la = legs[i]["desc"] or legs[i]["leg_type"]
            lb = legs[j]["desc"] or legs[j]["leg_type"]
            if c >= 0.5:
                st.success(f"**Strong positive correlation** ({c:+.2f}): *{la}* + *{lb}* — these move together. SGP EV boosted.")
            elif c >= 0.2:
                st.info(f"**Moderate correlation** ({c:+.2f}): *{la}* + *{lb}* — slight EV benefit.")
            elif c <= -0.5:
                st.error(f"**Negative correlation** ({c:+.2f}): *{la}* + *{lb}* — these legs work against each other. Avoid this combo.")
            elif c <= -0.2:
                st.warning(f"**Weak negative** ({c:+.2f}): *{la}* + *{lb}* — slight EV drag.")
if not found_any:
    st.caption("No significant correlations detected between these legs.")
