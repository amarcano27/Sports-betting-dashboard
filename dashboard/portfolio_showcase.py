"""
APEX ANALYTICS - Command Center
The ultimate high-level overview of the betting slate.
"""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
from datetime import datetime
from collections import Counter

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase, DB_MODE
from utils.model import devig, american_to_prob
from dashboard.mlb_page import find_pitcher, build_game_model
from dashboard.ui_components import render_metric_card, render_game_card

@st.cache_data(ttl=60)
def load_all_games():
    return supabase.table("games").select("*").order("start_time").execute().data or []

@st.cache_data(ttl=60)
def load_odds_for_game(game_id: str):
    return supabase.table("odds_snapshots").select("*").eq("game_id", game_id).execute().data or []

def fmt_time(iso_str: str) -> str:
    try:
        t = datetime.fromisoformat(iso_str.replace("Z","+00:00"))
        return t.strftime("%I:%M %p")
    except:
        return "TBD"

def best_ml(odds_rows, team):
    m = [r for r in odds_rows if r.get("market_type")=="h2h" and r.get("market_label")==team]
    if not m: return None
    return int(max(m, key=lambda r: r.get("price") or -9999).get("price", 0))

# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
st.title("⚡ Command Center")
st.caption(f"Live · {DB_MODE.upper()} Engine · {datetime.now().strftime('%b %d %Y %I:%M %p')}")

games = load_all_games()
counts = Counter(g["sport"] for g in games)

# ── Metrics strip ─────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
with m1: render_metric_card("Total Games", str(len(games)), color_type="info")
with m2: render_metric_card("MLB Slate", str(counts.get("MLB", 0)), color_type="neutral")
with m3: render_metric_card("NBA Slate", str(counts.get("NBA", 0)), color_type="neutral")
with m4: render_metric_card("NHL Slate", str(counts.get("NHL", 0)), color_type="neutral")

st.markdown("<br>", unsafe_allow_html=True)

# ── Top edge plays across all sports ─────────────────────────
st.subheader("🎯 Top Edges")

top_plays = []
for g in games:
    sport = g.get("sport", "?")
    rows  = load_odds_for_game(g["id"])
    away, home = g["away_team"], g["home_team"]
    a_ml = best_ml(rows, away)
    h_ml = best_ml(rows, home)
    if not a_ml or not h_ml:
        continue

    dv_a, dv_h = devig(a_ml, h_ml)

    if sport == "MLB":
        apn, apd = find_pitcher(away)
        hpn, hpd = find_pitcher(home)
        if apd and hpd:
            gm = build_game_model(away, home, apd["fip"], hpd["fip"], a_ml, h_ml)
            best_e = max(gm.away_edge, gm.home_edge)
            best_t = away if gm.away_edge >= gm.home_edge else home
            best_m = a_ml if gm.away_edge >= gm.home_edge else h_ml
            best_l = gm.away_rec if gm.away_edge >= gm.home_edge else gm.home_rec
            model_p = gm.model_away_prob if gm.away_edge >= gm.home_edge else gm.model_home_prob
            dv_p    = dv_a if gm.away_edge >= gm.home_edge else dv_h
        else:
            if dv_a > dv_h:
                best_e, best_t, best_m = (dv_a - american_to_prob(a_ml)) * 100, away, a_ml
            else:
                best_e, best_t, best_m = (dv_h - american_to_prob(h_ml)) * 100, home, h_ml
            best_l = "PLAY" if best_e >= 2 else "LEAN"
            model_p = dv_a
            dv_p    = dv_a
    else:
        if dv_a > american_to_prob(a_ml):
            best_e, best_t, best_m = (dv_a - american_to_prob(a_ml)) * 100, away, a_ml
            dv_p = dv_a
        else:
            best_e, best_t, best_m = (dv_h - american_to_prob(h_ml)) * 100, home, h_ml
            dv_p = dv_h
        best_l = "PLAY" if best_e >= 2 else "LEAN"
        model_p = dv_p

    if best_e >= 1.0:
        top_plays.append({
            "sport":    sport,
            "away":     away,
            "home":     home,
            "time":     fmt_time(g.get("start_time","")),
            "a_ml":     a_ml,
            "h_ml":     h_ml,
            "edge":     best_e,
            "label":    best_l,
            "model_p":  model_p,
            "dv_p":     dv_p,
        })

top_plays.sort(key=lambda x: -x["edge"])

if top_plays:
    hero = top_plays[:3]
    cols = st.columns(3)
    for ci, p in enumerate(hero):
        with cols[ci]:
            render_game_card(
                sport=p["sport"],
                away_team=p["away"],
                home_team=p["home"],
                time_str=p["time"],
                away_ml=p["a_ml"],
                home_ml=p["h_ml"],
                edge_pct=p["edge"],
                recommendation=p["label"],
                model_prob=p["model_p"],
                market_prob=p["dv_p"]
            )
else:
    st.info("No plays with edge ≥1% found. Fetch fresh odds data.")

st.markdown("<br>", unsafe_allow_html=True)

# ── Today's full schedule ─────────────────────────────────────
st.subheader("🗓️ Full Slate")
if games:
    sched_rows = []
    for g in sorted(games, key=lambda x: x.get("start_time","")):
        rows  = load_odds_for_game(g["id"])
        a_ml  = best_ml(rows, g["away_team"])
        h_ml  = best_ml(rows, g["home_team"])
        a_str = (f"+{a_ml}" if a_ml > 0 else str(a_ml)) if a_ml else "—"
        h_str = (f"+{h_ml}" if h_ml > 0 else str(h_ml)) if h_ml else "—"
        sched_rows.append({
            "Sport":         g["sport"],
            "Time":          fmt_time(g.get("start_time","")),
            "Away":          g["away_team"],
            "Away ML":       a_str,
            "Home":          g["home_team"],
            "Home ML":       h_str,
        })
    df = pd.DataFrame(sched_rows)
    st.dataframe(df, width="stretch", hide_index=True)
else:
    st.warning("No games loaded. Sync data.")
