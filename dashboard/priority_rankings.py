"""
APEX ANALYTICS - Top Edges
"""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from utils.model import devig, american_to_prob
from dashboard.mlb_page import find_pitcher, build_game_model
from dashboard.ui_components import render_game_card

@st.cache_data(ttl=60)
def load_all_games():
    return supabase.table("games").select("*").order("start_time").execute().data or []

@st.cache_data(ttl=60)
def load_odds_for_game(game_id: str):
    return supabase.table("odds_snapshots").select("*").eq("game_id", game_id).execute().data or []

def best_ml(rows, team):
    m = [r for r in rows if r.get("market_type")=="h2h" and r.get("market_label")==team]
    if not m: return None
    return int(max(m, key=lambda r: r.get("price") or -9999).get("price", 0))

st.title("⚡ Top Edges")
st.caption("All sports sorted by raw mathematical edge.")

games = load_all_games()
plays = []

for g in games:
    sport = g.get("sport", "?")
    rows  = load_odds_for_game(g["id"])
    away, home = g["away_team"], g["home_team"]
    a_ml = best_ml(rows, away)
    h_ml = best_ml(rows, home)
    if not a_ml or not h_ml: continue

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

    try:
        t = datetime.fromisoformat(g["start_time"].replace("Z","+00:00"))
        time_str = t.strftime("%I:%M %p ET")
    except:
        time_str = "TBD"

    plays.append({
        "sport": sport, "away": away, "home": home, "time": time_str,
        "a_ml": a_ml, "h_ml": h_ml, "edge": best_e, "label": best_l,
        "model_p": model_p, "dv_p": dv_p
    })

plays.sort(key=lambda x: -x["edge"])

if not plays:
    st.info("No plays found.")
    st.stop()

cols = st.columns(2)
for idx, p in enumerate(plays):
    with cols[idx % 2]:
        render_game_card(
            sport=p["sport"], away_team=p["away"], home_team=p["home"],
            time_str=p["time"], away_ml=p["a_ml"], home_ml=p["h_ml"],
            edge_pct=p["edge"], recommendation=p["label"],
            model_prob=p["model_p"], market_prob=p["dv_p"]
        )
