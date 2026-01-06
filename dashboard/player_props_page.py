"""
Enhanced Player Props Dashboard - Redesigned
Inspired by PrizePicks and optimizing tools
Removes repetitive sections, cleaner layout, prop card grid
"""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from services.grid_data_service import grid_service
from dashboard.player_props import format_odds, calculate_hitrate, create_prop_chart
from dashboard.ui_components import format_game_time
from rapidfuzz import process, fuzz

# Page config is handled by main.py when using st.navigation()

# Enhanced CSS - PrizePicks-inspired design
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #0e1117 0%, #1a1d29 100%);
    }
    .prop-type-chip {
        display: inline-block;
        padding: 0.5rem 1rem;
        margin: 0.25rem;
        background: #334155;
        color: #cbd5e1;
        border-radius: 20px;
        border: 2px solid #475569;
        cursor: pointer;
        transition: all 0.2s;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .prop-type-chip:hover {
        background: #475569;
        border-color: #64748b;
    }
    .prop-type-chip.active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-color: #667eea;
    }
    .player-prop-card {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        border-radius: 12px;
        padding: 1.25rem;
        margin: 0.75rem 0;
        border: 2px solid #475569;
        transition: all 0.3s ease;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
        position: relative;
    }
    .player-prop-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4);
        border-color: #64748b;
    }
    .prop-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }
    .prop-stat {
        font-size: 1.5rem;
        font-weight: 700;
        color: #f8fafc;
    }
    .prop-line {
        font-size: 2rem;
        font-weight: 700;
        color: #667eea;
        margin: 0.5rem 0;
    }
    .prop-odds-container {
        display: flex;
        gap: 1rem;
        margin: 1rem 0;
    }
    .odds-button {
        flex: 1;
        padding: 0.75rem;
        border-radius: 8px;
        text-align: center;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
        border: 2px solid;
    }
    .odds-button.over {
        background: rgba(16, 185, 129, 0.1);
        border-color: #10b981;
        color: #10b981;
    }
    .odds-button.under {
        background: rgba(239, 68, 68, 0.1);
        border-color: #ef4444;
        color: #ef4444;
    }
    .odds-button:hover {
        transform: scale(1.02);
        opacity: 0.9;
    }
    .hitrate-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-left: 0.5rem;
    }
    .hitrate-badge.good {
        background: rgba(16, 185, 129, 0.2);
        color: #10b981;
    }
    .hitrate-badge.bad {
        background: rgba(239, 68, 68, 0.2);
        color: #ef4444;
    }
    .player-search-result {
        padding: 0.75rem;
        margin: 0.5rem 0;
        background: rgba(30, 41, 59, 0.5);
        border-radius: 8px;
        border: 1px solid #475569;
        cursor: pointer;
        transition: all 0.2s;
    }
    .player-search-result:hover {
        background: rgba(51, 65, 85, 0.7);
        border-color: #64748b;
    }
    .player-search-result.selected {
        background: rgba(102, 126, 234, 0.2);
        border-color: #667eea;
    }
    .compact-header {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1.5rem;
    }
    .player-avatar-small {
        width: 50px;
        height: 50px;
        border-radius: 50%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        font-weight: bold;
        color: white;
        flex-shrink: 0;
    }
    .player-info-compact h2 {
        margin: 0;
        color: #f8fafc;
        font-size: 1.5rem;
    }
    .player-info-compact p {
        margin: 0.25rem 0 0 0;
        color: #94a3b8;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "selected_player_props" not in st.session_state:
    st.session_state.selected_player_props = None
if "selected_prop_type_filter" not in st.session_state:
    st.session_state.selected_prop_type_filter = "All"

# Helper functions
@st.cache_data(ttl=300)
def load_games_for_props(sport):
    cutoff_date = (datetime.now() + timedelta(days=7)).isoformat()
    games = (
        supabase.table("games")
        .select("*")
        .eq("sport", sport)
        .gte("start_time", datetime.now().isoformat())
        .lte("start_time", cutoff_date)
        .order("start_time")
        .execute()
        .data
    )
    return games

@st.cache_data(ttl=600)
def load_all_players_for_search(sport):
    try:
        query = supabase.table("players").select("*")
        if sport == "Esports":
            sub_sports = ["CS2", "LoL", "Dota2", "Valorant"]
            query = query.in_("sport", sub_sports)
        else:
            query = query.eq("sport", sport)
        
        players = (
            query.order("name")
            .execute()
            .data
        )
        return players
    except Exception as e:
        st.warning("⚠️ **Database unavailable. Using demo data.**\n\n💡 For production use, configure API keys in `.env` file. See `API_SETUP.md` for instructions.")
        from dashboard.demo_data_loader import get_demo_players
        return get_demo_players(sport)

@st.cache_data(ttl=300)
def load_player_props_for_player(player_id, game_id):
    """Load all props for a specific player in a game"""
    try:
        props = (
            supabase.table("player_prop_odds")
            .select("*")
            .eq("player_id", player_id)
            .eq("game_id", game_id)
            .order("prop_type")
            .execute()
            .data
        )
        return props
    except Exception as e:
        # Return empty list if database unavailable
        from dashboard.demo_data_loader import get_demo_props
        all_props = get_demo_props("NBA", [game_id])
        return [p for p in all_props if p.get("player_id") == player_id]

@st.cache_data(ttl=300)
def load_player_stats_for_hitrate(player_id, prop_type):
    """Load player stats for hitrate calculation"""
    stats = (
        supabase.table("player_game_stats")
        .select("*")
        .eq("player_id", player_id)
        .order("date", desc=True)
        .limit(30)
        .execute()
        .data
    )
    return stats

def fuzzy_search_players(query, players, limit=10):
    """Fuzzy search for players"""
    if not query or len(query) < 2:
        return []
    
    search_strings = [
        f"{p['name']} ({p.get('position', 'N/A')} - {p.get('team', 'N/A')})" 
        for p in players
    ]
    
    matches = process.extract(query, search_strings, limit=limit, score_cutoff=50)
    
    results = []
    seen_ids = set()
    for match_str, score, _ in matches:
        player_name = match_str.split(" (")[0]
        player = next((p for p in players if p['name'] == player_name), None)
        if player and player['id'] not in seen_ids:
            results.append(player)
            seen_ids.add(player['id'])
    
    return results

# Title
st.title("🎯 Player Props Dashboard")

# Streamlined sidebar - NO REPETITION
with st.sidebar:
    st.header("🔍 Quick Search")
    
    sport = st.selectbox("Sport", ["NBA", "NFL", "MLB", "NHL", "NCAAB", "NCAAF", "Esports"], index=0)
    
    # Single search input - no repetitive fields
    player_query = st.text_input(
        "Search Player", 
        value="",
        key="player_search_main",
        placeholder="Type player name (e.g., 'Devin', 'Booker')..."
    )
    
    # Load players and search
    all_players = load_all_players_for_search(sport)
    search_results = []
    
    if player_query:
        search_results = fuzzy_search_players(player_query, all_players, limit=8)
    
    # Show search results
    if search_results:
        st.write(f"**Found {len(search_results)} players:**")
        for player in search_results:
            is_selected = (st.session_state.selected_player_props and 
                          st.session_state.selected_player_props.get('id') == player.get('id'))
            
            player_display = f"{player['name']} ({player.get('position', 'N/A')} - {player.get('team', 'N/A')})"
            
            if st.button(
                player_display, 
                key=f"select_player_{player.get('id')}",
                use_container_width=True,
                type="primary" if is_selected else "secondary"
            ):
                st.session_state.selected_player_props = player
                st.rerun()
    elif player_query and len(player_query) >= 2:
        st.info("No players found. Try a different search or sync players.")
    
    st.divider()
    
    # Game selection (only if player selected) - simplified, NO REPETITION
    if st.session_state.selected_player_props:
        st.subheader("Select Game")
        games = load_games_for_props(sport)
        if games:
            # Filter games to only show games with this player's team
            player_team = st.session_state.selected_player_props.get("team")
            relevant_games = [
                g for g in games 
                if player_team in [g.get("home_team"), g.get("away_team")]
            ] if player_team else games
            
            if relevant_games:
                game_options = [
                    f"{g['away_team']} @ {g['home_team']} - {format_game_time(g['start_time'])}" 
                    for g in relevant_games
                ]
                # Initialize session state
                if "selected_game_idx" not in st.session_state:
                    st.session_state.selected_game_idx = 0
                
                selected_game_idx = st.selectbox(
                    "Game", 
                    range(len(game_options)), 
                    format_func=lambda x: game_options[x],
                    key="game_select_props",
                    index=st.session_state.selected_game_idx
                )
                st.session_state.selected_game_idx = selected_game_idx
            else:
                # Fallback to all games
                game_options = [
                    f"{g['away_team']} @ {g['home_team']} - {format_game_time(g['start_time'])}" 
                    for g in games
                ]
                if "selected_game_idx_all" not in st.session_state:
                    st.session_state.selected_game_idx_all = 0
                
                selected_game_idx = st.selectbox(
                    "Game", 
                    range(len(game_options)), 
                    format_func=lambda x: game_options[x],
                    key="game_select_props_all",
                    index=st.session_state.selected_game_idx_all
                )
                st.session_state.selected_game_idx_all = selected_game_idx
        else:
            st.warning("No games available")
    else:
        st.info("👆 Search and select a player first")
    
    st.divider()
    
    if st.button("🔄 Sync Players", use_container_width=True):
        st.info("Run: python workers/fetch_player_stats.py --sync-players")

# Main content
if not st.session_state.selected_player_props:
    # Show welcome/search state
    st.markdown("""
    <div style="text-align: center; padding: 3rem 2rem; color: #94a3b8;">
        <h2>🔍 Search for a Player</h2>
        <p>Use the sidebar to search for a player by name</p>
        <p style="margin-top: 1rem;">Example: Type "Devin" to find Devin Booker, Devin Vassell, etc.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Player selected - show props
selected_player = st.session_state.selected_player_props
player_id = selected_player.get("id")
player_name = selected_player.get("name", "Unknown")
player_position = selected_player.get("position", "N/A")
player_team = selected_player.get("team", "N/A")

# Get selected game - use the same logic as sidebar
games = load_games_for_props(sport)
selected_game = None

if games and st.session_state.selected_player_props:
    player_team = st.session_state.selected_player_props.get("team")
    relevant_games = [
        g for g in games 
        if player_team in [g.get("home_team"), g.get("away_team")]
    ] if player_team else games
    
    if relevant_games:
        if "selected_game_idx" in st.session_state:
            selected_game_idx = st.session_state.selected_game_idx
            if selected_game_idx < len(relevant_games):
                selected_game = relevant_games[selected_game_idx]
    elif games:
        # Fallback to all games
        if "selected_game_idx_all" in st.session_state:
            selected_game_idx = st.session_state.selected_game_idx_all
            if selected_game_idx < len(games):
                selected_game = games[selected_game_idx]

if not selected_game:
    st.warning("⚠️ Please select a game from the sidebar")
    st.info("💡 Games are filtered to show only games with this player's team")
    st.stop()

# Compact player header
initials = "".join([name[0] for name in player_name.split()[:2]])
st.markdown(f"""
<div class="compact-header">
    <div class="player-avatar-small">{initials}</div>
    <div class="player-info-compact">
        <h2>{player_name}</h2>
        <p>{player_position} • {player_team} • {format_game_time(selected_game['start_time'])}</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Esports Insights (GRID)
if sport == "Esports":
    with st.expander("🎮 Team Insights & History (GRID)", expanded=True):
        with st.spinner("Loading GRID insights..."):
            # 1. Find Team
            teams = grid_service.get_teams(search_term=player_team, limit=1)
            if teams:
                team_obj = teams[0]
                t_id = team_obj.get("id")
                
                c1, c2, c3 = st.columns([1, 2, 2])
                with c1:
                    if team_obj.get('logoUrl'):
                        st.image(team_obj['logoUrl'], width=80)
                    st.markdown(f"**GRID Rating:** {team_obj.get('rating', 'N/A')}")
                    st.caption(f"ID: {t_id}")
                
                with c2:
                    st.markdown("**📅 Recent Matches**")
                    hist = grid_service.get_team_history(t_id, limit=3)
                    if hist:
                        for h in hist:
                            start = h.get('startTimeScheduled', '')[:10]
                            opp = "Unknown"
                            for t in h.get('teams', []):
                                if t.get('baseInfo', {}).get('id') != t_id:
                                    opp = t.get('baseInfo', {}).get('name')
                            st.markdown(f"vs **{opp}** <span style='color:#888; font-size:0.8em'>({start})</span>", unsafe_allow_html=True)
                    else:
                        st.caption("No recent history.")
                        
                with c3:
                    st.markdown("**🔮 Matchup Analysis**")
                    if selected_game:
                        # Use normalize_team_name for proper team matching
                        from utils.team_mapping import normalize_team_name
                        player_team_norm = normalize_team_name(player_team)
                        home_team_norm = normalize_team_name(selected_game['home_team'])
                        away_team_norm = normalize_team_name(selected_game['away_team'])
                        
                        if player_team_norm == home_team_norm or player_team == selected_game['home_team']:
                            opp_name = selected_game['away_team']
                        elif player_team_norm == away_team_norm or player_team == selected_game['away_team']:
                            opp_name = selected_game['home_team']
                        else:
                            # Fallback
                            opp_name = selected_game['away_team'] if selected_game['home_team'] == player_team else selected_game['home_team']
                        # Clean opponent name for search (remove TAGs if any?)
                        opp_search = grid_service.get_teams(search_term=opp_name, limit=1)
                        if opp_search:
                            opp_obj = opp_search[0]
                            r1 = team_obj.get('rating') or 1000
                            r2 = opp_obj.get('rating') or 1000
                            
                            diff = r1 - r2
                            prob = 1 / (1 + 10**(-diff/400))
                            
                            st.progress(prob)
                            st.markdown(f"Win Prob: **{prob*100:.1f}%**")
                            if prob > 0.6:
                                st.success(f"Favorite vs {opp_name}")
                            elif prob < 0.4:
                                st.error(f"Underdog vs {opp_name}")
                            else:
                                st.warning(f"Close match vs {opp_name}")
                        else:
                            st.caption(f"Opponent '{opp_name}' data not found.")
                    else:
                        st.caption("Select a game to see matchup analysis.")
            else:
                st.info(f"Could not find GRID data for team: {player_team}")

# Esports Insights (GRID)
if sport == "Esports":
    with st.expander("🎮 Team Insights & History (GRID)", expanded=True):
        with st.spinner("Loading GRID insights..."):
            # 1. Find Team
            teams = grid_service.get_teams(search_term=player_team, limit=1)
            if teams:
                team_obj = teams[0]
                t_id = team_obj.get("id")
                
                c1, c2, c3 = st.columns([1, 2, 2])
                with c1:
                    if team_obj.get('logoUrl'):
                        st.image(team_obj['logoUrl'], width=80)
                    st.markdown(f"**GRID Rating:** {team_obj.get('rating', 'N/A')}")
                    st.caption(f"ID: {t_id}")
                
                with c2:
                    st.markdown("**📅 Recent Matches**")
                    hist = grid_service.get_team_history(t_id, limit=3)
                    if hist:
                        for h in hist:
                            start = h.get('startTimeScheduled', '')[:10]
                            opp = "Unknown"
                            for t in h.get('teams', []):
                                if t.get('baseInfo', {}).get('id') != t_id:
                                    opp = t.get('baseInfo', {}).get('name')
                            st.markdown(f"vs **{opp}** <span style='color:#888; font-size:0.8em'>({start})</span>", unsafe_allow_html=True)
                    else:
                        st.caption("No recent history.")
                        
                with c3:
                    st.markdown("**🔮 Matchup Analysis**")
                    if selected_game:
                        # Use normalize_team_name for proper team matching
                        from utils.team_mapping import normalize_team_name
                        player_team_norm = normalize_team_name(player_team)
                        home_team_norm = normalize_team_name(selected_game['home_team'])
                        away_team_norm = normalize_team_name(selected_game['away_team'])
                        
                        if player_team_norm == home_team_norm or player_team == selected_game['home_team']:
                            opp_name = selected_game['away_team']
                        elif player_team_norm == away_team_norm or player_team == selected_game['away_team']:
                            opp_name = selected_game['home_team']
                        else:
                            # Fallback
                            opp_name = selected_game['away_team'] if selected_game['home_team'] == player_team else selected_game['home_team']
                        # Clean opponent name for search (remove TAGs if any?)
                        opp_search = grid_service.get_teams(search_term=opp_name, limit=1)
                        if opp_search:
                            opp_obj = opp_search[0]
                            r1 = team_obj.get('rating') or 1000
                            r2 = opp_obj.get('rating') or 1000
                            
                            diff = r1 - r2
                            prob = 1 / (1 + 10**(-diff/400))
                            
                            st.progress(prob)
                            st.markdown(f"Win Prob: **{prob*100:.1f}%**")
                            if prob > 0.6:
                                st.success(f"Favorite vs {opp_name}")
                            elif prob < 0.4:
                                st.error(f"Underdog vs {opp_name}")
                            else:
                                st.warning(f"Close match vs {opp_name}")
                        else:
                            st.caption(f"Opponent '{opp_name}' data not found.")
                    else:
                        st.caption("Select a game to see matchup analysis.")
            else:
                st.info(f"Could not find GRID data for team: {player_team}")

# Prop type filter chips (PrizePicks style)
st.subheader("Prop Types")
prop_types = ["All", "Points", "Rebounds", "Assists", "PRA", "Threes", "Steals", "Blocks"]

# Create filter chips
cols = st.columns(len(prop_types))
selected_prop_filter = st.session_state.selected_prop_type_filter

for i, prop_type in enumerate(prop_types):
    with cols[i]:
        is_active = selected_prop_filter == prop_type
        if st.button(
            prop_type,
            key=f"prop_filter_{i}",
            use_container_width=True,
            type="primary" if is_active else "secondary"
        ):
            st.session_state.selected_prop_type_filter = prop_type
            st.rerun()

# Load props for this player/game
player_props = load_player_props_for_player(player_id, selected_game["id"])

if not player_props:
    st.info("No props available for this player. Fetch player prop odds first.")
    st.code("python workers/fetch_player_prop_odds.py")
    st.stop()

# Filter by prop type
filtered_props = player_props
if selected_prop_filter != "All":
    prop_type_map = {
        "Points": "points",
        "Rebounds": "rebounds",
        "Assists": "assists",
        "PRA": "pra",
        "Threes": "threes",
        "Steals": "steals",
        "Blocks": "blocks"
    }
    filter_type = prop_type_map.get(selected_prop_filter, "")
    filtered_props = [p for p in player_props if p.get("prop_type") == filter_type]

# Group props by type and line
props_by_type = {}
for prop in filtered_props:
    prop_type = prop.get("prop_type", "unknown")
    line = prop.get("line")
    book = prop.get("book", "Unknown")
    
    key = (prop_type, line)
    if key not in props_by_type:
        props_by_type[key] = {
            "prop_type": prop_type,
            "line": line,
            "books": {}
        }
    
    # Store best odds per book
    if book not in props_by_type[key]["books"]:
        props_by_type[key]["books"][book] = {
            "over_price": prop.get("over_price"),
            "under_price": prop.get("under_price")
        }
    else:
        # Keep best odds
        if prop.get("over_price"):
            existing_over = props_by_type[key]["books"][book]["over_price"]
            if existing_over is None or (prop.get("over_price") and prop.get("over_price") > existing_over):
                props_by_type[key]["books"][book]["over_price"] = prop.get("over_price")
        if prop.get("under_price"):
            existing_under = props_by_type[key]["books"][book]["under_price"]
            if existing_under is None or (prop.get("under_price") and prop.get("under_price") > existing_under):
                props_by_type[key]["books"][book]["under_price"] = prop.get("under_price")

# Display props in grid (PrizePicks style)
st.subheader(f"Available Props ({len(props_by_type)})")

# Get player stats for hitrate
player_stats = load_player_stats_for_hitrate(player_id, "points")

# Create columns for grid
num_cols = 3
cols = st.columns(num_cols)

for idx, ((prop_type, line), prop_data) in enumerate(props_by_type.items()):
    with cols[idx % num_cols]:
        # Get best odds across all books
        best_over = None
        best_under = None
        best_over_book = None
        best_under_book = None
        
        for book, odds in prop_data["books"].items():
            if odds.get("over_price") and (best_over is None or odds["over_price"] > best_over):
                best_over = odds["over_price"]
                best_over_book = book
            if odds.get("under_price") and (best_under is None or odds["under_price"] > best_under):
                best_under = odds["under_price"]
                best_under_book = book
        
        # Calculate hitrate if stats available
        hitrate_info = ""
        if player_stats and prop_type in ["points", "rebounds", "assists"]:
            hitrate_data = calculate_hitrate(
                [{"date": s.get("date"), prop_type: s.get(prop_type, 0)} for s in player_stats],
                prop_type,
                line
            )
            if hitrate_data and hitrate_data.get("hitrates"):
                l10_hitrate = hitrate_data["hitrates"].get("L10", hitrate_data["hitrates"].get("L30", 0))
                if l10_hitrate:
                    hitrate_class = "good" if l10_hitrate > 50 else "bad"
                    hitrate_info = f'<span class="hitrate-badge {hitrate_class}">{l10_hitrate:.0f}% L10</span>'
        
        # Create prop card
        prop_type_display = prop_type.replace("_", " ").title()
        
        card_html = f"""
        <div class="player-prop-card">
            <div class="prop-header">
                <div>
                    <div class="prop-stat">{prop_type_display}</div>
                    <div class="prop-line">{line}</div>
                </div>
                {hitrate_info}
            </div>
            <div class="prop-odds-container">
        """
        
        if best_over:
            card_html += f"""
                <div class="odds-button over">
                    <div style="font-size: 0.75rem; opacity: 0.8;">Over</div>
                    <div style="font-size: 1.1rem; font-weight: 700;">{format_odds(int(best_over))}</div>
                    <div style="font-size: 0.7rem; opacity: 0.7;">{best_over_book}</div>
                </div>
            """
        else:
            card_html += '<div class="odds-button over" style="opacity: 0.5;">Over N/A</div>'
        
        if best_under:
            card_html += f"""
                <div class="odds-button under">
                    <div style="font-size: 0.75rem; opacity: 0.8;">Under</div>
                    <div style="font-size: 1.1rem; font-weight: 700;">{format_odds(int(best_under))}</div>
                    <div style="font-size: 0.7rem; opacity: 0.7;">{best_under_book}</div>
                </div>
            """
        else:
            card_html += '<div class="odds-button under" style="opacity: 0.5;">Under N/A</div>'
        
        card_html += "</div></div>"
        
        st.markdown(card_html, unsafe_allow_html=True)
        
        # Add buttons for adding to slip
        if best_over or best_under:
            col_a, col_b = st.columns(2)
            with col_a:
                if best_over and st.button(f"➕ Over", key=f"add_over_{prop_type}_{line}_{idx}", use_container_width=True):
                    st.success("Added to slip!")
            with col_b:
                if best_under and st.button(f"➕ Under", key=f"add_under_{prop_type}_{line}_{idx}", use_container_width=True):
                    st.success("Added to slip!")

# Game Lines Section
st.divider()
st.subheader("Game Lines")

# Load game odds
@st.cache_data(ttl=300)
def load_game_odds(game_id):
    odds = (
        supabase.table("odds_snapshots")
        .select("*")
        .eq("game_id", game_id)
        .order("created_at", desc=True)
        .execute()
        .data
    )
    return odds

game_odds = load_game_odds(selected_game["id"])

if game_odds:
    # Create comparison table
    lines_data = {
        "Team": [selected_game["away_team"], selected_game["home_team"]],
        "Spread": ["", ""],
        "Total": ["", ""],
        "Moneyline": ["", ""]
    }
    
    for odd in game_odds:
        if odd["market_type"] == "h2h":
            if odd["market_label"] == selected_game["away_team"]:
                lines_data["Moneyline"][0] = format_odds(odd["price"])
            elif odd["market_label"] == selected_game["home_team"]:
                lines_data["Moneyline"][1] = format_odds(odd["price"])
        elif odd["market_type"] == "spreads":
            if odd["market_label"] == selected_game["away_team"]:
                lines_data["Spread"][0] = f"{odd.get('line', 'N/A')} | {format_odds(odd['price'])}"
            elif odd["market_label"] == selected_game["home_team"]:
                lines_data["Spread"][1] = f"{odd.get('line', 'N/A')} | {format_odds(odd['price'])}"
        elif odd["market_type"] == "totals":
            if odd["market_label"] == "Over":
                lines_data["Total"][0] = f"Over {odd.get('line', 'N/A')} | {format_odds(odd['price'])}"
            elif odd["market_label"] == "Under":
                lines_data["Total"][1] = f"Under {odd.get('line', 'N/A')} | {format_odds(odd['price'])}"
    
    lines_df = pd.DataFrame(lines_data)
    st.dataframe(lines_df, use_container_width=True, hide_index=True)
else:
    st.info("No game lines available")

# Statistics and Charts Section
if player_stats:
    st.divider()
    st.subheader("Performance Trends")
    
    # Show hitrates for different prop types
    prop_types_to_show = ["points", "rebounds", "assists"]
    hitrate_tabs = st.tabs([pt.title() for pt in prop_types_to_show])
    
    for tab_idx, prop_type in enumerate(prop_types_to_show):
        with hitrate_tabs[tab_idx]:
            # Get props for this type
            type_props = [p for p in player_props if p.get("prop_type") == prop_type]
            if type_props:
                # Use the most common line
                lines = [p.get("line") for p in type_props if p.get("line")]
                if lines:
                    common_line = max(set(lines), key=lines.count)
                    hitrate_data = calculate_hitrate(
                        [{"date": s.get("date"), prop_type: s.get(prop_type, 0)} for s in player_stats],
                        prop_type,
                        common_line
                    )
                    
                    if hitrate_data:
                        periods = ["L5", "L10", "L20", "Season"]
                        hitrate_table = {
                            "Period": periods,
                            "Average": [hitrate_data["averages"].get(p, "N/A") for p in periods],
                            "Hitrate (%)": [hitrate_data["hitrates"].get(p, "N/A") for p in periods]
                        }
                        st.dataframe(pd.DataFrame(hitrate_table), use_container_width=True, hide_index=True)
                        
                        # Show chart
                        chart_fig = create_prop_chart(
                            [{"date": s.get("date"), prop_type: s.get(prop_type, 0)} for s in player_stats[:15]],
                            prop_type,
                            common_line,
                            title=f"{prop_type.title()} Performance"
                        )
                        st.plotly_chart(chart_fig, use_container_width=True)

