"""
Slip Builder — construct multi-leg slips with stake targets, correlation flags, EV tracking.
Saves slips to Supabase ai_suggestions table for persistence.
"""
import sys
import json
from pathlib import Path
import streamlit as st
import pandas as pd
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from utils.methodology import (
    parlay_odds, american_to_decimal, parlay_ev,
    implied_probability, SLIP_TYPES, check_ml_structural
)
from dashboard.premium_styles import color, status_badge


SLIP_PRESETS = {
    "🔵 Anchor":      {"stake": "$50–$75",  "target": "+300 to +500",  "color": "blue"},
    "🔴 Value Mix":   {"stake": "$30–$50",  "target": "+450 to +750",  "color": "green"},
    "🟡 Swing":       {"stake": "$15–$25",  "target": "+900 to +1400", "color": "amber"},
    "🟢 SGP":         {"stake": "$20–$40",  "target": "+400 to +700",  "color": "green"},
    "💎 Cross-Sport": {"stake": "$25–$35",  "target": "+600 to +900",  "color": "purple"},
}


def init_state():
    if "slips" not in st.session_state:
        st.session_state.slips = []
    if "current_slip" not in st.session_state:
        st.session_state.current_slip = {
            "name":  "🔵 Anchor",
            "legs":  [],
            "stake": 50,
            "notes": "",
        }


def add_leg():
    st.session_state.current_slip["legs"].append({
        "play":     "",
        "odds":     110,
        "real_pct": 55.0,
        "sport":    "MLB",
        "game":     "",
    })


def remove_leg(idx):
    st.session_state.current_slip["legs"].pop(idx)


def save_slip():
    slip = dict(st.session_state.current_slip)
    if not slip["legs"]:
        st.error("Add at least one leg before saving")
        return False

    legs_odds = [l["odds"] for l in slip["legs"]]
    legs_with_probs = [(l["odds"], l["real_pct"]) for l in slip["legs"]]

    total_odds = parlay_odds(legs_odds)
    total_ev   = parlay_ev(legs_with_probs)

    # Persist to user_slips DB
    payload = {
        "sport":      slip["legs"][0]["sport"] if slip["legs"] else "Mixed",
        "total_odds": total_odds,
        "edge_pct":   total_ev,
        "legs":       json.dumps(slip["legs"]),
        "notes":      slip.get("notes", ""),
        "status":     "pending"
    }
    try:
        supabase.table("user_slips").insert([payload]).execute()
        return True
    except Exception as e:
        st.error(f"Save failed: {e}")
        return False


@st.cache_data(ttl=60)
def load_saved_slips():
    rows = (
        supabase.table("user_slips")
        .select("*")
        .order("created_at", desc=True)
        .limit(20)
        .execute()
        .data or []
    )
    return rows


def detect_correlations(legs: list) -> list[str]:
    """Find correlated legs in the slip — same-game pairings."""
    warnings = []
    games = {}
    for l in legs:
        g = l.get("game", "").strip()
        if not g:
            continue
        if g in games:
            warnings.append(f"✅ Same-game correlation: **{games[g]['play']}** + **{l['play']}** ({g})")
        games[g] = l
    return warnings


# ── PAGE ──────────────────────────────────────────────────────
st.title("🧾 Slip Builder")
st.caption("Construct multi-leg slips. Auto-calculates parlay odds, EV, and correlation flags. Saves to history.")

init_state()
slip = st.session_state.current_slip

# ── Slip type selector ────────────────────────────────────────
c1, c2 = st.columns([2, 1])
slip["name"] = c1.selectbox("Slip Type", list(SLIP_PRESETS.keys()),
                             index=list(SLIP_PRESETS.keys()).index(slip["name"]) if slip["name"] in SLIP_PRESETS else 0)
preset = SLIP_PRESETS[slip["name"]]
c2.markdown(f"<div style='padding:8px;background:{color('bg_panel_2')};border-radius:6px;text-align:center'>"
            f"<div style='font-size:11px;color:{color('text_muted')}'>SUGGESTED</div>"
            f"<div style='font-weight:700;color:{color('text_primary')}'>Stake: {preset['stake']}</div>"
            f"<div style='font-size:12px;color:{color('text_muted')}'>Target: {preset['target']}</div>"
            f"</div>", unsafe_allow_html=True)

st.markdown("---")

# ── Legs ──────────────────────────────────────────────────────
st.subheader(f"Legs ({len(slip['legs'])})")

if not slip["legs"]:
    st.info("No legs yet. Click **➕ Add Leg** below.")

for i, leg in enumerate(slip["legs"]):
    with st.container():
        st.markdown(f"<div style='background:{color('bg_panel')};border-radius:8px;padding:14px;margin-bottom:10px;border:1px solid {color('border')}'>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:11px;color:{color('text_muted')};font-weight:600;margin-bottom:8px'>LEG {i+1}</div>", unsafe_allow_html=True)

        c1, c2, c3, c4, c5 = st.columns([4, 3, 2, 2, 1])
        leg["play"]     = c1.text_input("Play", value=leg["play"], key=f"sl_p_{i}", placeholder="e.g. Soroka O6.5 Ks")
        leg["game"]     = c2.text_input("Game", value=leg.get("game",""), key=f"sl_g_{i}", placeholder="e.g. LAD @ ARI")
        leg["odds"]     = c3.number_input("Odds",     value=leg["odds"],     key=f"sl_o_{i}", min_value=-2000, max_value=5000, step=5)
        leg["real_pct"] = c4.number_input("Real %",   value=leg["real_pct"], key=f"sl_r_{i}", min_value=1.0, max_value=99.0, step=1.0)
        if c5.button("✕", key=f"sl_rm_{i}"):
            remove_leg(i)
            st.rerun()

        # Per-leg breakdown
        imp = implied_probability(leg["odds"])
        edge = leg["real_pct"] - imp
        leg_payout = (american_to_decimal(leg["odds"]) - 1) * 100

        st.markdown(f"""
<div style='display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:8px;font-size:12px'>
  <div><span style='color:{color('text_muted')}'>Implied:</span> <span style='color:{color('text_primary')};font-weight:600'>{imp:.1f}%</span></div>
  <div><span style='color:{color('text_muted')}'>Edge:</span> <span style='color:{color('green') if edge>0 else color('red')};font-weight:600'>{'+' if edge>=0 else ''}{edge:.1f}%</span></div>
  <div><span style='color:{color('text_muted')}'>Payout per $100:</span> <span style='color:{color('text_primary')};font-weight:600'>${leg_payout:.0f}</span></div>
  <div><span style='color:{color('text_muted')}'>Decimal:</span> <span style='font-family:monospace;color:{color('text_primary')}'>{american_to_decimal(leg['odds']):.2f}</span></div>
</div>
""", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

bc1, bc2 = st.columns([1, 5])
if bc1.button("➕ Add Leg", width="stretch"):
    add_leg()
    st.rerun()

# ── Summary ───────────────────────────────────────────────────
if slip["legs"]:
    st.markdown("---")
    st.subheader("📊 Slip Summary")

    # Correlations
    warns = detect_correlations(slip["legs"])
    if warns:
        for w in warns:
            st.success(w)

    legs_odds = [l["odds"] for l in slip["legs"]]
    legs_with_probs = [(l["odds"], l["real_pct"]) for l in slip["legs"]]

    combined_american = parlay_odds(legs_odds)
    combined_dec = 1.0
    combined_prob = 1.0
    for l in slip["legs"]:
        combined_dec *= american_to_decimal(l["odds"])
        combined_prob *= l["real_pct"] / 100

    stake = st.slider("Stake ($)", 5, 200, slip["stake"], 5, key="slip_stake")
    slip["stake"] = stake
    profit = (combined_dec - 1) * stake
    ev = round(combined_prob * profit - (1 - combined_prob) * stake, 2)

    m1, m2, m3, m4 = st.columns(4)
    prefix = "+" if combined_american > 0 else ""
    m1.metric("Parlay Odds", f"{prefix}{combined_american}")
    m2.metric("Win Prob",    f"{combined_prob*100:.1f}%")
    m3.metric("Payout",      f"${profit:.0f}")
    m4.metric("EV",          f"${ev:+.2f}", delta="+EV" if ev>0 else "−EV")

    slip["notes"] = st.text_area("Notes (optional)", value=slip.get("notes", ""), height=80,
                                  placeholder="e.g. SGP correlation: Soroka K + ARI ML pay together")

    bc1, bc2, bc3 = st.columns([1, 1, 4])
    if bc1.button("💾 Save Slip", width="stretch", type="primary"):
        if save_slip():
            st.success("✅ Slip saved to history")
            st.cache_data.clear()
    if bc2.button("🗑️ Clear", width="stretch"):
        st.session_state.current_slip = {"name": "🔵 Anchor", "legs": [], "stake": 50, "notes": ""}
        st.rerun()

# ── Saved slips history ───────────────────────────────────────
st.markdown("---")
st.subheader("📜 Saved Slip History")

saved = load_saved_slips()
if not saved:
    st.caption("No saved slips yet.")
else:
    for s in saved[:10]:
        try:
            legs_data = json.loads(s.get("legs", "[]")) if isinstance(s.get("legs"), str) else s.get("legs", [])
        except Exception:
            legs_data = []
            
        num_legs = len(legs_data)
        total_odds = s.get("total_odds", 0)
        ev_score   = s.get("edge_pct", 0)
        created    = s.get("created_at", "")[:19].replace("T", " ")

        odds_str = f"+{int(total_odds)}" if total_odds and total_odds > 0 else f"{int(total_odds)}" if total_odds else "—"
        ev_color = color("green") if ev_score and ev_score > 0 else color("red")

        with st.expander(f"Slip · {num_legs} legs · {odds_str} · Edge {ev_score:+.1f}% · {created}"):
            if legs_data:
                df = pd.DataFrame(legs_data)
                st.dataframe(df, width="stretch", hide_index=True)
            notes = s.get("notes", "")
            if notes:
                st.caption(f"📝 {notes}")
