"""
APEX ANALYTICS - Line Shopping
"""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase

@st.cache_data(ttl=60)
def load_all_games():
    return supabase.table("games").select("*").order("start_time").execute().data or []

@st.cache_data(ttl=60)
def load_odds_for_game(game_id: str):
    return supabase.table("odds_snapshots").select("*").eq("game_id", game_id).eq("market_type", "h2h").execute().data or []

st.title("⚖️ Line Shopping")
st.caption("Compare moneylines across all books.")

games = load_all_games()
if not games:
    st.warning("No games found.")
    st.stop()
    
game_opts = [f"{g['away_team']} @ {g['home_team']}" for g in games]
sel_idx = st.selectbox("Select Game", range(len(game_opts)), format_func=lambda x: game_opts[x])
sel_game = games[sel_idx]

rows = load_odds_for_game(sel_game["id"])
if not rows:
    st.info("No odds data for this game.")
    st.stop()

away_books = []
home_books = []

for r in rows:
    if r.get("market_label") == sel_game["away_team"]:
        away_books.append({"Book": r.get("book"), "Odds": int(r.get("price", 0))})
    elif r.get("market_label") == sel_game["home_team"]:
        home_books.append({"Book": r.get("book"), "Odds": int(r.get("price", 0))})

away_books.sort(key=lambda x: -x["Odds"])
home_books.sort(key=lambda x: -x["Odds"])

c1, c2 = st.columns(2)
with c1:
    st.subheader(sel_game["away_team"])
    if away_books:
        st.dataframe(pd.DataFrame(away_books), width="stretch", hide_index=True)
with c2:
    st.subheader(sel_game["home_team"])
    if home_books:
        st.dataframe(pd.DataFrame(home_books), width="stretch", hide_index=True)
