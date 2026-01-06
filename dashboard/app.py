import sys
from pathlib import Path
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from utils.ev import american_to_prob, ev
from services.ai_analysis import ai_service

# Page config is handled by main.py when using st.navigation()
# Removed to avoid conflicts

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .game-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        background: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .parlay-leg {
        background: #f8f9fa;
        padding: 0.75rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
    }
    .suggestion-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<h1 class="main-header">🎯 Sports Betting Analytics Dashboard</h1>', unsafe_allow_html=True)

# Sidebar filters
with st.sidebar:
    st.header("📊 Filters & Controls")
    
    # Sport selection
    sport = st.selectbox("Select Sport", ["NBA", "NFL"], index=0)
    
    # Date range
    st.subheader("Date Range")
    days_ahead = st.slider("Days ahead to show", 1, 14, 7)
    
    # Market type filter
    st.subheader("Market Types")
    show_h2h = st.checkbox("Moneyline (H2H)", value=True)
    show_spreads = st.checkbox("Spreads", value=True)
    show_totals = st.checkbox("Totals", value=True)
    
    # Bookmaker filter
    st.subheader("Bookmakers")
    all_books = st.checkbox("All Books", value=True)
    
    # Refresh button
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()

# Load data
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_games(sport, days_ahead):
    """Load games for the selected sport"""
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
def load_odds(game_ids, market_types):
    """Load odds for selected games"""
    if not game_ids:
        return []
    
    try:
        query = supabase.table("odds_snapshots").select("*").in_("game_id", game_ids)
        
        # Filter by market type if needed
        if market_types:
            query = query.in_("market_type", market_types)
        
        odds = query.order("created_at", desc=True).execute().data
        
        # Get latest odds per game/book/market/outcome
        latest_odds = {}
        for odd in odds:
            key = (odd["game_id"], odd["book"], odd["market_type"], odd["market_label"])
            if key not in latest_odds or odd["created_at"] > latest_odds[key]["created_at"]:
                latest_odds[key] = odd
        
        return list(latest_odds.values())
    except Exception as e:
        # Return empty for demo mode
        return []

# Load data
games = load_games(sport, days_ahead)
game_ids = [g["id"] for g in games]

market_types = []
if show_h2h:
    market_types.append("h2h")
if show_spreads:
    market_types.append("spreads")
if show_totals:
    market_types.append("totals")

odds = load_odds(game_ids, market_types) if game_ids else []

# Create game lookup
game_lookup = {g["id"]: g for g in games}

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs(["📈 Overview", "🎲 Parlay Builder", "💡 Smart Suggestions", "📊 Analysis"])

with tab1:
    st.header("📊 Dashboard Overview")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Upcoming Games", len(games))
    
    with col2:
        st.metric("Total Odds", len(odds))
    
    with col3:
        unique_books = len(set(o["book"] for o in odds)) if odds else 0
        st.metric("Bookmakers", unique_books)
    
    with col4:
        if games:
            next_game = min(games, key=lambda x: x["start_time"])
            next_time = datetime.fromisoformat(next_game["start_time"].replace("Z", "+00:00"))
            st.metric("Next Game", next_time.strftime("%m/%d %H:%M"))
    
    st.divider()
    
    # Games list with odds
    st.subheader(f"🏀 Upcoming {sport} Games")
    
    if not games:
        st.info("No games found for the selected criteria. Try adjusting your filters or fetch new odds data.")
    else:
        for game in games:
            game_odds = [o for o in odds if o["game_id"] == game["id"]]
            
            from dashboard.ui_components import format_game_time
            game_time_formatted = format_game_time(game['start_time'])
            with st.expander(f"🏀 {game['away_team']} @ {game['home_team']} - {game_time_formatted}"):
                if game_odds:
                    # Group odds by market type
                    h2h_odds = [o for o in game_odds if o["market_type"] == "h2h"]
                    spread_odds = [o for o in game_odds if o["market_type"] == "spreads"]
                    total_odds = [o for o in game_odds if o["market_type"] == "totals"]
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if h2h_odds:
                            st.write("**Moneyline**")
                            h2h_df = pd.DataFrame(h2h_odds)
                            h2h_display = h2h_df[["book", "market_label", "price"]].copy()
                            h2h_display.columns = ["Book", "Team", "Odds"]
                            st.dataframe(h2h_display, use_container_width=True, hide_index=True)
                    
                    with col2:
                        if spread_odds:
                            st.write("**Spreads**")
                            spread_df = pd.DataFrame(spread_odds)
                            spread_display = spread_df[["book", "market_label", "line", "price"]].copy()
                            spread_display.columns = ["Book", "Team", "Line", "Odds"]
                            st.dataframe(spread_display, use_container_width=True, hide_index=True)
                    
                    with col3:
                        if total_odds:
                            st.write("**Totals**")
                            total_df = pd.DataFrame(total_odds)
                            total_display = total_df[["book", "market_label", "line", "price"]].copy()
                            total_display.columns = ["Book", "Type", "Line", "Odds"]
                            st.dataframe(total_display, use_container_width=True, hide_index=True)
                else:
                    st.info("No odds available for this game")

with tab2:
    st.header("🎲 Custom Parlay Builder")
    st.write("Build your own parlay by selecting bets from available games")
    
    if not games or not odds:
        st.warning("No games or odds available. Please fetch odds data first.")
    else:
        # Initialize session state for parlay
        if "parlay_legs" not in st.session_state:
            st.session_state.parlay_legs = []
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Available Bets")
            
            # Group odds by game for easier selection
            for game in games:
                game_odds = [o for o in odds if o["game_id"] == game["id"]]
                if not game_odds:
                    continue
                
                from dashboard.ui_components import format_game_time
                game_time_formatted = format_game_time(game["start_time"])
                with st.expander(f"{game['away_team']} @ {game['home_team']} - {game_time_formatted}"):
                    for odd in game_odds:
                        # Format the bet description
                        if odd["market_type"] == "h2h":
                            bet_desc = f"{odd['market_label']} (Moneyline)"
                        elif odd["market_type"] == "spreads":
                            bet_desc = f"{odd['market_label']} {odd.get('line', 'N/A')}"
                        elif odd["market_type"] == "totals":
                            bet_desc = f"{odd['market_label']} {odd.get('line', 'N/A')}"
                        else:
                            bet_desc = f"{odd['market_label']}"
                        
                        odds_display = f"{odd['price']:+d}" if odd['price'] else "N/A"
                        key = f"{game['id']}_{odd['id']}"
                        
                        col_a, col_b, col_c = st.columns([3, 1, 1])
                        with col_a:
                            st.write(f"**{bet_desc}**")
                        with col_b:
                            st.write(f"**{odds_display}**")
                        with col_c:
                            if st.button("➕ Add", key=key, use_container_width=True):
                                leg = {
                                    "game": f"{game['away_team']} @ {game['home_team']}",
                                    "bet": bet_desc,
                                    "book": odd["book"],
                                    "price": odd["price"],
                                    "game_id": game["id"],
                                    "odd_id": odd["id"],
                                    "market_type": odd["market_type"],
                                    "line": odd.get("line")
                                }
                                if leg not in st.session_state.parlay_legs:
                                    st.session_state.parlay_legs.append(leg)
                                    st.success("Added!")
                                    st.rerun()
        
        with col2:
            st.subheader("Your Parlay")
            
            if not st.session_state.parlay_legs:
                st.info("Add bets from the left to build your parlay")
            else:
                total_odds = 1.0
                for i, leg in enumerate(st.session_state.parlay_legs):
                    with st.container():
                        st.markdown(f"""
                        <div class="parlay-leg">
                            <strong>{leg['bet']}</strong><br>
                            <small>{leg['game']}</small><br>
                            <small>Book: {leg['book']}</small><br>
                            <strong>Odds: {leg['price']:+d}</strong>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button("❌ Remove", key=f"remove_{i}", use_container_width=True):
                            st.session_state.parlay_legs.pop(i)
                            st.rerun()
                    
                    # Calculate combined odds
                    if leg["price"]:
                        if leg["price"] > 0:
                            decimal = leg["price"] / 100 + 1
                        else:
                            decimal = 100 / abs(leg["price"]) + 1
                        total_odds *= decimal
                
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
                    st.metric("Implied Probability", f"{(1/total_odds)*100:.2f}%")
                    
                    # Payout calculator
                    st.subheader("💰 Payout Calculator")
                    bet_amount = st.number_input("Bet Amount ($)", min_value=1, value=100, step=10)
                    payout = bet_amount * total_odds
                    profit = payout - bet_amount
                    st.metric("Total Payout", f"${payout:,.2f}")
                    st.metric("Profit", f"${profit:,.2f}")
                
                if st.button("🗑️ Clear Parlay", use_container_width=True):
                    st.session_state.parlay_legs = []
                    st.rerun()

with tab3:
    st.header("💡 Smart Pairing Suggestions & AI Analysis")
    st.write("AI-powered suggestions for profitable bet combinations")
    
    if not odds:
        st.warning("No odds data available for suggestions.")
    else:
        # AI Analysis Section
        st.subheader("🤖 AI Game Analysis")
        st.write("Automated insights for top upcoming games.")
        
        if games:
            # Analyze top 3 games
            for game in games[:3]:
                with st.expander(f"Analysis: {game['away_team']} @ {game['home_team']}"):
                    # Get odds for this game
                    g_odds = [o for o in odds if o['game_id'] == game['id']]
                    analysis = ai_service.analyze_game(game, g_odds)
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if analysis.get('prediction'):
                            st.markdown(f"#### Prediction: {analysis['prediction']}")
                        
                        st.write("**Key Factors:**")
                        for reason in analysis.get('reasoning', []):
                            st.write(f"• {reason}")
                            
                    with col2:
                        st.metric("Confidence", analysis.get('confidence', 'Low'))
                        
        st.divider()
        
        # Calculate EV for all odds
        suggestions = []
        for odd in odds:
            if odd["price"]:
                prob = american_to_prob(odd["price"])
                ev_value = ev(prob, odd["price"])
                if ev_value > 0:  # Only positive EV bets
                    game = game_lookup.get(odd["game_id"], {})
                    suggestions.append({
                        "game": f"{game.get('away_team', 'Unknown')} @ {game.get('home_team', 'Unknown')}",
                        "bet": odd["market_label"],
                        "book": odd["book"],
                        "price": odd["price"],
                        "ev": ev_value,
                        "market_type": odd["market_type"],
                        "line": odd.get("line")
                    })
        
        if suggestions:
            # Sort by EV
            suggestions.sort(key=lambda x: x["ev"], reverse=True)
            
            st.subheader("🔥 Top Value Bets (Positive EV)")
            
            # Show top 10
            for i, sug in enumerate(suggestions[:10], 1):
                with st.container():
                    ev_color = "🟢" if sug["ev"] > 0.1 else "🟡"
                    st.markdown(f"""
                    <div class="suggestion-card">
                        <h4>{ev_color} #{i}: {sug['bet']}</h4>
                        <p><strong>Game:</strong> {sug['game']}<br>
                        <strong>Book:</strong> {sug['book']} | <strong>Odds:</strong> {sug['price']:+d}<br>
                        <strong>Expected Value:</strong> {sug['ev']:.3f} ({sug['ev']*100:.1f}%)</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.divider()
            
            # Suggest pairings
            st.subheader("🎯 Suggested Pairings")
            st.write("Top 2-leg and 3-leg parlay combinations with high combined EV")
            
            # Generate 2-leg combinations
            top_suggestions = suggestions[:15]  # Top 15 for pairing
            pairings = []
            
            for i in range(len(top_suggestions)):
                for j in range(i + 1, len(top_suggestions)):
                    leg1 = top_suggestions[i]
                    leg2 = top_suggestions[j]
                    
                    # Calculate combined EV (simplified)
                    combined_ev = (leg1["ev"] + leg2["ev"]) / 2
                    
                    pairings.append({
                        "legs": [leg1, leg2],
                        "combined_ev": combined_ev
                    })
            
            # Sort by combined EV
            pairings.sort(key=lambda x: x["combined_ev"], reverse=True)
            
            # Show top 5 pairings
            for i, pairing in enumerate(pairings[:5], 1):
                with st.expander(f"💎 Pairing #{i} - Combined EV: {pairing['combined_ev']:.3f}"):
                    for leg in pairing["legs"]:
                        st.write(f"**{leg['bet']}** ({leg['game']}) - Odds: {leg['price']:+d} | EV: {leg['ev']:.3f}")
        else:
            st.info("No positive EV bets found. Try fetching fresh odds data.")

with tab4:
    st.header("📊 Data Analysis")
    
    if not odds:
        st.warning("No odds data available for analysis.")
    else:
        # Create analysis dataframe
        df = pd.DataFrame(odds)
        df = df.merge(pd.DataFrame(games), left_on="game_id", right_on="id", how="left")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 Odds Distribution by Market Type")
            market_counts = df["market_type"].value_counts()
            st.bar_chart(market_counts)
        
        with col2:
            st.subheader("📊 Bookmaker Coverage")
            book_counts = df["book"].value_counts()
            st.bar_chart(book_counts)
        
        st.divider()
        
        # Best odds finder
        st.subheader("🔍 Best Odds Finder")
        st.write("Find the best odds for each market across all bookmakers")
        
        if len(games) > 0:
            game_options = [f"{g['away_team']} @ {g['home_team']}" for g in games]
            selected_game = st.selectbox("Select Game", game_options, key="analysis_game")
            
            selected_game_idx = game_options.index(selected_game)
            selected_game_obj = games[selected_game_idx]
            game_odds = [o for o in odds if o["game_id"] == selected_game_obj["id"]]
            
            if game_odds:
                odds_df = pd.DataFrame(game_odds)
                
                # Group by market and find best odds
                for market_type in odds_df["market_type"].unique():
                    market_odds = odds_df[odds_df["market_type"] == market_type]
                    
                    st.write(f"**{market_type.upper()}**")
                    best_odds = market_odds.loc[market_odds.groupby("market_label")["price"].idxmax()]
                    display_df = best_odds[["market_label", "book", "price", "line"]].copy()
                    display_df.columns = ["Bet", "Best Book", "Best Odds", "Line"]
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                    st.divider()

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p>Sports Betting Analytics Dashboard | Data updates every 5 minutes | Last updated: {}</p>
</div>
""".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), unsafe_allow_html=True)
