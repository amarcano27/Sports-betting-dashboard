"""
Player prop betting dashboard component
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Optional


def format_odds(odds: int) -> str:
    """Format American odds for display"""
    if odds is None:
        return "N/A"
    return f"{odds:+d}"


def calculate_hitrate(games: List[Dict], prop_type: str, line: float) -> Dict:
    """
    Calculate hitrate statistics for a player prop.
    
    Args:
        games: List of game dictionaries with player stats
        prop_type: Type of prop ('points', 'rebounds', 'assists', 'pra')
        line: The over/under line
    
    Returns:
        Dictionary with hitrate stats
    """
    if not games:
        return {}
    
    hitrates = {}
    averages = {}
    
    # Standard betting intervals
    periods = [5, 10, 20]
    
    # Calculate for specific periods
    for period in periods:
        recent_games = games[:period] if len(games) >= period else games
        
        if not recent_games:
            hitrates[f"L{period}"] = 0
            averages[f"L{period}"] = 0
            continue
        
        # Get prop values
        prop_values = []
        for game in recent_games:
            value = None
            if prop_type == "points":
                value = game.get("points", 0)
            elif prop_type == "rebounds":
                value = game.get("rebounds", 0)
            elif prop_type == "assists":
                value = game.get("assists", 0)
            elif prop_type == "threes":
                value = game.get("threes", 0)
            elif prop_type == "pra":
                value = (game.get("points", 0) + 
                        game.get("rebounds", 0) + 
                        game.get("assists", 0))
            
            if value is not None:
                prop_values.append(value)
        
        if prop_values:
            # Calculate average
            avg = sum(prop_values) / len(prop_values)
            averages[f"L{period}"] = round(avg, 1)
            
            # Calculate hitrate (percentage over the line)
            hits = sum(1 for v in prop_values if v > line)
            hitrate = (hits / len(prop_values)) * 100
            hitrates[f"L{period}"] = round(hitrate, 1)
        else:
            averages[f"L{period}"] = 0
            hitrates[f"L{period}"] = 0

    # Calculate Season (All available games)
    season_values = []
    for game in games:
        value = None
        if prop_type == "points": value = game.get("points", 0)
        elif prop_type == "rebounds": value = game.get("rebounds", 0)
        elif prop_type == "assists": value = game.get("assists", 0)
        elif prop_type == "threes": value = game.get("threes", 0)
        elif prop_type == "pra": value = (game.get("points", 0) + game.get("rebounds", 0) + game.get("assists", 0))
        
        if value is not None:
            season_values.append(value)
            
    if season_values:
        season_avg = sum(season_values) / len(season_values)
        averages["Season"] = round(season_avg, 1)
        season_hits = sum(1 for v in season_values if v > line)
        hitrates["Season"] = round((season_hits / len(season_values)) * 100, 1)
    else:
        averages["Season"] = 0
        hitrates["Season"] = 0
    
    return {
        "averages": averages,
        "hitrates": hitrates
    }


def create_prop_chart(games: List[Dict], prop_type: str, line: float, title: str = "Player Prop Chart") -> go.Figure:
    """
    Create a bar chart showing player prop performance vs the line.
    
    Args:
        games: List of game dictionaries
        prop_type: Type of prop ('points', 'rebounds', 'assists', 'pra')
        line: The over/under line
        title: Chart title
    
    Returns:
        Plotly figure
    """
    if not games:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig
    
    # Prepare data
    dates = []
    values = []
    labels = []
    colors = []
    
    for game in games:
        # Get game date
        game_date = game.get("date")
        if isinstance(game_date, str):
            try:
                date_obj = datetime.fromisoformat(game_date.replace("Z", "+00:00"))
                dates.append(date_obj)
            except:
                dates.append(None)
        else:
            dates.append(game_date)
        
        # Get opponent
        opponent = game.get("opponent", "Unknown")
        home_away = "vs" if game.get("home", True) else "@"
        labels.append(f"{home_away} {opponent}")
        
        # Get prop value
        value = None
        if prop_type == "points":
            value = game.get("points", 0)
        elif prop_type == "rebounds":
            value = game.get("rebounds", 0)
        elif prop_type == "assists":
            value = game.get("assists", 0)
        elif prop_type == "pra":
            value = (game.get("points", 0) + 
                    game.get("rebounds", 0) + 
                    game.get("assists", 0))
        
        values.append(value if value is not None else 0)
        
        # Color: green if over line, red if under
        if value is not None and value > line:
            colors.append("#10b981")  # Green
        else:
            colors.append("#ef4444")  # Red
    
    # Create chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=labels,
        y=values,
        marker_color=colors,
        text=values,
        textposition="outside",
        name=prop_type.title()
    ))
    
    # Add line
    fig.add_hline(
        y=line,
        line_dash="dash",
        line_color="gray",
        annotation_text=f"Line: {line}",
        annotation_position="right"
    )
    
    fig.update_layout(
        title=title,
        xaxis_title="Game",
        yaxis_title=prop_type.title(),
        showlegend=False,
        height=400,
        template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white"
    )
    
    return fig


def display_game_lines(game_data: Dict, odds_data: List[Dict]) -> None:
    """
    Display game lines in a table format.
    
    Args:
        game_data: Game information dictionary
        odds_data: List of odds for the game
    """
    if not game_data or not odds_data:
        st.warning("No game lines available")
        return
    
    # Organize odds by market type
    h2h_odds = {}
    spread_odds = {}
    total_odds = {}
    
    for odd in odds_data:
        market = odd.get("market_type")
        label = odd.get("market_label")
        price = odd.get("price")
        line = odd.get("line")
        book = odd.get("book")
        
        if market == "h2h":
            h2h_odds[label] = {"price": price, "book": book}
        elif market == "spreads":
            if label not in spread_odds:
                spread_odds[label] = {}
            spread_odds[label][book] = {"price": price, "line": line}
        elif market == "totals":
            if label not in total_odds:
                total_odds[label] = {}
            total_odds[label][book] = {"price": price, "line": line}
    
    # Create table
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    
    with col1:
        st.write("**Team**")
        st.write(game_data.get("away_team", "Away"))
        st.write("@")
        st.write(game_data.get("home_team", "Home"))
    
    with col2:
        st.write("**Spread**")
        # Get best spread odds for away team
        away_spread = spread_odds.get(game_data.get("away_team", ""), {})
        if away_spread:
            best_book = list(away_spread.keys())[0]
            spread_data = away_spread[best_book]
            st.write(f"{spread_data.get('line', 'N/A')} | {format_odds(spread_data.get('price'))}")
        else:
            st.write("N/A")
        
        st.write("")
        
        # Get best spread odds for home team
        home_spread = spread_odds.get(game_data.get("home_team", ""), {})
        if home_spread:
            best_book = list(home_spread.keys())[0]
            spread_data = home_spread[best_book]
            st.write(f"{spread_data.get('line', 'N/A')} | {format_odds(spread_data.get('price'))}")
        else:
            st.write("N/A")
    
    with col3:
        st.write("**Total**")
        # Get total odds
        over_total = total_odds.get("Over", {})
        under_total = total_odds.get("Under", {})
        
        if over_total:
            best_book = list(over_total.keys())[0]
            total_data = over_total[best_book]
            st.write(f"Over {total_data.get('line', 'N/A')} | {format_odds(total_data.get('price'))}")
        else:
            st.write("N/A")
        
        if under_total:
            best_book = list(under_total.keys())[0]
            total_data = under_total[best_book]
            st.write(f"Under {total_data.get('line', 'N/A')} | {format_odds(total_data.get('price'))}")
        else:
            st.write("N/A")
    
    with col4:
        st.write("**Moneyline**")
        away_ml = h2h_odds.get(game_data.get("away_team", ""), {})
        if away_ml:
            st.write(format_odds(away_ml.get("price")))
        else:
            st.write("N/A")
        
        st.write("")
        
        home_ml = h2h_odds.get(game_data.get("home_team", ""), {})
        if home_ml:
            st.write(format_odds(home_ml.get("price")))
        else:
            st.write("N/A")

