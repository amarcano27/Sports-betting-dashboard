"""
APEX ANALYTICS - Bet Tracker
Log every play you actually make. Track ROI, hit rate, P&L by sport/tier.
All data stored in Supabase `tracked_bets` table (auto-created on first use).
"""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
from datetime import datetime, date, timezone

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from dashboard.premium_styles import TOKENS
from dashboard.mobile_utils import inject_mobile_css

inject_mobile_css()

# ─────────────────────────────────────────────────────────────
# TABLE BOOTSTRAP
# ─────────────────────────────────────────────────────────────
def _ensure_table():
    """Try to read the table; if it fails with 'does not exist' show setup SQL."""
    try:
        supabase.table("tracked_bets").select("id").limit(1).execute()
        return True
    except Exception as e:
        if "does not exist" in str(e) or "PGRST" in str(e):
            return False
        return True   # other error, table might exist


TABLE_SQL = """
-- Run this in your Supabase SQL Editor to enable Bet Tracker
CREATE TABLE IF NOT EXISTS tracked_bets (
    id          uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    bet_date    date NOT NULL DEFAULT CURRENT_DATE,
    sport       text NOT NULL,
    matchup     text NOT NULL,
    play        text NOT NULL,
    odds        integer NOT NULL,
    stake       numeric(10,2) NOT NULL DEFAULT 25,
    result      text CHECK (result IN ('Win','Loss','Push','Pending')) DEFAULT 'Pending',
    profit      numeric(10,2) DEFAULT 0,
    edge_pct    numeric(6,2),
    rec_label   text,
    notes       text,
    created_at  timestamptz DEFAULT now()
);
"""

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def _calc_profit(odds: int, stake: float, result: str) -> float:
    if result == "Win":
        if odds >= 0: return round(odds / 100 * stake, 2)
        else:         return round(100 / abs(odds) * stake, 2)
    elif result == "Loss":   return round(-stake, 2)
    elif result == "Push":   return 0.0
    return 0.0

@st.cache_data(ttl=30)
def load_bets():
    try:
        return (supabase.table("tracked_bets")
                .select("*").order("bet_date", desc=True)
                .execute().data or [])
    except Exception:
        return []

def save_bet(row: dict):
    try:
        supabase.table("tracked_bets").insert([row]).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Could not save: {e}")
        return False

def update_result(bet_id: str, result: str, stake: float, odds: int):
    profit = _calc_profit(odds, stake, result)
    try:
        supabase.table("tracked_bets").update(
            {"result": result, "profit": profit}
        ).eq("id", bet_id).execute()
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Update failed: {e}")

# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
st.title("📒 Bet Tracker")
st.caption("Log your plays — track ROI, hit rate, P&L by sport and recommendation tier.")

table_ok = _ensure_table()
if not table_ok:
    st.error("**Bet Tracker needs one-time setup.** Paste this into your Supabase SQL Editor:")
    st.code(TABLE_SQL, language="sql")
    st.info("1. Go to supabase.com/dashboard → SQL Editor\n2. Paste the code above\n3. Click RUN\n4. Refresh this page")
    st.stop()

# ── Log a new bet ─────────────────────────────────────────────
with st.expander("➕ Log a New Bet", expanded=True):
    with st.form("new_bet_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        sport   = c1.selectbox("Sport", ["MLB","NBA","NHL","NFL","NCAAB","Other"])
        bet_dt  = c2.date_input("Date", value=date.today())
        matchup = st.text_input("Matchup", placeholder="e.g. Padres @ Phillies")
        play    = st.text_input("Play",    placeholder="e.g. Walker Buehler O6.5 Ks")

        c3, c4, c5, c6 = st.columns(4)
        odds        = c3.number_input("Odds", -2000, 2000, -110, 5)
        stake       = c4.number_input("Stake ($)", 1.0, 10000.0, 25.0, 5.0)
        edge_pct    = c5.number_input("Edge % (opt)", -50.0, 50.0, 0.0, 0.5)
        rec_label   = c6.selectbox("Label", ["","BEST VALUE","STRONG","PLAY","LEAN","SKIP","PARLAY ONLY"])
        notes       = st.text_area("Notes (optional)", height=60)

        if st.form_submit_button("Save Bet", use_container_width=True, type="primary"):
            if not matchup.strip() or not play.strip():
                st.warning("Fill in Matchup and Play before saving.")
            else:
                save_bet({
                    "bet_date":  str(bet_dt),
                    "sport":     sport,
                    "matchup":   matchup.strip(),
                    "play":      play.strip(),
                    "odds":      int(odds),
                    "stake":     float(stake),
                    "result":    "Pending",
                    "profit":    0.0,
                    "edge_pct":  float(edge_pct) if edge_pct else None,
                    "rec_label": rec_label or None,
                    "notes":     notes.strip() or None,
                })
                st.success("Bet logged!")

bets = load_bets()
if not bets:
    st.info("No bets tracked yet. Log your first play above.")
    st.stop()

# ── P&L summary strip ─────────────────────────────────────────
settled = [b for b in bets if b.get("result") in ("Win","Loss","Push")]
pending = [b for b in bets if b.get("result") == "Pending"]

total_stake  = sum(float(b.get("stake",0)) for b in settled)
total_profit = sum(float(b.get("profit",0)) for b in settled)
roi          = round(total_profit / total_stake * 100, 1) if total_stake else 0
wins         = sum(1 for b in settled if b.get("result")=="Win")
losses       = sum(1 for b in settled if b.get("result")=="Loss")
hit_rate     = round(wins / (wins+losses) * 100, 1) if (wins+losses) > 0 else 0

c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("Total Bets",    len(settled))
c2.metric("Win / Loss",    f"{wins}W – {losses}L")
c3.metric("Hit Rate",      f"{hit_rate}%")
c4.metric("P&L",           f"${total_profit:+.2f}")
c5.metric("ROI",           f"{roi:+.1f}%")

if pending:
    st.caption(f"**{len(pending)} pending** bet(s) not included in stats.")

st.markdown("---")

# ── Update pending results ────────────────────────────────────
if pending:
    st.subheader("⏳ Pending — Mark Results")
    for b in pending:
        odds_v = int(b.get("odds",0))
        ml_str = f"+{odds_v}" if odds_v > 0 else str(odds_v)
        stake_v = float(b.get("stake",0))
        pc1, pc2, pc3 = st.columns([4,2,2])
        pc1.markdown(f"**{b.get('play','')}** · {b.get('matchup','')} · {ml_str} · ${stake_v:.0f}")
        result_choice = pc2.selectbox("Result", ["Pending","Win","Loss","Push"],
                                       key=f"res_{b['id']}", label_visibility="collapsed")
        if pc3.button("Update", key=f"upd_{b['id']}"):
            if result_choice != "Pending":
                update_result(b["id"], result_choice, stake_v, odds_v)
                st.rerun()

st.markdown("---")

# ── Bet history table ─────────────────────────────────────────
st.subheader("📋 Full History")

sport_f = st.selectbox("Filter sport", ["All"] + sorted({b.get("sport","?") for b in bets}))
filtered = bets if sport_f == "All" else [b for b in bets if b.get("sport") == sport_f]

table_rows = []
for b in filtered:
    odds_v  = int(b.get("odds",0))
    result  = b.get("result","Pending")
    profit  = float(b.get("profit",0))
    p_str   = f"${profit:+.2f}" if result != "Pending" else "—"
    result_icon = {"Win":"✅","Loss":"❌","Push":"➖","Pending":"⏳"}.get(result,"?")
    table_rows.append({
        "Date":     b.get("bet_date",""),
        "Sport":    b.get("sport",""),
        "Play":     b.get("play",""),
        "Matchup":  b.get("matchup",""),
        "Odds":     f"+{odds_v}" if odds_v>0 else str(odds_v),
        "Stake":    f"${float(b.get('stake',0)):.0f}",
        "Result":   f"{result_icon} {result}",
        "P&L":      p_str,
        "Edge%":    f"{b['edge_pct']:+.1f}%" if b.get("edge_pct") else "—",
        "Label":    b.get("rec_label") or "—",
    })

if table_rows:
    df = pd.DataFrame(table_rows)
    st.dataframe(df, use_container_width=True, hide_index=True,
        column_config={
            "Date":    st.column_config.TextColumn(width=100),
            "Sport":   st.column_config.TextColumn(width=60),
            "Play":    st.column_config.TextColumn(width=200),
            "Matchup": st.column_config.TextColumn(width=180),
            "Odds":    st.column_config.TextColumn(width=70),
            "Stake":   st.column_config.TextColumn(width=65),
            "Result":  st.column_config.TextColumn(width=95),
            "P&L":     st.column_config.TextColumn(width=80),
            "Edge%":   st.column_config.TextColumn(width=70),
            "Label":   st.column_config.TextColumn(width=100),
        })

# ── Performance by sport ──────────────────────────────────────
if len(settled) >= 3:
    st.markdown("---")
    st.subheader("📊 Performance by Sport")
    by_sport = {}
    for b in settled:
        s = b.get("sport","?")
        if s not in by_sport:
            by_sport[s] = {"w":0,"l":0,"profit":0.0,"stake":0.0}
        if b.get("result")=="Win":   by_sport[s]["w"] += 1
        elif b.get("result")=="Loss":by_sport[s]["l"] += 1
        by_sport[s]["profit"] += float(b.get("profit",0))
        by_sport[s]["stake"]  += float(b.get("stake",0))

    sport_rows = []
    for sp, v in sorted(by_sport.items()):
        total = v["w"] + v["l"]
        hr    = round(v["w"]/total*100,1) if total else 0
        roi_s = round(v["profit"]/v["stake"]*100,1) if v["stake"] else 0
        sport_rows.append({
            "Sport": sp, "W": v["w"], "L": v["l"],
            "Hit %": f"{hr}%",
            "P&L":   f"${v['profit']:+.2f}",
            "ROI":   f"{roi_s:+.1f}%",
        })
    st.dataframe(pd.DataFrame(sport_rows), use_container_width=True, hide_index=True)
