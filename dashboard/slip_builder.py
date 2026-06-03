"""
APEX ANALYTICS - Bet Slip
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
from utils.methodology import parlay_odds, american_to_decimal, parlay_ev, implied_probability

def init_state():
    if "current_slip" not in st.session_state:
        st.session_state.current_slip = {
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
    try:
        return supabase.table("user_slips").select("*").order("created_at", desc=True).limit(20).execute().data or []
    except:
        return []

init_state()
slip = st.session_state.current_slip

st.title("🎫 Bet Slip")
st.caption("Construct multi-leg slips and track EV.")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Current Slip")
    
    if not slip["legs"]:
        st.info("Slip is empty. Add legs below.")
        
    for i, leg in enumerate(slip["legs"]):
        st.markdown(f"**Leg {i+1}**")
        c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1])
        leg["play"]     = c1.text_input("Play", value=leg["play"], key=f"play_{i}", label_visibility="collapsed")
        leg["odds"]     = c2.number_input("Odds", value=leg["odds"], step=5, key=f"odds_{i}", label_visibility="collapsed")
        leg["real_pct"] = c3.number_input("True Win %", value=leg["real_pct"], step=1.0, key=f"pct_{i}", label_visibility="collapsed")
        leg["sport"]    = c4.selectbox("Sport", ["MLB","NBA","NHL","NFL","Esports"], index=["MLB","NBA","NHL","NFL","Esports"].index(leg["sport"]), key=f"spt_{i}", label_visibility="collapsed")
        if c5.button("✕", key=f"rm_{i}"):
            remove_leg(i)
            st.rerun()
            
    if st.button("➕ Add Leg", type="secondary"):
        add_leg()
        st.rerun()

with col2:
    st.subheader("Summary")
    if slip["legs"]:
        legs_odds = [l["odds"] for l in slip["legs"]]
        legs_with_probs = [(l["odds"], l["real_pct"]) for l in slip["legs"]]

        combined_american = parlay_odds(legs_odds)
        combined_dec = 1.0
        combined_prob = 1.0
        for l in slip["legs"]:
            combined_dec *= american_to_decimal(l["odds"])
            combined_prob *= l["real_pct"] / 100

        stake = st.number_input("Stake ($)", min_value=1, value=slip["stake"])
        slip["stake"] = stake
        profit = (combined_dec - 1) * stake
        ev = round(combined_prob * profit - (1 - combined_prob) * stake, 2)

        st.markdown(f"""
        <div class="apex-card" style="padding: 16px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <span style="color: #94A3B8;">Parlay Odds</span>
                <span style="font-family: 'JetBrains Mono', monospace; font-weight: 800; color: #F8FAFC;">{'+' if combined_american > 0 else ''}{combined_american}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <span style="color: #94A3B8;">True Win Prob</span>
                <span style="font-family: 'JetBrains Mono', monospace; font-weight: 800; color: #F8FAFC;">{combined_prob*100:.1f}%</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <span style="color: #94A3B8;">Payout</span>
                <span style="font-family: 'JetBrains Mono', monospace; font-weight: 800; color: #10B981;">${profit:.2f}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 16px; padding-top: 16px; border-top: 1px solid #1E293B;">
                <span style="color: #94A3B8; font-weight: 700;">Expected Value</span>
                <span style="font-family: 'JetBrains Mono', monospace; font-weight: 800; color: {'#10B981' if ev > 0 else '#EF4444'};">${ev:+.2f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        slip["notes"] = st.text_area("Notes", placeholder="Add rationale here...")
        
        if st.button("💾 Save Slip", type="primary", use_container_width=True):
            if save_slip():
                st.success("Slip saved!")
                st.session_state.current_slip = {"legs": [], "stake": 50, "notes": ""}
                st.rerun()

st.markdown("<hr style='border-color: #1E293B; margin: 32px 0;'>", unsafe_allow_html=True)

st.subheader("📜 Saved Slips")
saved = load_saved_slips()
if not saved:
    st.caption("No saved slips yet.")
else:
    for s in saved[:10]:
        try:
            legs_data = json.loads(s.get("legs", "[]")) if isinstance(s.get("legs"), str) else s.get("legs", [])
        except:
            legs_data = []
            
        num_legs = len(legs_data)
        total_odds = s.get("total_odds", 0)
        ev_score   = s.get("edge_pct", 0)
        created    = s.get("created_at", "")[:19].replace("T", " ")

        odds_str = f"+{int(total_odds)}" if total_odds and total_odds > 0 else f"{int(total_odds)}" if total_odds else "—"

        with st.expander(f"Slip · {num_legs} legs · {odds_str} · Edge {ev_score:+.1f}% · {created}"):
            if legs_data:
                df = pd.DataFrame(legs_data)
                st.dataframe(df, width="stretch", hide_index=True)
            notes = s.get("notes", "")
            if notes:
                st.caption(f"📝 {notes}")
