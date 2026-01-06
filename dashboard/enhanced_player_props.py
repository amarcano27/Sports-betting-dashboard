"""
Enhanced Player Props Dashboard with all requested features
"""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from rapidfuzz import process, fuzz
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from dashboard.player_props import (
    calculate_hitrate, 
    create_prop_chart
)
from utils.ev import american_to_prob, ev

def format_odds(odds: int) -> str:
    """Format American odds for display"""
    if odds is None:
        return "N/A"
    return f"{odds:+d}"

# Page config
st.set_page_config(
    page_title="Player Props Marketplace",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS with gradients and modern design
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #0e1117 0%, #1a1d29 100%);
    }
    .stApp {
        background: transparent;
        color: #fafafa;
    }
    .prop-card {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        border: 1px solid #475569;
        border-radius: 12px;
        padding: 1.25rem;
        margin: 0.75rem 0;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    .prop-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 12px rgba(0, 0, 0, 0.4);
        border-color: #10b981;
    }
    .player-name {
        font-size: 1.25rem;
        font-weight: 700;
        color: #fafafa;
        margin: 0;
    }
    .prop-info {
        color: #94a3b8;
        font-size: 0.9rem;
        margin: 0.5rem 0;
    }
    .odds-positive {
        color: #10b981;
        font-weight: 600;
    }
    .odds-negative {
        color: #ef4444;
        font-weight: 600;
    }
    .edge-badge {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
    }
    .add-button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.5rem 1.5rem;
        border-radius: 8px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s;
        width: 100%;
    }
    .add-button:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    .slip-sidebar {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-left: 2px solid #475569;
        padding: 1rem;
        position: sticky;
        top: 0;
        max-height: 100vh;
        overflow-y: auto;
    }
    .slip-leg {
        background: #334155;
        border-radius: 8px;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-left: 3px solid #667eea;
    }
    .search-suggestion {
        padding: 0.5rem;
        cursor: pointer;
        border-radius: 4px;
        transition: background 0.2s;
    }
    .search-suggestion:hover {
        background: #334155;
    }
    .filter-chip {
        background: #334155;
        border: 1px solid #475569;
        color: #fafafa;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.85rem;
        cursor: pointer;
        transition: all 0.2s;
    }
    .filter-chip.active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-color: #667eea;
    }
    .sparkline-container {
        height: 40px;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "parlay_legs" not in st.session_state:
    st.session_state.parlay_legs = []
if "selected_filters" not in st.session_state:
    st.session_state.selected_filters = {
        "prop_type": "All",
        "over_under": "All",
        "team": "All",
        "only_ev": False
    }

# Helper functions
@st.cache_data(ttl=3600)
def load_all_players(sport="NBA"):
    """Load all players with caching"""
    players = (
        supabase.table("players")
        .select("*")
        .eq("sport", sport)
        .order("name")
        .execute()
        .data
    )
    return players

@st.cache_data(ttl=300)
def load_games_for_props(sport, hours_ahead=24):
    """Load games within specified hours"""
    cutoff = (datetime.now() + timedelta(hours=hours_ahead)).isoformat()
    games = (
        supabase.table("games")
        .select("*")
        .eq("sport", sport)
        .gte("start_time", datetime.now().isoformat())
        .lte("start_time", cutoff)
        .order("start_time")
        .execute()
        .data
    )
    return games

@st.cache_data(ttl=300)
def load_player_prop_odds(game_ids=None, player_ids=None):
    """Load player prop odds"""
    query = supabase.table("player_prop_odds").select("*")
    
    if game_ids:
        query = query.in_("game_id", game_ids)
    if player_ids:
        query = query.in_("player_id", player_ids)
    
    odds = query.order("created_at", desc=True).execute().data
    return odds

def fuzzy_search_players(query, players, limit=10):
    """Fuzzy search for players"""
    if not query or len(query) < 2:
        return []
    
    player_names = [f"{p['name']} ({p.get('position', 'N/A')} - {p.get('team', 'N/A')})" for p in players]
    matches = process.extract(query, player_names, limit=limit, score_cutoff=50)
    
    # Get full player objects
    results = []
    for match_name, score, _ in matches:
        # Extract player name from match string
        player_name = match_name.split(" (")[0]
        player = next((p for p in players if p['name'] == player_name), None)
        if player:
            results.append(player)
    
    return results

def calculate_prop_edge(price, true_prob):
    """Calculate edge for a prop"""
    if not price:
        return None
    implied_prob = american_to_prob(price)
    if true_prob and implied_prob:
        edge = ((true_prob - implied_prob) / implied_prob) * 100
        return edge
    return None

def create_sparkline(data, color="#10b981"):
    """Create a mini sparkline chart"""
    if not data or len(data) < 2:
        return None
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=data,
        mode='lines',
        line=dict(color=color, width=2),
        showlegend=False,
        hoverinfo='skip'
    ))
    fig.update_layout(
        height=40,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        template='plotly_dark'
    )
    return fig

# Main layout
st.title("🎯 Player Props Marketplace")

# Sidebar filters
with st.sidebar:
    st.header("🔍 Filters")
    
    # Prop type filter
    prop_types = ["All", "Points", "Rebounds", "Assists", "3PM", "PRA"]
    selected_prop = st.selectbox("Prop Type", prop_types, index=0)
    st.session_state.selected_filters["prop_type"] = selected_prop
    
    # Over/Under filter
    over_under = st.selectbox("Over/Under", ["All", "Over", "Under"], index=0)
    st.session_state.selected_filters["over_under"] = over_under
    
    # Team filter
    sport = st.selectbox("Sport", ["NBA", "NFL"], index=0)
    games = load_games_for_props(sport, hours_ahead=24)
    teams = set()
    for game in games:
        teams.add(game.get("home_team", ""))
        teams.add(game.get("away_team", ""))
    teams = sorted(list(teams))
    selected_team = st.selectbox("Team", ["All"] + teams, index=0)
    st.session_state.selected_filters["team"] = selected_team
    
    # +EV only toggle
    only_ev = st.checkbox("🔥 Only +EV Props", value=False)
    st.session_state.selected_filters["only_ev"] = only_ev
    
    st.divider()
    
    # Slip builder
    st.header("📝 Your Slip")
    
    if st.session_state.parlay_legs:
        total_odds = 1.0
        for i, leg in enumerate(st.session_state.parlay_legs):
            with st.container():
                st.markdown(f"""
                <div class="slip-leg">
                    <strong>{leg.get('player_name', 'Unknown')}</strong><br>
                    <small>{leg.get('prop_type', 'N/A')} {leg.get('line', 'N/A')}</small><br>
                    <small>Odds: {format_odds(leg.get('price', 0))}</small>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("❌", key=f"remove_{i}", use_container_width=True):
                    st.session_state.parlay_legs.pop(i)
                    st.rerun()
            
            # Calculate combined odds
            price = leg.get("price", 0)
            if price:
                if price > 0:
                    decimal = price / 100 + 1
                else:
                    decimal = 100 / abs(price) + 1
                total_odds *= decimal
        
        if total_odds > 1:
            if total_odds > 2:
                american_odds = int((total_odds - 1) * 100)
            else:
                american_odds = int(-100 / (total_odds / 100))
            
            st.metric("Combined Odds", f"{american_odds:+d}")
            st.metric("Implied Prob", f"{(1/total_odds)*100:.1f}%")
            
            bet_amount = st.number_input("Bet Amount ($)", min_value=1, value=100, step=10)
            payout = bet_amount * total_odds
            st.metric("Payout", f"${payout:,.2f}")
        
        if st.button("🗑️ Clear Slip", use_container_width=True):
            st.session_state.parlay_legs = []
            st.rerun()
        
        if st.button("🤖 Generate AI Slip", use_container_width=True, type="primary"):
            st.info("AI slip generation coming soon!")
    else:
        st.info("Add props to build your slip")

# Main content area
tab1, tab2, tab3 = st.tabs(["🏠 Tonight's Props", "🔍 Player Search", "📊 Player Analysis"])

with tab1:
    st.subheader("🔥 Tonight's Best Props")
    
    # Load props
    game_ids = [g["id"] for g in games] if games else []
    all_props = load_player_prop_odds(game_ids=game_ids) if game_ids else []
    
    # Get player info for props
    if all_props:
        player_ids = list(set([p["player_id"] for p in all_props]))
        players_dict = {p["id"]: p for p in load_all_players(sport) if p["id"] in player_ids}
        
        # Build prop cards
        prop_cards = []
        for prop in all_props:
            player = players_dict.get(prop["player_id"])
            if not player:
                continue
            
            # Apply filters
            if selected_prop != "All" and prop.get("prop_type") != selected_prop.lower():
                continue
            if selected_team != "All" and player.get("team") != selected_team:
                continue
            
            # Get game info
            game = next((g for g in games if g["id"] == prop["game_id"]), None)
            
            prop_cards.append({
                "player_id": prop["player_id"],
                "player_name": player["name"],
                "team": player.get("team", "N/A"),
                "position": player.get("position", "N/A"),
                "prop_type": prop.get("prop_type", "N/A"),
                "line": prop.get("line"),
                "over_price": prop.get("over_price"),
                "under_price": prop.get("under_price"),
                "book": prop.get("book", "N/A"),
                "game": game
            })
        
        # Display in grid
        cols_per_row = 3
        for i in range(0, len(prop_cards), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, prop in enumerate(prop_cards[i:i+cols_per_row]):
                with cols[j]:
                    with st.container():
                        st.markdown(f"""
                        <div class="prop-card">
                            <p class="player-name">{prop['player_name']}</p>
                            <p class="prop-info">{prop['team']} | {prop['position']}</p>
                            <hr style="border-color: #475569; margin: 0.5rem 0;">
                            <p><strong>{prop['prop_type'].upper()}</strong> {prop['line']}</p>
                            <p>O: <span class="odds-positive">{format_odds(int(prop['over_price'])) if prop['over_price'] else 'N/A'}</span> | 
                               U: <span class="odds-negative">{format_odds(int(prop['under_price'])) if prop['under_price'] else 'N/A'}</span></p>
                            <p><small>{prop['book']}</small></p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Add to slip button
                        if st.button("➕ Add Over", key=f"add_over_{prop['player_id']}_{i}_{j}", use_container_width=True):
                            leg = {
                                "player_id": prop["player_id"],
                                "player_name": prop["player_name"],
                                "prop_type": prop["prop_type"],
                                "line": prop["line"],
                                "price": prop["over_price"],
                                "book": prop["book"],
                                "side": "Over"
                            }
                            st.session_state.parlay_legs.append(leg)
                            st.success("Added!")
                            st.rerun()
    else:
        st.info("No props available. Fetch player prop odds or use mock data for testing.")
        
        # Show mock props for UX testing
        st.subheader("📋 Mock Props (for UX testing)")
        mock_props = [
            {"player": "Luka Doncic", "team": "DAL", "prop": "Points", "line": 31.5, "over": -105, "under": -115, "book": "FanDuel", "edge": 6},
            {"player": "Jayson Tatum", "team": "BOS", "prop": "Rebounds", "line": 9.5, "over": 120, "under": -150, "book": "DraftKings", "edge": 4},
            {"player": "Stephen Curry", "team": "GSW", "prop": "3PM", "line": 4.5, "over": -110, "under": -110, "book": "BetMGM", "edge": 2},
        ]
        
        cols = st.columns(3)
        for i, prop in enumerate(mock_props):
            with cols[i]:
                st.markdown(f"""
                <div class="prop-card">
                    <p class="player-name">{prop['player']}</p>
                    <p class="prop-info">{prop['team']}</p>
                    <hr style="border-color: #475569; margin: 0.5rem 0;">
                    <p><strong>{prop['prop']}</strong> {prop['line']}</p>
                    <p>O: <span class="odds-positive">{format_odds(prop['over'])}</span> | 
                       U: <span class="odds-negative">{format_odds(prop['under'])}</span></p>
                    <p><small>{prop['book']}</small></p>
                    <span class="edge-badge">+{prop['edge']}% edge</span>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("➕ Add Over", key=f"mock_over_{i}", use_container_width=True):
                    st.info("Mock prop - real props will be available when odds are fetched")

with tab2:
    st.subheader("🔍 Player Search")
    
    # Fuzzy search input
    search_query = st.text_input("Search player name (e.g., 'Devin', 'Booker')", key="player_search", placeholder="Type to search...")
    
    all_players = load_all_players(sport)
    
    if search_query:
        matches = fuzzy_search_players(search_query, all_players, limit=10)
        
        if matches:
            st.write(f"Found {len(matches)} players:")
            
            for player in matches:
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.write(f"**{player['name']}**")
                with col2:
                    st.write(f"{player.get('position', 'N/A')} | {player.get('team', 'N/A')}")
                with col3:
                    if st.button("View", key=f"view_{player['id']}"):
                        st.session_state.selected_player = player
                        st.switch_page("dashboard/player_props_page.py")
        else:
            st.info("No players found. Try a different search term.")
    else:
        st.info("Start typing to search for players...")

with tab3:
    st.subheader("📊 Player Analysis")
    st.info("Select a player from search to view detailed analysis")

# Footer
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {len(all_players) if 'all_players' in locals() else 0} players in database")

