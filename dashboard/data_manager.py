"""
APEX ANALYTICS - Data Sync
"""
import sys
from pathlib import Path
import streamlit as st
import subprocess
import os

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase

st.title("🔄 Data Sync")
st.caption("Manage API fetches and database population.")

def run_worker(script_name: str, args: list):
    script_path = os.path.join(project_root, "workers", script_name)
    cmd = [sys.executable, script_path] + args
    
    with st.spinner(f"Running {script_name} {' '.join(args)}..."):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            st.success("Sync complete!")
            with st.expander("View Logs"):
                st.code(result.stdout)
        except subprocess.CalledProcessError as e:
            st.error(f"Sync failed (Exit {e.returncode})")
            with st.expander("View Error Logs"):
                st.code(e.stderr or e.stdout)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Odds Data (Costs Credits)")
    st.caption("Fetches live market odds from The Odds API.")
    
    if st.button("Fetch MLB Odds", use_container_width=True):
        run_worker("fetch_all_odds.py", ["--sport", "mlb"])
        
    if st.button("Fetch NBA Odds", use_container_width=True):
        run_worker("fetch_all_odds.py", ["--sport", "nba"])
        
    if st.button("Fetch NHL Odds", use_container_width=True):
        run_worker("fetch_all_odds.py", ["--sport", "nhl"])

with col2:
    st.subheader("Player Data (Free)")
    st.caption("Fetches rosters and recent game logs.")
    
    if st.button("Fetch MLB Players", use_container_width=True):
        run_worker("fetch_live_players.py", ["--sport", "mlb"])
        
    if st.button("Fetch NBA Players", use_container_width=True):
        run_worker("fetch_live_players.py", ["--sport", "nba"])
        
    if st.button("Fetch NHL Players", use_container_width=True):
        run_worker("fetch_live_players.py", ["--sport", "nhl"])

st.markdown("<hr style='border-color: #1E293B; margin: 32px 0;'>", unsafe_allow_html=True)

st.subheader("Database Status")
try:
    games = len(supabase.table("games").select("id").execute().data or [])
    odds = len(supabase.table("odds_snapshots").select("id").limit(1000).execute().data or [])
    players = len(supabase.table("players").select("id").execute().data or [])
    logs = len(supabase.table("player_game_stats").select("id").limit(1000).execute().data or [])
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Games", games)
    c2.metric("Odds Rows", f"{odds}+")
    c3.metric("Players", players)
    c4.metric("Game Logs", f"{logs}+")
except Exception as e:
    st.error(f"Could not connect to database: {e}")
