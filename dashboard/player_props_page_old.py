"""
Player Props Dashboard - Main page matching the reference design
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
from dashboard.player_props import (
    format_odds, 
    calculate_hitrate, 
    create_prop_chart, 
    display_game_lines
)
from rapidfuzz import process, fuzz

# Page config is handled by main.py when using st.navigation()
# Removed to avoid conflicts

# Dark theme CSS - matching the reference design
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {
        background-color: #0e1117;
    }
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    .player-header-container {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1rem 0;
        margin-bottom: 1rem;
    }
    .player-avatar {
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        font-weight: bold;
        color: white;
        flex-shrink: 0;
    }
    .player-info h2 {
        margin: 0;
        color: #fafafa;
        font-size: 1.5rem;
    }
    .player-info p {
        margin: 0.25rem 0 0 0;
        color: #94a3b8;
        font-size: 0.9rem;
    }
    .prop-category-button {
        background-color: #10b981;
        color: white;
        border: none;
        padding: 0.5rem 1.5rem;
        border-radius: 4px;
        font-weight: 500;
        cursor: pointer;
    }
    .prop-category-button.inactive {
        background-color: #1e293b;
        color: #94a3b8;
    }
    .game-lines-container {
        background-color: #1e293b;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .metric-container {
        background-color: #1e293b;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Helper functions for loading data
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
def load_players(sport, team=None):
    """Load players from database"""
    query = supabase.table("players").select("*").eq("sport", sport)
    if team:
        query = query.eq("team", team)
    players = query.order("name").execute().data
    return players

@st.cache_data(ttl=600)
def load_all_players_for_search(sport):
    """Load all players for fuzzy search"""
    players = (
        supabase.table("players")
        .select("*")
        .eq("sport", sport)
        .order("name")
        .execute()
        .data
    )
    return players

def fuzzy_search_players(query, players, limit=10):
    """Fuzzy search for players with autocomplete"""
    if not query or len(query) < 2:
        return []
    
    # Create searchable strings with context
    search_strings = [
        f"{p['name']} ({p.get('position', 'N/A')} - {p.get('team', 'N/A')})" 
        for p in players
    ]
    
    # Fuzzy match with score cutoff
    matches = process.extract(query, search_strings, limit=limit, score_cutoff=50)
    
    # Get full player objects
    results = []
    seen_ids = set()
    for match_str, score, _ in matches:
        # Extract player name from match string
        player_name = match_str.split(" (")[0]
        player = next((p for p in players if p['name'] == player_name), None)
        if player and player['id'] not in seen_ids:
            results.append(player)
            seen_ids.add(player['id'])
    
    return results

@st.cache_data(ttl=300)
def search_players(sport, query):
    """Search players by name (legacy - uses fuzzy now)"""
    all_players = load_all_players_for_search(sport)
    return fuzzy_search_players(query, all_players, limit=20)

# Title
st.title("🎯 Player Props Dashboard")

# Sidebar for game/player selection
with st.sidebar:
    st.header("🎯 Select Game & Player")
    
    # Sport selection
    sport = st.selectbox("Sport", ["NBA", "NFL"], index=0)
    
    # Load games
    games = load_games_for_props(sport)
    
    if games:
        # Import format_game_time for proper timezone handling
        from dashboard.ui_components import format_game_time
        game_options = [f"{g['away_team']} @ {g['home_team']} - {format_game_time(g['start_time'])}" for g in games]
        selected_game_idx = st.selectbox("Select Game", range(len(game_options)), format_func=lambda x: game_options[x])
        selected_game = games[selected_game_idx]
    else:
        st.warning("No games available. Fetch odds data first.")
        st.stop()
    
    # Player selection
    st.subheader("Player Selection")
    
    # Get teams for the selected game
    game_teams = [selected_game["home_team"], selected_game["away_team"]]
    
    # Search or select by team
    search_mode = st.radio("Find Player", ["Search", "By Team"], horizontal=True)
    
    selected_player = None
    player_id = None
    
    if search_mode == "Search":
        player_query = st.text_input("Search Player Name (e.g., 'Devin', 'Booker')", 
                                    value="", key="player_search", 
                                    placeholder="Type to search...")
        if player_query:
            all_players = load_all_players_for_search(sport)
            players = fuzzy_search_players(player_query, all_players, limit=10)
            if players:
                st.write(f"**Found {len(players)} players:**")
                # Show dropdown with better formatting
                player_options = [f"{p['name']} ({p.get('position', 'N/A')} - {p.get('team', 'N/A')})" for p in players]
                selected_player_idx = st.selectbox(
                    "Select Player", 
                    range(len(player_options)), 
                    format_func=lambda x: player_options[x], 
                    key="player_select",
                    label_visibility="collapsed"
                )
                selected_player = players[selected_player_idx]
                player_id = selected_player["id"]
            else:
                st.info("No players found. Try a different search term or sync players first.")
        else:
            st.info("💡 Start typing to search (e.g., 'Devin' finds Devin Booker, Devin Vassell, etc.)")
    else:
        # Select by team
        selected_team = st.selectbox("Team", game_teams, key="team_select")
        players = load_players(sport, selected_team)
        if players:
            player_options = [f"{p['name']} ({p.get('position', 'N/A')})" for p in players]
            selected_player_idx = st.selectbox("Select Player", range(len(player_options)), 
                                               format_func=lambda x: player_options[x], key="team_player_select")
            selected_player = players[selected_player_idx]
            player_id = selected_player["id"]
        else:
            st.info(f"No players found for {selected_team}. Sync players first.")
    
    # Use selected player or fallback to mock
    if selected_player:
        player_name = selected_player["name"]
        player_position = selected_player.get("position", "N/A")
        player_team = selected_player.get("team", "N/A")
    else:
        # Fallback to mock data
        player_name = st.text_input("Player Name", value="Josh Hart", key="mock_player_name")
        player_position = st.selectbox("Position", ["PG", "SG", "SF", "PF", "C"], index=1, key="mock_position")
        player_team = st.selectbox("Team", game_teams, key="mock_team")
        player_id = None
    
    # Sync players button
    if st.button("🔄 Sync Players", use_container_width=True):
        st.info("Run: python workers/fetch_player_stats.py --sync-players")

# Main content
# Player Header
col1, col2 = st.columns([1, 5])
with col1:
    # Player avatar (using initials)
    initials = "".join([name[0] for name in player_name.split()[:2]])
    st.markdown(f"""
    <div class="player-avatar">
        {initials}
    </div>
    """, unsafe_allow_html=True)

with col2:
    from dashboard.ui_components import format_game_time
    game_time_formatted = format_game_time(selected_game["start_time"])
    st.markdown(f"""
    <div class="player-header-container">
        <div class="player-info">
            <h2>{player_name}</h2>
            <p>{player_position} | {player_team} ({game_time_formatted})</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Prop Categories - Horizontal buttons matching reference
st.markdown("<br>", unsafe_allow_html=True)
prop_categories = ["Points", "Rebounds", "Assists", "Points Rebounds Assists"]

prop_selected = st.session_state.get("prop_selected", "Points")

# Create button row
button_cols = st.columns(4)
for i, prop in enumerate(prop_categories):
    with button_cols[i]:
        is_active = prop_selected == prop
        if st.button(prop, key=f"prop_{prop}", use_container_width=True, 
                    type="primary" if is_active else "secondary"):
            prop_selected = prop
            st.session_state.prop_selected = prop
            st.rerun()

# Alt Lines and Current Odds
col1, col2, col3 = st.columns([2, 3, 2])
with col1:
    alt_lines = st.selectbox("Alt Lines:", ["9.5", "10.5", "11.5", "12.5"], index=0)
    current_line = float(alt_lines)

with col2:
    # Get odds for the selected prop from database
    st.write("")  # Spacing
    prop_type_map = {
        "Points": "points",
        "Rebounds": "rebounds", 
        "Assists": "assists",
        "Points Rebounds Assists": "pra"
    }
    prop_type = prop_type_map.get(prop_selected, "points")
    
    # Load player prop odds from database
    over_odds = None
    under_odds = None
    
    if player_id and selected_game:
        prop_odds = (
            supabase.table("player_prop_odds")
            .select("*")
            .eq("player_id", player_id)
            .eq("game_id", selected_game["id"])
            .eq("prop_type", prop_type)
            .eq("line", current_line)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
        )
        
        if prop_odds:
            over_odds = prop_odds[0].get("over_price")
            under_odds = prop_odds[0].get("under_price")
    
    # Display odds or placeholder
    if over_odds and under_odds:
        st.write(f"**{prop_selected.upper()} O{current_line}: {format_odds(int(over_odds))} | U{current_line}: {format_odds(int(under_odds))}**")
    else:
        st.write(f"**{prop_selected.upper()} O{current_line}: N/A | U{current_line}: N/A**")
        st.caption("Fetch player prop odds to see live lines")

# Game Lines Table
st.markdown("<br>", unsafe_allow_html=True)
st.subheader("Game Lines")

# Load odds for the selected game
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

# Display game lines
if game_odds:
    # Create a better formatted table
    lines_data = {
        "Team": [selected_game["away_team"], selected_game["home_team"]],
        "Spread": ["", ""],
        "Total": ["", ""],
        "Moneyline": ["", ""]
    }
    
    # Organize odds
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
    st.info("No odds available for this game. Fetch odds data first.")

# Hitrates Section
st.markdown("<br>", unsafe_allow_html=True)
hitrate_tabs = st.tabs(["Hitrates", "Home", "Away"])

# Load player game stats from database
def load_player_game_stats(player_id):
    """Load player game stats from database"""
    if not player_id:
        return []
    
    stats = (
        supabase.table("player_game_stats")
        .select("*")
        .eq("player_id", player_id)
        .order("date", desc=True)
        .limit(30)
        .execute()
        .data
    )
    
    # Convert to format expected by chart
    games = []
    for stat in stats:
        games.append({
            "date": stat.get("date"),
            "opponent": stat.get("opponent", "Unknown"),
            "home": stat.get("home", True),
            "points": stat.get("points", 0),
            "rebounds": stat.get("rebounds", 0),
            "assists": stat.get("assists", 0),
            "minutes_played": stat.get("minutes_played", 0)
        })
    
    return games

# Load real stats or use mock
if player_id:
    player_games = load_player_game_stats(player_id)
    if not player_games:
        st.sidebar.warning(f"No stats found for {player_name}. Fetch stats first.")
        # Use mock data as fallback
        mock_games = [
            {"date": "2024-10-24", "opponent": "DEN", "home": True, "points": 15, "rebounds": 11, "assists": 5},
            {"date": "2024-12-08", "opponent": "BOS", "home": False, "points": 12, "rebounds": 6, "assists": 4},
            {"date": "2024-12-23", "opponent": "DEN", "home": False, "points": 18, "rebounds": 11, "assists": 7},
        ]
        player_games = mock_games
else:
    # Use mock data
    player_games = [
        {"date": "2024-10-24", "opponent": "DEN", "home": True, "points": 15, "rebounds": 11, "assists": 5},
        {"date": "2024-12-08", "opponent": "BOS", "home": False, "points": 12, "rebounds": 6, "assists": 4},
        {"date": "2024-12-23", "opponent": "DEN", "home": False, "points": 18, "rebounds": 11, "assists": 7},
        {"date": "2024-01-05", "opponent": "PHI", "home": True, "points": 14, "rebounds": 8, "assists": 6},
        {"date": "2024-01-12", "opponent": "MIA", "home": False, "points": 16, "rebounds": 9, "assists": 5},
        {"date": "2024-01-18", "opponent": "ATL", "home": True, "points": 13, "rebounds": 7, "assists": 4},
        {"date": "2024-01-20", "opponent": "CHI", "home": True, "points": 17, "rebounds": 10, "assists": 6},
        {"date": "2024-01-22", "opponent": "CLE", "home": False, "points": 11, "rebounds": 5, "assists": 3},
        {"date": "2024-01-25", "opponent": "MIL", "home": True, "points": 19, "rebounds": 12, "assists": 8},
        {"date": "2024-01-28", "opponent": "BKN", "home": False, "points": 15, "rebounds": 9, "assists": 5},
    ]

# Reverse to show most recent first
player_games.reverse()

with hitrate_tabs[0]:  # Hitrates tab
    # Calculate hitrates
    hitrate_data = calculate_hitrate(player_games, prop_type, current_line)
    
    if hitrate_data:
        # Create hitrate table
        periods = ["L3", "L6", "L9", "L12", "L15", "L30"]
        
        hitrate_table_data = {
            "Period": periods,
            "Average": [hitrate_data["averages"].get(p, "N/A") for p in periods],
            "Hitrate (%)": [hitrate_data["hitrates"].get(p, "N/A") for p in periods]
        }
        
        hitrate_df = pd.DataFrame(hitrate_table_data)
        st.dataframe(hitrate_df, use_container_width=True, hide_index=True)
    else:
        st.info("No hitrate data available. Player stats integration needed.")

with hitrate_tabs[1]:  # Home tab
    home_games = [g for g in player_games if g.get("home", True)]
    if home_games:
        home_hitrate = calculate_hitrate(home_games, prop_type, current_line)
        if home_hitrate:
            periods = ["L3", "L6", "L9", "L12", "L15", "L30"]
            home_table_data = {
                "Period": periods,
                "Average": [home_hitrate["averages"].get(p, "N/A") for p in periods],
                "Hitrate (%)": [home_hitrate["hitrates"].get(p, "N/A") for p in periods]
            }
            home_df = pd.DataFrame(home_table_data)
            st.dataframe(home_df, use_container_width=True, hide_index=True)
    else:
        st.info("No home game data available.")

with hitrate_tabs[2]:  # Away tab
    away_games = [g for g in player_games if not g.get("home", True)]
    if away_games:
        away_hitrate = calculate_hitrate(away_games, prop_type, current_line)
        if away_hitrate:
            periods = ["L3", "L6", "L9", "L12", "L15", "L30"]
            away_table_data = {
                "Period": periods,
                "Average": [away_hitrate["averages"].get(p, "N/A") for p in periods],
                "Hitrate (%)": [away_hitrate["hitrates"].get(p, "N/A") for p in periods]
            }
            away_df = pd.DataFrame(away_table_data)
            st.dataframe(away_df, use_container_width=True, hide_index=True)
    else:
        st.info("No away game data available.")

# Statistics Section
st.markdown("<br>", unsafe_allow_html=True)
st.subheader("Statistics")

col1, col2 = st.columns([2, 3])
with col1:
    calculated_minutes = st.metric("Calculated Minutes", "39.93")
    selected_minutes = st.slider("Select Minutes", 0, 48, 35, key="minutes_slider")

# Statistics filter - using tabs for display matching reference
stat_tab_names = ["L3", "L6", "L9", "L10", "L15", "L30", "Home", "Away", "H2H"]
stat_tabs = st.tabs(stat_tab_names)

# Use radio buttons for selection (more reliable than tab detection)
stat_filter = st.radio(
    "Filter by:",
    stat_tab_names,
    horizontal=True,
    index=0,
    key="stat_filter",
    label_visibility="collapsed"
)

# Determine filtered games based on selection
filtered_games = player_games[:3] if len(player_games) >= 3 else player_games  # Default to L3

if stat_filter in ["L3", "L6", "L9", "L10", "L15", "L30"]:
    period_map = {"L3": 3, "L6": 6, "L9": 9, "L10": 10, "L15": 15, "L30": 30}
    period = period_map[stat_filter]
    filtered_games = player_games[:period] if len(player_games) >= period else player_games
elif stat_filter == "Home":
    filtered_games = [g for g in player_games if g.get("home", True)]
elif stat_filter == "Away":
    filtered_games = [g for g in player_games if not g.get("home", True)]
elif stat_filter == "H2H":
    # Filter by opponent (would be the current game's opponent)
    current_opponent = selected_game["away_team"] if player_team == selected_game["home_team"] else selected_game["home_team"]
    # For demo, use first 3 letters of opponent name
    opp_short = current_opponent[:3].upper() if len(current_opponent) >= 3 else current_opponent.upper()
    filtered_games = [g for g in player_games if g.get("opponent") == opp_short]

# Show active tab content
tab_idx = stat_tab_names.index(stat_filter)
with stat_tabs[tab_idx]:
    st.write(f"📊 Filtering by: **{stat_filter}** ({len(filtered_games)} games)")

# Player Prop Chart
st.markdown("<br>", unsafe_allow_html=True)
st.subheader("Player Prop Chart")

# Create chart with filtered games
chart_fig = create_prop_chart(
    filtered_games,
    prop_type,
    current_line,
    title=f"{prop_selected} Prop Chart"
)

st.plotly_chart(chart_fig, use_container_width=True)

# Footer
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Player stats integration pending")

