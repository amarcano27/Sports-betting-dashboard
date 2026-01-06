"""
Enhanced Home Page with Prop Marketplace Feed
"""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from rapidfuzz import process

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from utils.ev import american_to_prob, ev
from dashboard.player_props import format_odds, calculate_hitrate

# Page config is handled by main.py when using st.navigation()
# Removed to avoid conflicts

# Enhanced CSS with modern design
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #0e1117 0%, #1a1d29 100%);
    }
    .prop-card {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        border-radius: 12px;
        padding: 1.25rem;
        margin: 0.75rem 0;
        border: 1px solid #475569;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    .prop-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.4);
        border-color: #64748b;
    }
    .player-name {
        font-size: 1.25rem;
        font-weight: 700;
        color: #f8fafc;
        margin-bottom: 0.5rem;
    }
    .prop-info {
        color: #cbd5e1;
        font-size: 0.9rem;
        margin: 0.25rem 0;
    }
    .odds-display {
        font-size: 1.1rem;
        font-weight: 600;
        color: #10b981;
    }
    .edge-positive {
        color: #10b981;
        font-weight: 600;
    }
    .edge-negative {
        color: #ef4444;
    }
    .degen-badge {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
        margin-left: 0.5rem;
    }
    .filter-chip {
        background: #334155;
        color: #cbd5e1;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        border: 1px solid #475569;
        cursor: pointer;
        transition: all 0.2s;
    }
    .filter-chip.active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-color: #667eea;
    }
    .slip-sidebar {
        position: fixed;
        right: 0;
        top: 0;
        width: 350px;
        height: 100vh;
        background: #1e293b;
        border-left: 2px solid #475569;
        padding: 1rem;
        overflow-y: auto;
        z-index: 1000;
    }
    .slip-leg {
        background: #334155;
        padding: 0.75rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 3px solid #667eea;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        transform: scale(1.02);
    }
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #475569;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "slip_legs" not in st.session_state:
    st.session_state.slip_legs = []
if "degen_mode" not in st.session_state:
    st.session_state.degen_mode = False

# Helper functions with caching
@st.cache_data(ttl=3600)  # Cache for 1 hour
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

@st.cache_data(ttl=300)  # Cache for 5 minutes
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
    """Load player props for the feed"""
    try:
        query = (
            supabase.table("player_prop_odds")
            .select("*, players(*), games(*)")
        )
        
        if game_ids:
            query = query.in_("game_id", game_ids)
        
        props = query.order("created_at", desc=True).execute().data
        
        # Get latest props per player/game/prop_type/line
        latest_props = {}
        for prop in props:
            key = (
                prop.get("player_id"),
                prop.get("game_id"),
                prop.get("prop_type"),
                prop.get("line")
            )
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

def is_degen_play(edge_data, odds):
    """Determine if a play qualifies as DEGEN (higher risk, higher reward, but not worst odds)"""
    if not edge_data:
        return False
    
    edge = edge_data.get("edge", 0)
    prob = edge_data.get("prob", 0.5)
    
    # DEGEN criteria:
    # - Positive edge (profitable)
    # - Lower probability (30-50% range) - higher risk
    # - Not the worst odds (not extremely negative)
    # - Higher potential payout
    
    if edge > 0 and 0.30 <= prob <= 0.50:
        # Check if odds are reasonable (not -500 or worse)
        if odds and odds > -400:
            return True
    
    return False

def create_prop_card(prop, player_info, game_info, edge_data=None):
    """Create a styled prop card"""
    player_name = player_info.get("name", "Unknown") if player_info else "Unknown"
    player_team = player_info.get("team", "N/A") if player_info else "N/A"
    position = player_info.get("position", "") if player_info else ""
    
    prop_type = prop.get("prop_type", "").replace("_", " ").title()
    line = prop.get("line")
    book = prop.get("book", "Unknown")
    
    over_price = prop.get("over_price")
    under_price = prop.get("under_price")
    
    # Determine if DEGEN play
    best_odds = over_price if over_price else under_price
    is_degen = is_degen_play(edge_data, best_odds) if edge_data else False
    
    # Format display
    card_html = f"""
    <div class="prop-card">
        <div class="player-name">
            {player_name}
            {f'<span class="degen-badge">🔥 DEGEN</span>' if is_degen else ''}
        </div>
        <div class="prop-info">
            {position} | {player_team} | {game_info.get('away_team', '')} @ {game_info.get('home_team', '') if game_info else ''}
        </div>
        <div style="margin: 0.75rem 0;">
            <strong>{prop_type} {line}</strong>
        </div>
        <div class="prop-info">
            O{line}: {format_odds(int(over_price)) if over_price else 'N/A'} | 
            U{line}: {format_odds(int(under_price)) if under_price else 'N/A'}
        </div>
        <div class="prop-info">
            Book: <strong>{book}</strong>
        </div>
    """
    
    if edge_data:
        edge = edge_data.get("edge", 0)
        edge_pct = edge * 100
        edge_class = "edge-positive" if edge > 0 else "edge-negative"
        card_html += f"""
        <div style="margin-top: 0.75rem;">
            <span class="{edge_class}">Edge: {edge_pct:+.1f}%</span>
        </div>
        """
    
    card_html += "</div>"
    return card_html

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
        selected_prop_types = prop_types[1:]  # All means all types
    
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

# Load data
games = load_tonight_games(sport)
game_ids = [g["id"] for g in games] if games else []

if not games:
    st.warning("⚠️ No games scheduled for tonight. Try adjusting the date range.")
    st.info("💡 To see games, run: `python workers/fetch_odds.py`")
    st.info("💡 Make sure you're on the **🏠 Home** page (check the sidebar navigation)")
    st.stop()

# Load props
props = load_player_props_for_feed(sport, game_ids)

if not props:
    st.info("📊 No player props available. Fetch player prop odds first.")
    st.info("💡 Run: `python workers/fetch_player_prop_odds.py`")
    st.info("💡 Make sure you're on the **🏠 Home** page (check the sidebar navigation)")
    st.stop()

# Filter props
filtered_props = []
for prop in props:
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
    if player_id:
        stats = load_player_stats_for_edge(player_id, prop.get("prop_type"))
        edge_data = calculate_prop_edge(prop, stats)
    
    # +EV filter
    if show_ev_only:
        if not edge_data or edge_data.get("edge", 0) <= 0:
            continue
    
    # DEGEN filter
    if degen_mode:
        best_odds = prop.get("over_price") or prop.get("under_price")
        if not is_degen_play(edge_data, best_odds):
            continue
    
    filtered_props.append((prop, edge_data))

# Sort props
if sort_by == "Edge (Highest)":
    filtered_props.sort(key=lambda x: x[1].get("edge", -999) if x[1] else -999, reverse=True)
elif sort_by == "Odds (Best)":
    filtered_props.sort(key=lambda x: x[0].get("over_price") or x[0].get("under_price") or 999, reverse=True)
elif sort_by == "Line (Lowest)":
    filtered_props.sort(key=lambda x: x[0].get("line", 999))
elif sort_by == "Player Name":
    filtered_props.sort(key=lambda x: x[0].get("players", {}).get("name", "") if isinstance(x[0].get("players"), dict) else "")

# Display props in grid
st.write(f"**Found {len(filtered_props)} props**")

# Create columns for grid layout
num_cols = 3
cols = st.columns(num_cols)

for idx, (prop, edge_data) in enumerate(filtered_props):
    with cols[idx % num_cols]:
        player_info = prop.get("players", {})
        game_info = prop.get("games", {})
        
        if isinstance(player_info, dict) and isinstance(game_info, dict):
            card_html = create_prop_card(prop, player_info, game_info, edge_data)
            st.markdown(card_html, unsafe_allow_html=True)
            
            # Add to slip button
            side = edge_data.get("side", "over") if edge_data else "over"
            button_text = f"➕ Add {side.upper()}"
            if st.button(button_text, key=f"add_{prop.get('id')}_{side}", use_container_width=True):
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
                # Check if leg already exists (simple check)
                leg_exists = any(
                    l.get("prop_id") == leg["prop_id"] and l.get("side") == leg["side"]
                    for l in st.session_state.slip_legs
                )
                if not leg_exists:
                    st.session_state.slip_legs.append(leg)
                    st.success("Added!")
                    st.rerun()

# Slip sidebar
with st.sidebar:
    if st.session_state.slip_legs:
        st.divider()
        st.subheader("🎫 Your Slip")
        
        total_odds = 1.0
        total_ev = 0.0
        
        for i, leg in enumerate(st.session_state.slip_legs):
            with st.container():
                st.markdown(f"""
                <div class="slip-leg">
                    <strong>{leg.get('player_name', 'Unknown')}</strong><br>
                    {leg.get('prop_type', '').replace('_', ' ').title()} {leg.get('line', '')} {leg.get('side', '').upper()}<br>
                    Odds: {format_odds(int(leg.get('odds', 0)))} | {leg.get('book', 'Unknown')}
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
            
            if st.button("🗑️ Clear Slip", use_container_width=True):
                st.session_state.slip_legs = []
                st.rerun()

