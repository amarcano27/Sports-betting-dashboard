"""
Reusable dashboard components
"""
import streamlit as st
import plotly.graph_objects as go
from rapidfuzz import process
from typing import List, Dict


def render_prop_card(prop: Dict, show_sparkline: bool = False, sparkline_data: List = None):
    """Render a prop card with modern design"""
    player_name = prop.get("player_name", "Unknown")
    team = prop.get("team", "N/A")
    position = prop.get("position", "N/A")
    prop_type = prop.get("prop_type", "N/A")
    line = prop.get("line", "N/A")
    over_price = prop.get("over_price")
    under_price = prop.get("under_price")
    book = prop.get("book", "N/A")
    edge = prop.get("edge")
    
    card_html = f"""
    <div class="prop-card">
        <div style="display: flex; justify-content: space-between; align-items: start;">
            <div>
                <p class="player-name">{player_name}</p>
                <p class="prop-info">{team} | {position}</p>
            </div>
            {f'<span class="edge-badge">+{edge:.1f}%</span>' if edge and edge > 0 else ''}
        </div>
        <hr style="border-color: #475569; margin: 0.75rem 0;">
        <p style="margin: 0.5rem 0;"><strong>{prop_type.upper()}</strong> {line}</p>
        <div style="display: flex; gap: 1rem; margin: 0.5rem 0;">
            <div>
                <small style="color: #94a3b8;">Over</small><br>
                <span class="odds-positive">{format_odds(int(over_price)) if over_price else 'N/A'}</span>
            </div>
            <div>
                <small style="color: #94a3b8;">Under</small><br>
                <span class="odds-negative">{format_odds(int(under_price)) if under_price else 'N/A'}</span>
            </div>
        </div>
        <p style="margin: 0.5rem 0;"><small style="color: #64748b;">{book}</small></p>
    </div>
    """
    return card_html


def format_odds(odds: int) -> str:
    """Format American odds"""
    if odds is None:
        return "N/A"
    return f"{odds:+d}"


def create_mini_sparkline(values: List[float], color: str = "#10b981", height: int = 30) -> go.Figure:
    """Create a mini sparkline chart"""
    if not values or len(values) < 2:
        return None
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=values,
        mode='lines+markers',
        line=dict(color=color, width=2),
        marker=dict(size=3, color=color),
        showlegend=False,
        hoverinfo='y'
    ))
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        template='plotly_dark'
    )
    return fig


def fuzzy_search_players(query: str, players: List[Dict], limit: int = 10) -> List[Dict]:
    """Fuzzy search players with autocomplete"""
    if not query or len(query) < 2:
        return []
    
    # Create searchable strings
    search_strings = [
        f"{p['name']} ({p.get('position', 'N/A')} - {p.get('team', 'N/A')})" 
        for p in players
    ]
    
    # Fuzzy match
    matches = process.extract(query, search_strings, limit=limit, score_cutoff=50)
    
    # Get full player objects
    results = []
    seen_ids = set()
    for match_str, score, _ in matches:
        # Extract player name
        player_name = match_str.split(" (")[0]
        player = next((p for p in players if p['name'] == player_name), None)
        if player and player['id'] not in seen_ids:
            results.append(player)
            seen_ids.add(player['id'])
    
    return results


def render_filter_chips(active_filter: str, filters: List[str], key_prefix: str = "filter"):
    """Render filter chips"""
    cols = st.columns(len(filters))
    selected = active_filter
    
    for i, filter_name in enumerate(filters):
        with cols[i]:
            is_active = filter_name == active_filter
            button_type = "primary" if is_active else "secondary"
            if st.button(filter_name, key=f"{key_prefix}_{i}", use_container_width=True, type=button_type):
                selected = filter_name
                st.rerun()
    
    return selected

