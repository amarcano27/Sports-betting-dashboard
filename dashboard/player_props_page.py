"""
APEX ANALYTICS - Prop Matrix
The ultimate player props dashboard.
"""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
from datetime import datetime
from rapidfuzz import process

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from dashboard.ui_components import render_prop_card
from dashboard.player_props import calculate_hitrate

# ── DATA LOADERS ──────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_all_players(sport: str):
    query = supabase.table("players").select("id, name, team, position, external_id, image_url, raw_data")
    if sport != "All":
        query = query.eq("sport", sport)
    return query.execute().data or []

@st.cache_data(ttl=300)
def load_prop_odds(player_id: str):
    return supabase.table("player_prop_odds").select("*").eq("player_id", player_id).order("created_at", desc=True).limit(50).execute().data or []

def get_headshot(player: dict) -> str:
    if player.get("image_url"):
        return player["image_url"]
    
    raw = player.get("raw_data", {})
    if isinstance(raw, str):
        import json
        try:
            raw = json.loads(raw)
        except:
            raw = {}
    
    if raw.get("headshot_url"):
        return raw["headshot_url"]
        
    ext_id = player.get("external_id", "")
    if ext_id and "nba" in str(player.get("sport", "")).lower():
        return f"https://cdn.nba.com/headshots/nba/latest/1040x760/{ext_id}.png"
    return None

# ── MAIN ──────────────────────────────────────────────────────
st.title("🎯 Prop Matrix")

# Search & Filters
col1, col2 = st.columns([1, 3])
with col1:
    sport_filter = st.selectbox("Sport", ["All", "NBA", "MLB", "NHL", "NFL", "Esports"])
with col2:
    search_query = st.text_input("Search Player", placeholder="e.g. LeBron James, Shohei Ohtani...")

players = load_all_players(sport_filter)

if search_query and len(search_query) >= 2:
    search_strings = [p['name'] for p in players]
    matches = process.extract(search_query, search_strings, limit=5, score_cutoff=60)
    
    if matches:
        st.markdown("### Select Player")
        cols = st.columns(len(matches))
        for i, (match_name, score, _) in enumerate(matches):
            p = next(p for p in players if p['name'] == match_name)
            with cols[i]:
                if st.button(f"{p['name']}\n{p.get('team', '')}", key=f"p_{p['id']}", use_container_width=True):
                    st.session_state.selected_prop_player = p
                    st.rerun()
    else:
        st.warning("No players found.")

st.markdown("<hr style='border-color: #1E293B;'>", unsafe_allow_html=True)

# Selected Player View
if "selected_prop_player" in st.session_state:
    player = st.session_state.selected_prop_player
    st.subheader(f"Props for {player['name']}")
    
    odds = load_prop_odds(player['id'])
    
    if not odds:
        st.info("No active props found for this player in the database.")
    else:
        # Group by prop type
        props_by_type = {}
        for o in odds:
            ptype = o["prop_type"]
            line = o["line"]
            key = f"{ptype}_{line}"
            
            if key not in props_by_type:
                props_by_type[key] = {
                    "type": ptype,
                    "line": line,
                    "over": None,
                    "under": None,
                    "game_id": o.get("game_id")
                }
            
            if o.get("over_price"):
                curr = props_by_type[key]["over"]
                if curr is None or o["over_price"] > curr:
                    props_by_type[key]["over"] = o["over_price"]
                    
            if o.get("under_price"):
                curr = props_by_type[key]["under"]
                if curr is None or o["under_price"] > curr:
                    props_by_type[key]["under"] = o["under_price"]
        
        # Display Grid
        grid_cols = st.columns(3)
        for idx, (k, p_data) in enumerate(props_by_type.items()):
            with grid_cols[idx % 3]:
                # Mock projection for now (would connect to projections.py)
                mock_proj = p_data["line"] * 1.05
                edge = ((mock_proj - p_data["line"]) / p_data["line"]) * 100
                
                render_prop_card(
                    player_name=player["name"],
                    team=player.get("team", "UNK"),
                    opponent="TBD",
                    game_time="Today",
                    prop_type=p_data["type"],
                    line=p_data["line"],
                    over_odds=p_data["over"],
                    under_odds=p_data["under"],
                    model_proj=mock_proj,
                    edge_pct=edge,
                    image_url=get_headshot(player)
                )
else:
    st.info("Search and select a player to view their prop matrix.")
