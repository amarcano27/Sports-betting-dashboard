"""
APEX ANALYTICS - NBA Model
"""
import sys
from pathlib import Path
import streamlit as st
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from utils.model import devig, american_to_prob
from dashboard.ui_components import render_game_card

@st.cache_data(ttl=120)
def load_nba_games():
    return supabase.table("games").select("*").eq("sport","NBA").order("start_time").execute().data or []

@st.cache_data(ttl=120)
def load_game_odds(game_id: str):
    return supabase.table("odds_snapshots").select("*").eq("game_id", game_id).execute().data or []

def best_price(rows, market, label):
    m = [r for r in rows if r.get("market_type") == market and r.get("market_label") == label]
    if not m: return None, None
    b = max(m, key=lambda r: r.get("price") or -9999)
    return int(b["price"]), b.get("book","?")

st.title("🏀 NBA Model")
st.caption("Market Devigging & Structural Analysis")

games = load_nba_games()
if not games:
    st.warning("No NBA games found in database.")
    st.stop()

cols = st.columns(2)

for idx, g in enumerate(games):
    away, home = g["away_team"], g["home_team"]
    try:
        t = datetime.fromisoformat(g["start_time"].replace("Z","+00:00"))
        time_str = t.strftime("%I:%M %p ET")
    except:
        time_str = "TBD"

    rows = load_game_odds(g["id"])
    away_ml, _ = best_price(rows, "h2h", away)
    home_ml, _ = best_price(rows, "h2h", home)

    if not away_ml or not home_ml:
        continue

    dv_a, dv_h = devig(away_ml, home_ml)
    
    if dv_a > dv_h:
        best_e = (dv_a - american_to_prob(away_ml)) * 100
        model_p = dv_a
        dv_p = dv_a
    else:
        best_e = (dv_h - american_to_prob(home_ml)) * 100
        model_p = dv_h
        dv_p = dv_h
        
    rec = "VALUE" if best_e >= 1.5 else "LEAN"

    with cols[idx % 2]:
        render_game_card(
            sport="NBA",
            away_team=away,
            home_team=home,
            time_str=time_str,
            away_ml=away_ml,
            home_ml=home_ml,
            edge_pct=best_e,
            recommendation=rec,
            model_prob=model_p,
            market_prob=dv_p
        )
