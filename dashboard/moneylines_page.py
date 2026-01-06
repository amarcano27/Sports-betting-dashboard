"""
Moneylines Dashboard - Best odds finder and analysis
"""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from utils.ev import american_to_prob, ev
from dashboard.player_props import format_odds

# Page config is handled by main.py when using st.navigation()
# Removed to avoid conflicts

# Enhanced CSS
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #0e1117 0%, #1a1d29 100%);
    }
    .moneyline-card {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid #475569;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    .team-name {
        font-size: 1.5rem;
        font-weight: 700;
        color: #f8fafc;
        margin-bottom: 0.5rem;
    }
    .odds-display {
        font-size: 1.75rem;
        font-weight: 700;
        margin: 0.5rem 0;
    }
    .odds-positive {
        color: #10b981;
    }
    .odds-negative {
        color: #ef4444;
    }
    .best-odds-badge {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
        margin-left: 0.5rem;
    }
    .game-header {
        font-size: 1.75rem;
        font-weight: 700;
        color: #f8fafc;
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #475569;
    }
    .comparison-table {
        background: #1e293b;
        border-radius: 8px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "ml_slip" not in st.session_state:
    st.session_state.ml_slip = []

# Helper functions with caching
@st.cache_data(ttl=300)
def load_games_with_moneylines(sport, days_ahead=7):
    """Load games with moneyline odds"""
    try:
        cutoff_date = (datetime.now() + timedelta(days=days_ahead)).isoformat()
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
    except Exception as e:
        st.warning("⚠️ **Database unavailable. Using demo data.**\n\n💡 For production use, configure API keys in `.env` file. See `API_SETUP.md` for instructions.")
        from dashboard.demo_data_loader import get_demo_games
        return get_demo_games(sport)

@st.cache_data(ttl=300)
def load_moneyline_odds(game_ids):
    """Load moneyline odds for games"""
    if not game_ids:
        return []
    
    try:
        odds = (
            supabase.table("odds_snapshots")
            .select("*")
            .in_("game_id", game_ids)
            .eq("market_type", "h2h")
            .order("created_at", desc=True)
            .execute()
            .data
        )
        
        # Get latest odds per game/book/team
        latest_odds = {}
        for odd in odds:
            key = (odd["game_id"], odd["book"], odd["market_label"])
            if key not in latest_odds or odd["created_at"] > latest_odds[key]["created_at"]:
                latest_odds[key] = odd
        
        return list(latest_odds.values())
    except Exception as e:
        # Return empty for demo mode
        return []

def find_best_odds(game_odds, team):
    """Find best odds for a team across all books"""
    team_odds = [o for o in game_odds if o.get("market_label") == team]
    if not team_odds:
        return None
    
    # Best odds = highest price (most positive or least negative)
    best = max(team_odds, key=lambda x: x.get("price", -999))
    return best

def calculate_implied_prob(odds):
    """Calculate implied probability from American odds"""
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

# Sidebar
with st.sidebar:
    st.header("🎯 Filters")
    
    sport = st.selectbox("Sport", ["NBA", "NFL"], index=0)
    
    st.divider()
    
    days_ahead = st.slider("Days Ahead", 1, 14, 7)
    
    st.divider()
    
    show_best_only = st.checkbox("Show Best Odds Only", value=False)
    
    st.divider()
    
    # Moneyline slip
    if st.session_state.ml_slip:
        st.subheader("🎫 Moneyline Slip")
        for i, leg in enumerate(st.session_state.ml_slip):
            st.write(f"**{leg['team']}** - {format_odds(leg['odds'])} ({leg['book']})")
            if st.button("❌ Remove", key=f"ml_remove_{i}", use_container_width=True):
                st.session_state.ml_slip.pop(i)
                st.rerun()
        
        st.divider()
        
        # Calculate parlay
        if st.session_state.ml_slip:
            total_odds = 1.0
            for leg in st.session_state.ml_slip:
                odds = leg["odds"]
                if odds > 0:
                    decimal = odds / 100 + 1
                else:
                    decimal = 100 / abs(odds) + 1
                total_odds *= decimal
            
            american_odds = (total_odds - 1) * 100
            if american_odds > 100:
                american_odds = int(american_odds)
            else:
                american_odds = int(-100 / (american_odds / 100))
            
            st.metric("Parlay Odds", f"{american_odds:+d}")
            st.metric("Decimal", f"{total_odds:.2f}")
            
            bet_amount = st.number_input("Bet ($)", min_value=1, value=100, step=10, key="ml_bet")
            payout = bet_amount * total_odds
            st.metric("Payout", f"${payout:,.2f}")
            
            if st.button("🗑️ Clear Slip", use_container_width=True):
                st.session_state.ml_slip = []
                st.rerun()

# Title
st.title("💰 Moneylines Dashboard")

# Load data
games = load_games_with_moneylines(sport, days_ahead)
game_ids = [g["id"] for g in games] if games else []

if not games:
    st.warning("No games found. Fetch odds data first.")
    st.stop()

odds = load_moneyline_odds(game_ids)
game_lookup = {g["id"]: g for g in games}

# Group odds by game
games_with_odds = {}
for odd in odds:
    game_id = odd["game_id"]
    if game_id not in games_with_odds:
        games_with_odds[game_id] = []
    games_with_odds[game_id].append(odd)

# Display games
for game in games:
    game_id = game["id"]
    game_odds = games_with_odds.get(game_id, [])
    
    if not game_odds:
        continue
    
    from dashboard.ui_components import format_game_time
    game_time_formatted = format_game_time(game["start_time"])
    
    st.markdown(f"""
    <div class="game-header">
        {game['away_team']} @ {game['home_team']} - {game_time_formatted}
    </div>
    """, unsafe_allow_html=True)
    
    # Find best odds for each team
    away_best = find_best_odds(game_odds, game["away_team"])
    home_best = find_best_odds(game_odds, game["home_team"])
    
    # Create comparison table
    away_odds_list = [o for o in game_odds if o.get("market_label") == game["away_team"]]
    home_odds_list = [o for o in game_odds if o.get("market_label") == game["home_team"]]
    
    # Build comparison dataframe
    books = sorted(set(o["book"] for o in game_odds))
    comparison_data = {
        "Book": books,
        f"{game['away_team']}": [],
        f"{game['home_team']}": []
    }
    
    for book in books:
        away_odd = next((o for o in away_odds_list if o["book"] == book), None)
        home_odd = next((o for o in home_odds_list if o["book"] == book), None)
        
        comparison_data[f"{game['away_team']}"].append(
            format_odds(away_odd["price"]) if away_odd else "N/A"
        )
        comparison_data[f"{game['home_team']}"].append(
            format_odds(home_odd["price"]) if home_odd else "N/A"
        )
    
    comparison_df = pd.DataFrame(comparison_data)
    
    # Display in columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class="moneyline-card">
            <div class="team-name">
                {game['away_team']}
                {'<span class="best-odds-badge">BEST</span>' if away_best else ''}
            </div>
            <div class="odds-display {'odds-positive' if away_best and away_best.get('price', 0) > 0 else 'odds-negative'}">
                {format_odds(away_best['price']) if away_best else 'N/A'}
            </div>
            <div style="color: #cbd5e1; margin-top: 0.5rem;">
                {away_best['book'] if away_best else 'No odds'}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if away_best:
            prob = calculate_implied_prob(away_best["price"])
            st.metric("Implied Probability", f"{prob*100:.1f}%")
            
            if st.button(f"➕ Add {game['away_team']}", key=f"add_away_{game_id}", use_container_width=True):
                leg = {
                    "game": f"{game['away_team']} @ {game['home_team']}",
                    "team": game["away_team"],
                    "odds": away_best["price"],
                    "book": away_best["book"],
                    "game_id": game_id
                }
                if leg not in st.session_state.ml_slip:
                    st.session_state.ml_slip.append(leg)
                    st.success("Added!")
                    st.rerun()
    
    with col2:
        st.markdown(f"""
        <div class="moneyline-card">
            <div class="team-name">
                {game['home_team']}
                {'<span class="best-odds-badge">BEST</span>' if home_best else ''}
            </div>
            <div class="odds-display {'odds-positive' if home_best and home_best.get('price', 0) > 0 else 'odds-negative'}">
                {format_odds(home_best['price']) if home_best else 'N/A'}
            </div>
            <div style="color: #cbd5e1; margin-top: 0.5rem;">
                {home_best['book'] if home_best else 'No odds'}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if home_best:
            prob = calculate_implied_prob(home_best["price"])
            st.metric("Implied Probability", f"{prob*100:.1f}%")
            
            if st.button(f"➕ Add {game['home_team']}", key=f"add_home_{game_id}", use_container_width=True):
                leg = {
                    "game": f"{game['away_team']} @ {game['home_team']}",
                    "team": game["home_team"],
                    "odds": home_best["price"],
                    "book": home_best["book"],
                    "game_id": game_id
                }
                if leg not in st.session_state.ml_slip:
                    st.session_state.ml_slip.append(leg)
                    st.success("Added!")
                    st.rerun()
    
    # Show comparison table
    with st.expander("📊 Compare All Books"):
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)
        
        # Calculate best value
        st.subheader("💡 Best Value Analysis")
        
        if away_best and home_best:
            away_prob = calculate_implied_prob(away_best["price"])
            home_prob = calculate_implied_prob(home_best["price"])
            total_prob = away_prob + home_prob
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Away Implied", f"{away_prob*100:.1f}%")
            with col_b:
                st.metric("Home Implied", f"{home_prob*100:.1f}%")
            with col_c:
                st.metric("Total (Vig)", f"{total_prob*100:.1f}%")
            
            if total_prob > 1.0:
                vig = (total_prob - 1.0) * 100
                st.info(f"💰 Bookmaker edge (vig): {vig:.2f}%")
    
    st.divider()

# Summary stats
if odds:
    st.subheader("📊 Summary Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Games", len(games))
    
    with col2:
        unique_books = len(set(o["book"] for o in odds))
        st.metric("Books", unique_books)
    
    with col3:
        total_odds = len(odds)
        st.metric("Total Odds", total_odds)
    
    with col4:
        if games:
            next_game = min(games, key=lambda x: x["start_time"])
            next_time = datetime.fromisoformat(next_game["start_time"].replace("Z", "+00:00"))
            st.metric("Next Game", next_time.strftime("%m/%d %H:%M"))

