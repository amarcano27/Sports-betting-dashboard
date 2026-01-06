"""
Reusable UI Components for the Million Dollar Dashboard
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import textwrap
import html
import html.parser

def render_metric_card(label, value, delta=None, color="neutral"):
    """
    Renders a sleek metric card
    """
    color_map = {
        "success": "#00E5FF",
        "danger": "#FF2E63",
        "neutral": "#FFFFFF"
    }
    c = color_map.get(color, "#FFFFFF")
    
    delta_html = ""
    if delta:
        # Determine delta color
        delta_color = "#B0B0B0" # Default light grey
        
        # Try to parse as number to determine color
        try:
            # Remove common non-numeric chars
            clean_delta = str(delta).replace("%", "").replace("+", "").replace(" games", "").strip()
            delta_val = float(clean_delta)
            
            if delta_val > 0:
                delta_color = "#00E5FF"
            elif delta_val < 0:
                delta_color = "#FF2E63"
        except ValueError:
            # If not a number, check for explicit signs
            if "+" in str(delta):
                delta_color = "#00E5FF"
            elif "-" in str(delta):
                delta_color = "#FF2E63"
            # Otherwise keep default gray
            
        delta_escaped = html.escape(str(delta))
        delta_html = f'<span style="color: {delta_color}; font-size: 0.9rem; margin-left: 8px;">{delta_escaped}</span>'

    # Escape HTML entities
    label_escaped = html.escape(str(label))
    value_escaped = html.escape(str(value))
    
    html_content = f"""<div style="background: #141414; border: 1px solid #2A2A2A; border-radius: 8px; padding: 15px;">
<div style="color: #CCCCCC; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px;">{label_escaped}</div>
<div style="font-family: 'JetBrains Mono'; font-size: 1.8rem; font-weight: 700; color: {c};">
{value_escaped}
{delta_html}
</div>
</div>"""
    st.markdown(html_content, unsafe_allow_html=True)

def render_hit_rate_card(label, hit_rate_pct, avg_value, color="neutral"):
    """
    Renders a specialized card for hit rates
    """
    color_map = {
        "success": "#00E5FF",
        "danger": "#FF2E63",
        "neutral": "#FFFFFF"
    }
    c = color_map.get(color, "#FFFFFF")
    
    # Escape HTML entities
    label_escaped = html.escape(str(label))
    hit_rate_escaped = html.escape(str(hit_rate_pct))
    avg_value_escaped = html.escape(str(avg_value))
    
    html_content = f"""<div style="background: #141414; border: 1px solid #2A2A2A; border-radius: 8px; padding: 15px; text-align: center;">
<div style="color: #CCCCCC; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">{label_escaped}</div>
<div style="font-family: 'JetBrains Mono'; font-size: 2rem; font-weight: 800; color: {c}; margin-bottom: 4px;">
{hit_rate_escaped}
</div>
<div style="font-size: 0.8rem; color: #CCCCCC; border-top: 1px solid #333; padding-top: 8px; margin-top: 8px;">
{avg_value_escaped}
</div>
</div>"""
    st.markdown(html_content, unsafe_allow_html=True)

def decode_html_entities(text):
    """
    Decode HTML entities like &#x27; to their actual characters
    """
    if not text:
        return text
    try:
        # First decode HTML entities (like &#x27; -> ')
        decoded = html.unescape(str(text))
        return decoded
    except Exception:
        return str(text)

def render_prop_card_header(player_name, team, opponent, game_time, image_url=None):
    """
    Renders the top part of a prop card
    """
    # First decode HTML entities, then escape for safe display
    player_name_decoded = decode_html_entities(player_name)
    team_decoded = decode_html_entities(team)
    opponent_decoded = decode_html_entities(opponent)
    
    player_name_escaped = html.escape(str(player_name_decoded))
    team_escaped = html.escape(str(team_decoded))
    opponent_escaped = html.escape(str(opponent_decoded))
    game_time_escaped = html.escape(str(game_time))
    
    # Safe initial extraction from decoded name
    initial = str(player_name_decoded)[0] if player_name_decoded and len(str(player_name_decoded)) > 0 else "?"
    initial_escaped = html.escape(initial)
    
    if image_url:
        # Escape image URL but keep it as a valid URL
        image_url_escaped = html.escape(str(image_url))
        # Use onerror to fallback to initials if image fails to load
        img_html = f'<img src="{image_url_escaped}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover; border: 2px solid #333; display: block;" onerror="this.style.display=\'none\'; this.nextElementSibling.style.display=\'flex\';">'
        fallback_html = f'<div style="width: 40px; height: 40px; background: #222; border-radius: 50%; display: none; align-items: center; justify-content: center; font-weight: bold; color: #CCCCCC;">{initial_escaped}</div>'
        avatar_html = f'{img_html}{fallback_html}'
    else:
        avatar_html = f'<div style="width: 40px; height: 40px; background: #222; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; color: #CCCCCC;">{initial_escaped}</div>'

    return f"""<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
<div style="display: flex; align-items: center; gap: 12px;">
{avatar_html}
<div>
<div style="font-weight: 700; font-size: 1.1rem; color: #FFF;">{player_name_escaped}</div>
<div style="font-size: 0.8rem; color: #CCCCCC;">{team_escaped} vs {opponent_escaped} • {game_time_escaped}</div>
</div>
</div>
</div>"""

def render_edge_meter(edge_pct):
    """
    Renders a visual bar for the edge
    """
    width = min(abs(edge_pct) * 2, 100)  # Scale edge to width
    color = "#00E5FF" if edge_pct > 0 else "#FF2E63"
    
    return f"""<div style="margin-top: 10px;">
<div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 4px;">
<span style="color: #CCCCCC;">EDGE</span>
<span style="color: {color}; font-weight: bold;">{edge_pct:+.1f}%</span>
</div>
<div style="width: 100%; height: 6px; background: #222; border-radius: 3px; overflow: hidden;">
<div style="width: {width}%; height: 100%; background: {color}; border-radius: 3px;"></div>
</div>
</div>"""

def render_context_badge(context_summary):
    """
    Renders a badge if there is significant context
    """
    if not context_summary or context_summary == "No significant context":
        return ""
    
    # Escape HTML entities
    context_escaped = html.escape(str(context_summary))
    
    return f"""<div style="margin-top: 12px; padding: 8px 12px; background: rgba(255, 165, 0, 0.1); border: 1px solid rgba(255, 165, 0, 0.3); border-radius: 6px; font-size: 0.8rem; color: #FFA500; display: flex; align-items: center; gap: 8px;">
<span>⚡</span> {context_escaped}
</div>"""

def render_bet_slip(legs):
    """
    Renders the bet slip in the sidebar
    """
    st.markdown("### 🎫 BET SLIP")
    
    if not legs:
        st.info("Your slip is empty. Add legs from the marketplace.")
        return

    total_odds = 1
    
    for i, leg in enumerate(legs):
        # Calculate parlay odds (simplified)
        odds = leg.get('odds')
        if odds:
            if odds > 0:
                dec_odds = (odds / 100) + 1
            else:
                dec_odds = (100 / abs(odds)) + 1
            total_odds *= dec_odds
            
        # Render leg - decode HTML entities first, then escape all dynamic content
        player_name_clean = decode_html_entities(leg.get('player_name', 'Unknown'))
        player_name_escaped = html.escape(str(player_name_clean))
        prop_type_escaped = html.escape(str(leg.get('prop_type', 'N/A')))
        side_escaped = html.escape(str(leg.get('side', 'N/A')).upper())
        line_escaped = html.escape(str(leg.get('line', 'N/A')))
        odds_escaped = html.escape(str(leg.get('odds', 'N/A')))
        
        leg_html = f"""<div style="background: #1A1A1A; padding: 12px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid #00E5FF; position: relative;">
<div style="font-weight: 700; color: #FFF; font-size: 0.9rem;">{player_name_escaped}</div>
<div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
<div style="font-size: 0.8rem; color: #E0E0E0;">{prop_type_escaped} <span style="color: #00E5FF; font-weight: bold;">{side_escaped}</span> {line_escaped}</div>
<div style="font-family: 'JetBrains Mono'; font-size: 0.8rem; color: #CCCCCC;">{odds_escaped}</div>
</div>
</div>"""
        st.markdown(leg_html, unsafe_allow_html=True)
        
        if st.button("Remove", key=f"rem_{i}_{leg.get('prop_id')}"):
            legs.pop(i)
            st.rerun()

    # Summary
    if legs:
        # Convert total decimal odds back to American
        if total_odds >= 2:
            final_american = (total_odds - 1) * 100
        else:
            final_american = -100 / (total_odds - 1)
        
        st.markdown("---")
        total_odds_html = f"""<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
<div style="color: #CCCCCC;">Total Odds</div>
<div style="font-family: 'JetBrains Mono'; font-weight: 700; color: #00E5FF; font-size: 1.2rem;">{int(final_american):+d}</div>
</div>"""
        st.markdown(total_odds_html, unsafe_allow_html=True)
        
        st.button("🚀 PLACE BET (Simulated)", use_container_width=True)

def format_game_time(start_time_str):
    """
    Format game time correctly, handling timezone conversion.
    Assumes games are stored in UTC and converts to local timezone (EST/EDT).
    """
    try:
        from zoneinfo import ZoneInfo
        # Parse the ISO format time (assume UTC)
        if start_time_str.endswith('Z'):
            dt_utc = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        elif '+' in start_time_str:
            dt_utc = datetime.fromisoformat(start_time_str)
        else:
            # Assume UTC if no timezone info
            dt_utc = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        
        # Convert UTC to EST/EDT (handles DST automatically)
        try:
            est = ZoneInfo("America/New_York")
            dt_local = dt_utc.astimezone(est)
        except:
            # Fallback if zoneinfo not available (Python < 3.9)
            # EST is UTC-5, EDT is UTC-4
            # Simple check: March-November is EDT (UTC-4), rest is EST (UTC-5)
            month = dt_utc.month
            if 3 <= month <= 11:
                offset = -4  # EDT
            else:
                offset = -5  # EST
            dt_local = dt_utc + timedelta(hours=offset)
        
        # Format for display
        return dt_local.strftime('%I:%M %p')
    except Exception as e:
        return start_time_str

def format_odds(odds):
    """
    Format odds as American odds string
    """
    if odds is None:
        return "N/A"
    try:
        odds_int = int(odds)
        if odds_int > 0:
            return f"+{odds_int}"
        else:
            return str(odds_int)
    except (ValueError, TypeError):
        return "N/A"

def render_injury_ticker(injuries):
    """
    Renders a scrolling ticker of injury news.
    """
    if not injuries:
        return ""
    
    items = []
    for inj in injuries:
        player = inj.get('player_name') or inj.get('players', {}).get('name')
        status = inj.get('status', 'Unknown')
        team = inj.get('team') or inj.get('players', {}).get('team')
        if player:
            # Escape HTML entities
            player_escaped = html.escape(str(player))
            team_escaped = html.escape(str(team))
            status_escaped = html.escape(str(status))
            items.append(f"🚨 {player_escaped} ({team_escaped}): {status_escaped}")
    
    text = "   •   ".join(items)
    
    # CSS animation for ticker
    ticker_html = f"""
    <div style="width: 100%; overflow: hidden; background: #1A1A1A; color: #FFA500; padding: 10px 0; border-bottom: 1px solid #333; white-space: nowrap; margin-bottom: 20px;">
        <div style="display: inline-block; padding-left: 100%; animation: ticker 60s linear infinite;">
            <span style="font-family: 'JetBrains Mono'; font-weight: bold;">{text}</span>
        </div>
    </div>
    <style>
    @keyframes ticker {{
        0% {{ transform: translate3d(0, 0, 0); }}
        100% {{ transform: translate3d(-100%, 0, 0); }}
    }}
    </style>
    """
    st.markdown(ticker_html, unsafe_allow_html=True)
