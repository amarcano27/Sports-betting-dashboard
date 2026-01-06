"""
Enhanced Home Page with Prop Marketplace Feed - Redesigned
Fixes duplicates, improves UI, adds all requested features
"""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from rapidfuzz import process
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from utils.ev import american_to_prob, ev
from dashboard.player_props import format_odds, calculate_hitrate
from dashboard.ui_components import (
    create_sparkline, create_enhanced_prop_card, 
    export_slip_to_json, export_slip_to_text
)

# Page config is handled by main.py when using st.navigation()

# Enhanced CSS with modern design - NO DUPLICATES
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #0e1117 0%, #1a1d29 100%);
    }
    .enhanced-prop-card {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 2px solid #475569;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
        position: relative;
        overflow: hidden;
    }
    .enhanced-prop-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
    .enhanced-prop-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6);
        border-color: #64748b;
    }
    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 1rem;
    }
    .player-header {
        flex: 1;
    }
    .player-name-large {
        font-size: 1.5rem;
        font-weight: 700;
        color: #f8fafc;
        margin-bottom: 0.25rem;
        line-height: 1.2;
    }
    .player-meta {
        color: #94a3b8;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .card-badges {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        justify-content: flex-end;
    }
    .degen-badge {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        box-shadow: 0 2px 4px rgba(245, 158, 11, 0.3);
    }
    .edge-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .edge-badge.edge-positive {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
    }
    .edge-badge.edge-negative {
        background: #374151;
        color: #9ca3af;
    }
    .game-info {
        color: #cbd5e1;
        font-size: 0.9rem;
        margin-bottom: 1rem;
        padding: 0.5rem;
        background: rgba(71, 85, 105, 0.3);
        border-radius: 8px;
        text-align: center;
        font-weight: 500;
    }
    .prop-main {
        margin: 1rem 0;
    }
    .prop-type-line {
        display: flex;
        align-items: baseline;
        gap: 0.5rem;
        margin-bottom: 1rem;
    }
    .prop-type {
        font-size: 1.1rem;
        font-weight: 600;
        color: #f8fafc;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .prop-line {
        font-size: 1.5rem;
        font-weight: 700;
        color: #667eea;
    }
    .odds-container {
        display: flex;
        align-items: center;
        justify-content: space-around;
        gap: 1rem;
        padding: 1rem;
        background: rgba(15, 23, 42, 0.5);
        border-radius: 12px;
        margin: 1rem 0;
    }
    .odds-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.25rem;
    }
    .odds-label {
        font-size: 0.75rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .odds-value {
        font-size: 1.25rem;
        font-weight: 700;
    }
    .odds-positive {
        color: #10b981;
    }
    .odds-negative {
        color: #ef4444;
    }
    .odds-divider {
        color: #475569;
        font-size: 1.5rem;
    }
    .book-info {
        color: #64748b;
        font-size: 0.85rem;
        text-align: center;
        margin-top: 0.5rem;
    }
    .matchup-info {
        margin-top: 0.75rem;
        padding: 0.5rem;
        background: rgba(59, 130, 246, 0.1);
        border-left: 3px solid #3b82f6;
        border-radius: 4px;
        color: #93c5fd;
        font-size: 0.85rem;
    }
    .sparkline-container {
        margin-top: 0.75rem;
        padding-top: 0.75rem;
        border-top: 1px solid #475569;
    }
    .trending-badge {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.65rem;
        font-weight: 600;
        margin-left: 0.5rem;
    }
    .slip-leg-enhanced {
        background: linear-gradient(135deg, #334155 0%, #475569 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.75rem 0;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    }
    .empty-state {
        text-align: center;
        padding: 3rem 2rem;
        color: #94a3b8;
    }
    .empty-state-icon {
        font-size: 4rem;
        margin-bottom: 1rem;
    }
    .loading-spinner {
        display: inline-block;
        width: 20px;
        height: 20px;
        border: 3px solid rgba(102, 126, 234, 0.3);
        border-radius: 50%;
        border-top-color: #667eea;
        animation: spin 1s ease-in-out infinite;
    }
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }
    .stat-box {
        background: rgba(30, 41, 59, 0.5);
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #475569;
    }
    .stat-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #f8fafc;
        margin-bottom: 0.25rem;
    }
    .stat-label {
        font-size: 0.75rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "slip_legs" not in st.session_state:
    st.session_state.slip_legs = []
if "degen_mode" not in st.session_state:
    st.session_state.degen_mode = False
if "trending_props" not in st.session_state:
    st.session_state.trending_props = {}

# Helper functions with caching
@st.cache_data(ttl=3600)
def load_all_players(sport):
    """Load all players for search"""
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
def load_tonight_games(sport):
    """Load games starting within 24 hours"""
    now = datetime.now()
    tomorrow = now + timedelta(hours=24)
    games = (
        supabase.table("games")
        .select("*")
        .eq("sport", sport)
        .gte("start_time", now.isoformat())
        .lte("start_time", tomorrow.isoformat())
        .order("start_time")
        .execute()
        .data
    )
    return games

@st.cache_data(ttl=300)
def load_player_props_for_feed(sport, game_ids=None):
    """Load player props for the feed - FIXED TO PREVENT DUPLICATES"""
    try:
        query = (
            supabase.table("player_prop_odds")
            .select("*, players(*), games(*)")
        )
        
        if game_ids:
            query = query.in_("game_id", game_ids)
        
        props = query.order("created_at", desc=True).execute().data
        
        # FIX: Get latest props per player/game/prop_type/line/book to prevent duplicates
        latest_props = {}
        for prop in props:
            # Create unique key: player + game + prop_type + line + book
            key = (
                prop.get("player_id"),
                prop.get("game_id"),
                prop.get("prop_type"),
                prop.get("line"),
                prop.get("book")
            )
            # Only keep the most recent one
            if key not in latest_props:
                latest_props[key] = prop
            elif prop.get("created_at", "") > latest_props[key].get("created_at", ""):
                latest_props[key] = prop
        
        return list(latest_props.values())
    except Exception as e:
        st.error(f"Error loading props: {e}")
        return []

@st.cache_data(ttl=300)
def load_player_stats_for_edge(player_id, prop_type):
    """Load player stats to calculate edge"""
    stats = (
        supabase.table("player_game_stats")
        .select("*")
        .eq("player_id", player_id)
        .order("date", desc=True)
        .limit(15)
        .execute()
        .data
    )
    return stats

@st.cache_data(ttl=300)
def load_matchup_stats(player_id, opponent_team, prop_type):
    """Load player stats vs specific opponent"""
    stats = (
        supabase.table("player_game_stats")
        .select("*")
        .eq("player_id", player_id)
        .eq("opponent", opponent_team)
        .order("date", desc=True)
        .limit(10)
        .execute()
        .data
    )
    
    if not stats:
        return None
    
    # Calculate average
    prop_values = []
    for stat in stats:
        value = None
        if prop_type == "points":
            value = stat.get("points", 0)
        elif prop_type == "rebounds":
            value = stat.get("rebounds", 0)
        elif prop_type == "assists":
            value = stat.get("assists", 0)
        elif prop_type == "pra":
            value = (
                stat.get("points", 0) +
                stat.get("rebounds", 0) +
                stat.get("assists", 0)
            )
        if value is not None:
            prop_values.append(value)
    
    if prop_values:
        return {
            "avg_vs_opponent": sum(prop_values) / len(prop_values),
            "games": len(prop_values)
        }
    return None

def calculate_prop_edge(prop, stats):
    """Calculate expected value/edge for a prop"""
    if not stats:
        return None
    
    prop_type = prop.get("prop_type")
    line = prop.get("line")
    
    # Get prop values from stats
    prop_values = []
    for stat in stats:
        value = None
        if prop_type == "points":
            value = stat.get("points", 0)
        elif prop_type == "rebounds":
            value = stat.get("rebounds", 0)
        elif prop_type == "assists":
            value = stat.get("assists", 0)
        elif prop_type == "pra":
            value = (
                stat.get("points", 0) +
                stat.get("rebounds", 0) +
                stat.get("assists", 0)
            )
        
        if value is not None:
            prop_values.append(value)
    
    if not prop_values:
        return None
    
    # Calculate true probability
    hits = sum(1 for v in prop_values if v > line)
    true_prob = hits / len(prop_values) if prop_values else 0.5
    
    # Get best odds (over or under)
    over_price = prop.get("over_price")
    under_price = prop.get("under_price")
    
    if not over_price and not under_price:
        return None
    
    # Calculate EV for over
    if over_price:
        over_ev = ev(true_prob, int(over_price))
    else:
        over_ev = None
    
    # Calculate EV for under
    if under_price:
        under_ev = ev(1 - true_prob, int(under_price))
    else:
        under_ev = None
    
    # Return best edge
    if over_ev is not None and under_ev is not None:
        if over_ev > under_ev:
            return {"edge": over_ev, "side": "over", "odds": over_price, "prob": true_prob}
        else:
            return {"edge": under_ev, "side": "under", "odds": under_price, "prob": 1 - true_prob}
    elif over_ev is not None:
        return {"edge": over_ev, "side": "over", "odds": over_price, "prob": true_prob}
    elif under_ev is not None:
        return {"edge": under_ev, "side": "under", "odds": under_price, "prob": 1 - true_prob}
    
    return None

def get_sparkline_data(player_id, prop_type):
    """Get last 10 games data for sparkline"""
    stats = load_player_stats_for_edge(player_id, prop_type)
    if not stats or len(stats) < 2:
        return None
    
    # Get last 10 games
    recent_stats = stats[:10]
    values = []
    for stat in reversed(recent_stats):  # Reverse to show chronological order
        value = None
        if prop_type == "points":
            value = stat.get("points", 0)
        elif prop_type == "rebounds":
            value = stat.get("rebounds", 0)
        elif prop_type == "assists":
            value = stat.get("assists", 0)
        elif prop_type == "pra":
            value = (
                stat.get("points", 0) +
                stat.get("rebounds", 0) +
                stat.get("assists", 0)
            )
        if value is not None:
            values.append(float(value))
    
    return values if len(values) >= 2 else None

def is_degen_play(edge_data, odds):
    """Determine if a play qualifies as DEGEN"""
    if not edge_data:
        return False
    
    edge = edge_data.get("edge", 0)
    prob = edge_data.get("prob", 0.5)
    
    if edge > 0 and 0.30 <= prob <= 0.50:
        if odds and odds > -400:
            return True
    
    return False

# Sidebar filters
with st.sidebar:
    st.header("🎯 Filters")
    
    sport = st.selectbox("Sport", ["NBA", "NFL"], index=0)
    
    st.divider()
    
    # Prop type filter
    st.subheader("Prop Types")
    prop_types = ["All", "Points", "Rebounds", "Assists", "PRA", "3PM"]
    selected_prop_types = st.multiselect(
        "Select Prop Types",
        prop_types,
        default=["All"] if "All" in prop_types else []
    )
    
    if "All" in selected_prop_types:
        selected_prop_types = prop_types[1:]
    
    st.divider()
    
    # DEGEN mode toggle
    st.subheader("🔥 DEGEN Mode")
    degen_mode = st.checkbox(
        "Show Only DEGEN Plays",
        value=st.session_state.degen_mode,
        help="Higher risk, higher reward plays (30-50% hit rate, positive edge)"
    )
    st.session_state.degen_mode = degen_mode
    
    st.divider()
    
    # +EV only filter
    show_ev_only = st.checkbox("Only +EV Props", value=False)
    
    st.divider()
    
    # Team filter
    st.subheader("Team Filter")
    all_teams = st.checkbox("All Teams", value=True)
    if not all_teams:
        players = load_all_players(sport)
        teams = sorted(set(p.get("team") for p in players if p.get("team")))
        selected_teams = st.multiselect("Select Teams", teams)
    else:
        selected_teams = None
    
    st.divider()
    
    # Sort options
    st.subheader("Sort By")
    sort_by = st.selectbox(
        "Sort Options",
        ["Edge (Highest)", "Odds (Best)", "Line (Lowest)", "Player Name"],
        index=0
    )

# Title
st.title("🏀 Tonight's Props Marketplace")

# Load data with loading state
with st.spinner("Loading games and props..."):
    games = load_tonight_games(sport)
    game_ids = [g["id"] for g in games] if games else []

if not games:
    st.markdown("""
    <div class="empty-state">
        <div class="empty-state-icon">📅</div>
        <h3>No Games Scheduled</h3>
        <p>No games found for tonight. Try adjusting the date range or fetch new odds data.</p>
        <p style="margin-top: 1rem;">
            <code>python workers/fetch_odds.py</code>
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Load props with loading state
with st.spinner("Loading player props..."):
    props = load_player_props_for_feed(sport, game_ids)

if not props:
    st.markdown("""
    <div class="empty-state">
        <div class="empty-state-icon">📊</div>
        <h3>No Player Props Available</h3>
        <p>Fetch player prop odds to see available props.</p>
        <p style="margin-top: 1rem;">
            <code>python workers/fetch_player_prop_odds.py</code>
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Track trending props (props added to slips)
trending_counts = {}
for leg in st.session_state.slip_legs:
    prop_key = f"{leg.get('player_name')}_{leg.get('prop_type')}_{leg.get('line')}"
    trending_counts[prop_key] = trending_counts.get(prop_key, 0) + 1

# Filter and process props - FIXED TO PREVENT DUPLICATES
filtered_props = []
seen_prop_keys = set()  # Track to prevent duplicates

for prop in props:
    # Create unique key to prevent duplicates
    prop_key = (
        prop.get("player_id"),
        prop.get("game_id"),
        prop.get("prop_type"),
        prop.get("line"),
        prop.get("book")
    )
    
    if prop_key in seen_prop_keys:
        continue  # Skip duplicates
    seen_prop_keys.add(prop_key)
    
    # Prop type filter
    prop_type = prop.get("prop_type", "").replace("_", " ").title()
    if selected_prop_types and prop_type not in selected_prop_types:
        continue
    
    # Team filter
    player_info = prop.get("players", {})
    if isinstance(player_info, dict):
        player_team = player_info.get("team")
        if selected_teams and player_team not in selected_teams:
            continue
    
    # Calculate edge
    player_id = prop.get("player_id")
    edge_data = None
    sparkline_data = None
    matchup_stats = None
    
    if player_id:
        stats = load_player_stats_for_edge(player_id, prop.get("prop_type"))
        edge_data = calculate_prop_edge(prop, stats)
        sparkline_data = get_sparkline_data(player_id, prop.get("prop_type"))
        
        # Get matchup stats
        game_info = prop.get("games", {})
        if isinstance(game_info, dict):
            opponent = game_info.get("away_team") if player_team == game_info.get("home_team") else game_info.get("home_team")
            if opponent:
                matchup_stats = load_matchup_stats(player_id, opponent, prop.get("prop_type"))
    
    # +EV filter
    if show_ev_only:
        if not edge_data or edge_data.get("edge", 0) <= 0:
            continue
    
    # DEGEN filter
    if degen_mode:
        best_odds = prop.get("over_price") or prop.get("under_price")
        if not is_degen_play(edge_data, best_odds):
            continue
    
    filtered_props.append((prop, edge_data, sparkline_data, matchup_stats))

# Sort props
if sort_by == "Edge (Highest)":
    filtered_props.sort(key=lambda x: x[1].get("edge", -999) if x[1] else -999, reverse=True)
elif sort_by == "Odds (Best)":
    filtered_props.sort(key=lambda x: x[0].get("over_price") or x[0].get("under_price") or 999, reverse=True)
elif sort_by == "Line (Lowest)":
    filtered_props.sort(key=lambda x: x[0].get("line", 999))
elif sort_by == "Player Name":
    filtered_props.sort(key=lambda x: x[0].get("players", {}).get("name", "") if isinstance(x[0].get("players"), dict) else "")

# Display stats
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Props", len(filtered_props))
with col2:
    positive_ev = sum(1 for _, edge, _, _ in filtered_props if edge and edge.get("edge", 0) > 0)
    st.metric("+EV Props", positive_ev)
with col3:
    degen_count = sum(1 for _, edge, _, _ in filtered_props if edge and is_degen_play(edge, None))
    st.metric("DEGEN Plays", degen_count)
with col4:
    st.metric("Games Tonight", len(games))

# Trending section
if trending_counts:
    st.subheader("🔥 Trending Props")
    trending_list = sorted(trending_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    trending_text = ", ".join([f"{k.split('_')[0]} ({v})" for k, v in trending_list])
    st.caption(trending_text)

# Display props in grid - NO DUPLICATES
if filtered_props:
    st.write(f"**Showing {len(filtered_props)} props**")
    
    # Create columns for grid layout
    num_cols = 3
    cols = st.columns(num_cols)
    
    for idx, (prop, edge_data, sparkline_data, matchup_stats) in enumerate(filtered_props):
        with cols[idx % num_cols]:
            player_info = prop.get("players", {})
            game_info = prop.get("games", {})
            
            if isinstance(player_info, dict) and isinstance(game_info, dict):
                # Check if trending
                prop_key = f"{player_info.get('name')}_{prop.get('prop_type')}_{prop.get('line')}"
                is_trending = prop_key in trending_counts and trending_counts[prop_key] >= 3
                
                card_html = create_enhanced_prop_card(
                    prop, player_info, game_info, edge_data, 
                    sparkline_data, matchup_stats
                )
                st.markdown(card_html, unsafe_allow_html=True)
                
                # Add sparkline if available
                if sparkline_data:
                    fig = create_sparkline(sparkline_data, prop.get("line"))
                    if fig:
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                
                # Add to slip button
                side = edge_data.get("side", "over") if edge_data else "over"
                button_text = f"➕ Add {side.upper()}"
                if st.button(button_text, key=f"add_{prop.get('id')}_{side}_{idx}", use_container_width=True):
                    leg = {
                        "prop_id": prop.get("id"),
                        "player_name": player_info.get("name", "Unknown"),
                        "prop_type": prop.get("prop_type", ""),
                        "line": prop.get("line"),
                        "side": side,
                        "odds": edge_data.get("odds") if edge_data else (prop.get("over_price") or prop.get("under_price")),
                        "book": prop.get("book", "Unknown"),
                        "edge": edge_data.get("edge") if edge_data else None
                    }
                    # Check if leg already exists
                    leg_exists = any(
                        l.get("prop_id") == leg["prop_id"] and l.get("side") == leg["side"]
                        for l in st.session_state.slip_legs
                    )
                    if not leg_exists:
                        st.session_state.slip_legs.append(leg)
                        st.success("Added!")
                        st.rerun()
else:
    st.markdown("""
    <div class="empty-state">
        <div class="empty-state-icon">🔍</div>
        <h3>No Props Match Your Filters</h3>
        <p>Try adjusting your filters to see more props.</p>
    </div>
    """, unsafe_allow_html=True)

# Enhanced Slip sidebar
with st.sidebar:
    if st.session_state.slip_legs:
        st.divider()
        st.subheader("🎫 Your Slip")
        
        total_odds = 1.0
        total_ev = 0.0
        
        for i, leg in enumerate(st.session_state.slip_legs):
            with st.container():
                st.markdown(f"""
                <div class="slip-leg-enhanced">
                    <strong>{leg.get('player_name', 'Unknown')}</strong><br>
                    {leg.get('prop_type', '').replace('_', ' ').title()} {leg.get('line', '')} {leg.get('side', '').upper()}<br>
                    Odds: {format_odds(int(leg.get('odds', 0)))} | {leg.get('book', 'Unknown')}
                    {f'<br><small style="color: #10b981;">Edge: {leg.get("edge")*100:.1f}%</small>' if leg.get('edge') else ''}
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("❌ Remove", key=f"remove_{i}", use_container_width=True):
                    st.session_state.slip_legs.pop(i)
                    st.rerun()
                
                # Calculate combined odds
                odds_val = leg.get("odds")
                if odds_val:
                    try:
                        if odds_val > 0:
                            decimal = odds_val / 100 + 1
                        else:
                            decimal = 100 / abs(odds_val) + 1
                        total_odds *= decimal
                    except:
                        pass
                
                if leg.get("edge"):
                    total_ev += leg["edge"]
        
        if st.session_state.slip_legs:
            st.divider()
            
            # Calculate parlay odds
            if total_odds > 1:
                american_odds = (total_odds - 1) * 100
                if american_odds > 100:
                    american_odds = int(american_odds)
                else:
                    american_odds = int(-100 / (american_odds / 100))
                
                st.metric("Combined Odds", f"{american_odds:+d}")
                st.metric("Decimal Odds", f"{total_odds:.2f}")
                if total_ev != 0:
                    st.metric("Combined EV", f"{total_ev*100:.1f}%")
                
                # Payout calculator
                bet_amount = st.number_input("Bet Amount ($)", min_value=1, value=100, step=10, key="bet_amount")
                payout = bet_amount * total_odds
                profit = payout - bet_amount
                st.metric("Total Payout", f"${payout:,.2f}")
                st.metric("Profit", f"${profit:,.2f}")
            
            # Export functionality
            st.divider()
            st.subheader("📥 Export Slip")
            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                if st.button("📄 JSON", use_container_width=True):
                    json_data = export_slip_to_json(st.session_state.slip_legs)
                    st.download_button(
                        "Download JSON",
                        json_data,
                        "betting_slip.json",
                        "application/json",
                        key="download_json"
                    )
            with col_exp2:
                if st.button("📝 Text", use_container_width=True):
                    text_data = export_slip_to_text(st.session_state.slip_legs)
                    st.download_button(
                        "Download Text",
                        text_data,
                        "betting_slip.txt",
                        "text/plain",
                        key="download_text"
                    )
            
            if st.button("🗑️ Clear Slip", use_container_width=True):
                st.session_state.slip_legs = []
                st.rerun()

