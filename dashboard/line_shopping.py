"""
Line Shopping Tool
Compare our custom projections vs all book lines to find best value
"""
import streamlit as st
from services.db import supabase
from services.projections import calculate_projection
from datetime import datetime
from dashboard.ui_components import format_odds, format_game_time
from dashboard.data_loaders import load_tonight_games, load_all_players
from typing import List, Dict

def load_all_book_lines(player_id: str, game_id: str, prop_type: str) -> List[Dict]:
    """
    Load all book lines for a specific player prop
    
    Returns:
        List of dicts with book, line, over_price, under_price
    """
    try:
        props = (
            supabase.table("player_prop_odds")
            .select("book, line, over_price, under_price, created_at")
            .eq("player_id", player_id)
            .eq("game_id", game_id)
            .eq("prop_type", prop_type)
            .order("created_at", desc=True)
            .execute()
            .data
        )
        
        # Group by book and get most recent line for each book
        book_lines = {}
        for prop in props:
            book = prop.get("book")
            if book and book not in book_lines:
                book_lines[book] = {
                    "book": book,
                    "line": prop.get("line"),
                    "over_price": prop.get("over_price"),
                    "under_price": prop.get("under_price"),
                    "created_at": prop.get("created_at")
                }
        
        return list(book_lines.values())
    except:
        return []


def calculate_line_value(our_line: float, book_line: float, book_odds: int, side: str) -> Dict:
    """
    Calculate value of betting on a book line vs our projection
    
    Returns:
        Dict with value_score, recommendation, edge
    """
    if our_line is None or book_line is None:
        return {"value_score": 0, "recommendation": "No data", "edge": 0}
    
    # Calculate difference
    diff = our_line - book_line
    
    # If our line is higher, over has value
    # If our line is lower, under has value
    if diff > 0.5:  # Our line is significantly higher
        recommended_side = "over"
        value_score = diff * 10  # Scale for display
    elif diff < -0.5:  # Our line is significantly lower
        recommended_side = "under"
        value_score = abs(diff) * 10
    else:
        recommended_side = "neutral"
        value_score = 0
    
    # Calculate edge (simplified)
    # If betting over and our line is higher, positive edge
    if side == "over" and diff > 0:
        edge = diff * 5  # Rough edge calculation
    elif side == "under" and diff < 0:
        edge = abs(diff) * 5
    else:
        edge = 0
    
    return {
        "value_score": value_score,
        "recommendation": recommended_side,
        "edge": edge,
        "diff": diff
    }


def render_line_shopping():
    """Main line shopping interface"""
    st.title("🛒 Line Shopping Tool")
    st.markdown("""
    **Compare our custom projections vs all book lines to find the best value**
    
    Our projections are based on:
    - Player historical performance
    - Matchup analysis (vs opponent, home/away)
    - Injury reports (free sources)
    - Recent form and trends
    - Opponent defense ratings
    """)
    
    # Sport selector
    sport = st.selectbox("Sport", ["NBA", "NFL"], index=0)
    
    # Load games
    games = load_tonight_games(sport.lower() if sport == "NBA" else sport) # Assuming sport param expects NBA/NFL as is or lowercase
    
    if not games:
        st.warning("No games found. Fetch games first: `python workers/fetch_odds.py`")
        st.stop()
    
    # Game selector
    game_options = [
        f"{g.get('away_team', '?')} @ {g.get('home_team', '?')} - {format_game_time(g.get('start_time', ''))}"
        for g in games
    ]
    selected_game_idx = st.selectbox("Select Game", range(len(game_options)), format_func=lambda x: game_options[x])
    selected_game = games[selected_game_idx]
    
    # Load players in this game
    try:
        # Get players from both teams
        home_team = selected_game.get("home_team")
        away_team = selected_game.get("away_team")
        
        players = (
            supabase.table("players")
            .select("id, name, team, position")
            .eq("sport", sport)
            .in_("team", [home_team, away_team])
            .order("name")
            .execute()
            .data
        )
    except:
        players = []
    
    if not players:
        st.warning("No players found for this game. Sync players first: `python workers/fetch_player_stats.py --sync-players`")
        st.stop()
    
    # Player selector
    player_options = [f"{p['name']} ({p.get('team', '?')} - {p.get('position', '?')})" for p in players]
    selected_player_idx = st.selectbox("Select Player", range(len(player_options)), format_func=lambda x: player_options[x])
    selected_player = players[selected_player_idx]
    
    # Prop type selector
    prop_types = ["points", "rebounds", "assists", "pra", "threes"]
    prop_type = st.selectbox("Prop Type", prop_types)
    
    st.divider()
    
    # Calculate our projection
    with st.spinner("Calculating our projection..."):
        try:
            # Get opponent
            player_team = selected_player.get("team")
            opponent = away_team if player_team == home_team else home_team
            is_home = player_team == home_team
            
            # Calculate projection
            projection = calculate_projection(
                player_id=selected_player["id"],
                prop_type=prop_type,
                opponent_team=opponent,
                is_home=is_home,
                game_id=selected_game["id"]
            )
            
            our_line = projection.get("projected_line")
            confidence = projection.get("confidence", 0) * 100
            factors = projection.get("factors", {})
        except Exception as e:
            st.error(f"Error calculating projection: {e}")
            our_line = None
            confidence = 0
            factors = {}
    
    # Display our projection
    col1, col2, col3 = st.columns(3)
    with col1:
        if our_line:
            st.metric("Our Projected Line", f"{our_line:.1f}", delta=f"{confidence:.0f}% confidence")
        else:
            st.metric("Our Projected Line", "N/A")
    
    with col2:
        st.metric("Confidence", f"{confidence:.0f}%")
    
    with col3:
        baseline_source = factors.get("baseline_source", "unknown")
        st.metric("Baseline", baseline_source.replace("_", " ").title())
    
    # Show projection factors
    if factors:
        with st.expander("📊 Projection Factors"):
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Adjustments:**")
                st.write(f"- Player Avg: {factors.get('player_avg', 0):.1f}")
                st.write(f"- Defense Adj: {factors.get('defense_adjustment', 1.0):.2f}x")
                st.write(f"- Matchup Adj: {factors.get('matchup_adjustment', 1.0):.2f}x")
                st.write(f"- Home/Away Adj: {factors.get('home_away_adjustment', 1.0):.2f}x")
            with col2:
                st.write("**Other Factors:**")
                st.write(f"- Injury Adj: {factors.get('injury_adjustment', 1.0):.2f}x")
                st.write(f"- Rest Adj: {factors.get('rest_adjustment', 1.0):.2f}x")
                rest_days = factors.get("rest_days")
                if rest_days is not None:
                    st.write(f"- Rest Days: {rest_days}")
    
    st.divider()
    
    # Load all book lines
    st.subheader("📚 Book Lines Comparison")
    
    book_lines = load_all_book_lines(
        selected_player["id"],
        selected_game["id"],
        prop_type
    )
    
    if not book_lines:
        st.warning("No book lines found. Fetch player props first: `python workers/fetch_player_prop_odds.py`")
        st.stop()
    
    # Sort by value (if we have our projection)
    if our_line:
        for book_line in book_lines:
            # Calculate value for over and under
            over_value = calculate_line_value(our_line, book_line["line"], book_line.get("over_price", 0), "over")
            under_value = calculate_line_value(our_line, book_line["line"], book_line.get("under_price", 0), "under")
            
            # Use the better value
            if over_value["value_score"] > under_value["value_score"]:
                book_line["value"] = over_value
                book_line["best_side"] = "over"
            else:
                book_line["value"] = under_value
                book_line["best_side"] = "under"
        
        book_lines.sort(key=lambda x: x.get("value", {}).get("value_score", 0), reverse=True)
    
    # Display book lines in table
    st.markdown("### Best Value Lines")
    
    for i, book_line in enumerate(book_lines):
        line = book_line["line"]
        over_price = book_line.get("over_price")
        under_price = book_line.get("under_price")
        book = book_line["book"]
        value = book_line.get("value", {})
        best_side = book_line.get("best_side", "neutral")
        
        # Calculate difference from our line
        if our_line:
            diff = our_line - line
            diff_str = f"{diff:+.1f}" if diff != 0 else "0.0"
            diff_color = "🟢" if abs(diff) > 0.5 else "🟡" if abs(diff) > 0.2 else "⚪"
        else:
            diff_str = "N/A"
            diff_color = ""
        
        # Create card
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])
            
            with col1:
                st.write(f"**{book}**")
            
            with col2:
                st.write(f"**Line: {line:.1f}**")
                if our_line:
                    st.caption(f"{diff_color} {diff_str} vs our line")
            
            with col3:
                if over_price:
                    st.write(f"Over: {format_odds(int(over_price))}")
                else:
                    st.write("Over: N/A")
            
            with col4:
                if under_price:
                    st.write(f"Under: {format_odds(int(under_price))}")
                else:
                    st.write("Under: N/A")
            
            with col5:
                if value.get("value_score", 0) > 0:
                    st.success(f"✅ {best_side.upper()}")
                    st.caption(f"Value: {value.get('value_score', 0):.1f}")
                else:
                    st.info("Neutral")
            
            st.divider()
    
    # Summary
    if our_line and book_lines:
        st.subheader("💡 Shopping Summary")
        
        # Find best over and under
        best_over = None
        best_under = None
        
        for bl in book_lines:
            if bl.get("over_price") and (not best_over or bl["over_price"] > best_over["over_price"]):
                best_over = bl
            if bl.get("under_price") and (not best_under or bl["under_price"] > best_under["under_price"]):
                best_under = bl
        
        col1, col2 = st.columns(2)
        
        with col1:
            if best_over:
                st.success(f"**Best Over:** {best_over['book']} - {best_over['line']:.1f} @ {format_odds(int(best_over['over_price']))}")
                if our_line:
                    diff = our_line - best_over["line"]
                    if diff > 0.5:
                        st.caption(f"✅ Our line ({our_line:.1f}) is {diff:.1f} higher - Over has value!")
        
        with col2:
            if best_under:
                st.success(f"**Best Under:** {best_under['book']} - {best_under['line']:.1f} @ {format_odds(int(best_under['under_price']))}")
                if our_line:
                    diff = our_line - best_under["line"]
                    if diff < -0.5:
                        st.caption(f"✅ Our line ({our_line:.1f}) is {abs(diff):.1f} lower - Under has value!")


if __name__ == "__main__":
    render_line_shopping()
