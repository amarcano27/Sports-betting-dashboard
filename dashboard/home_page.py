"""
Enhanced Home Page with Prop Marketplace Feed - Redesigned
Fixes duplicates, improves UI, adds all requested features
"""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
from rapidfuzz import process
import json
import html

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from services.projections import calculate_projection, compare_projection_to_book_line
from utils.ev import american_to_prob, ev
from dashboard.player_props import format_odds, calculate_hitrate
from dashboard.ui_components import (
    render_prop_card_header, render_edge_meter, render_metric_card, render_context_badge,
    format_game_time, render_bet_slip, render_injury_ticker
)
from dashboard.prop_insights import render_prop_insights
from dashboard.slip_generator import generate_optimal_slip
from dashboard.data_loaders import load_all_players, load_tonight_games, load_prop_feed_snapshots

# Initialize session state
if "slip_legs" not in st.session_state:
    st.session_state.slip_legs = []
if "degen_mode" not in st.session_state:
    st.session_state.degen_mode = False
if "trending_props" not in st.session_state:
    st.session_state.trending_props = {}

@st.cache_data(ttl=300)
def load_recent_injuries(sport):
    """Load recent injury news for the ticker"""
    try:
        query = supabase.table("player_injuries").select("*, players!inner(name, team, sport)")
        
        if sport == "Esports":
            # Need to filter by multiple sports on the joined table
            # Supabase-py postgrest syntax for joined filtering is tricky: players.sport.in.(...)
            # Simpler: filter in python or use raw sql, but let's try 'in' filter
            sub_sports = ["CS2", "LoL", "Dota2", "Valorant"]
            query = query.in_("players.sport", sub_sports)
        else:
            query = query.eq("players.sport", sport)
            
        injuries = (
            query
            .eq("status", "out") # Filter for significant news
            .order("updated_at", desc=True)
            .limit(15)
            .execute()
            .data
        )
        return injuries
    except Exception as e:
        return []

def _parse_metadata(metadata):
    if not metadata:
        return {}
    if isinstance(metadata, dict):
        return metadata
    if isinstance(metadata, str):
        try:
            return json.loads(metadata)
        except Exception:
            return {}
    return {}


def _build_edge_from_snapshot(prop, metadata):
    edge_value = prop.get("edge")
    snapshot_edge = metadata.get("edge") if metadata else None
    if edge_value is None and isinstance(snapshot_edge, dict):
        return snapshot_edge
    if edge_value is None:
        return None
    return {
        "edge": edge_value,
        "side": prop.get("edge_side") or (snapshot_edge.get("side") if isinstance(snapshot_edge, dict) else None),
        "prob": prop.get("edge_prob") or (snapshot_edge.get("prob") if isinstance(snapshot_edge, dict) else None),
        "odds": prop.get("ev_odds") or (snapshot_edge.get("odds") if isinstance(snapshot_edge, dict) else None),
    }


def _build_projection_from_snapshot(prop, metadata, show_projections: bool):
    if not show_projections:
        return None
    projected_line = prop.get("projection_line")
    if projected_line is None:
        return None
    projection_data = {
        "projected_line": projected_line,
        "confidence": prop.get("projection_confidence"),
        "baseline_source": prop.get("projection_baseline"),
        "bovada_line": prop.get("projection_bovada_line"),
    }
    projection_meta = metadata.get("projection_snapshot") if metadata else {}
    if isinstance(projection_meta, str):
        try:
            projection_meta = json.loads(projection_meta)
        except Exception:
            projection_meta = {}
    if isinstance(projection_meta, dict):
        if projection_meta.get("injury_status"):
            projection_data["injury_status"] = projection_meta.get("injury_status")
        factors = projection_meta.get("factors") or {}
        rest_days = projection_meta.get("rest_days")
        if rest_days is not None:
            factors = {**factors, "rest_days": rest_days}
        if factors:
            projection_data["factors"] = factors
    book_line = prop.get("line")
    if book_line:
        try:
            projection_data["comparison"] = compare_projection_to_book_line(
                projection_data["projected_line"],
                book_line,
            )
        except Exception:
            pass
    return projection_data

def is_degen_play(edge_data, odds):
    """Determine if a play qualifies as DEGEN"""
    if not edge_data:
        return False
    
    edge = edge_data.get("edge", 0) or 0
    prob = edge_data.get("prob")
    
    # Check if prob is None or invalid
    if prob is None:
        return False
    
    if edge > 0 and 0.30 <= prob <= 0.50:
        if odds and odds > -400:
            return True
    
    return False

# Sidebar filters
with st.sidebar:
    st.header("FILTERS")
    
    sport = st.selectbox("Sport", ["NBA", "NFL", "MLB", "NHL", "NCAAB", "NCAAF", "Esports"], index=0)
    
    st.divider()
    
    # Prop type filter
    st.subheader("MARKETS")
    prop_types = ["All", "Points", "Rebounds", "Assists", "PRA", "3PM", "Win", "Kills", "Headshots", "First Kills"]
    selected_prop_types = st.multiselect(
        "Select Markets",
        prop_types,
        default=["All"] if "All" in prop_types else []
    )
    
    if "All" in selected_prop_types:
        selected_prop_types = prop_types[1:]
    
    st.divider()
    
    # DEGEN mode toggle
    st.subheader("RISK PROFILE")
    degen_mode = st.checkbox(
        "🔥 DEGEN Mode",
        value=st.session_state.degen_mode,
        help="Higher risk, higher reward plays (30-50% hit rate, positive edge)"
    )
    st.session_state.degen_mode = degen_mode
    
    # +EV only filter
    show_ev_only = st.checkbox("Only +EV Props", value=False)
    
    st.divider()
    
    # Alt lines filter
    st.subheader("LINE SETTINGS")
    hide_alt_lines = st.checkbox(
        "Standard Lines Only",
        value=True,
        help="Only show props with standard lines that most books offer."
    )
    
    # Deduplication filter
    dedupe_props = st.checkbox(
        "Best Odds Only",
        value=True,
        help="Show only the best odds for each player+prop+line combination."
    )
    
    st.divider()
    
    # Projections toggle
    st.subheader("PROJECTIONS")
    show_projections = st.checkbox(
        "Show Model Projections",
        value=True,  # Enabled by default - this is our core feature!
        help="Display our custom line projections based on player performance, matchups, injuries, and other factors."
    )
    
    st.divider()
    
    # Team filter
    st.subheader("TEAMS")
    all_teams = st.checkbox("All Teams", value=True)
    
    # Always load players to get images/metadata
    try:
        players = load_all_players(sport)
    except Exception as e:
        players = []
        st.error(f"Error loading players: {e}")
    
    # Build player image map
    player_image_map = {}
    try:
        for p in players:
            pid = p.get("id")
            if pid:
                # Prefer direct image_url (e.g. for Esports)
                if p.get("image_url"):
                    player_image_map[pid] = p.get("image_url")
                # Fallback to NBA CDN if external_id exists and sport is NBA
                elif p.get("sport") == "NBA" and p.get("external_id"):
                    player_image_map[pid] = f"https://cdn.nba.com/headshots/nba/latest/1040x760/{p.get('external_id')}.png"
    except Exception as e:
        # If image map building fails, continue without images
        pass

    if not all_teams:
        teams = sorted(set(p.get("team") for p in players if p.get("team")))
        selected_teams = st.multiselect("Select Teams", teams)
    else:
        selected_teams = None
    
    st.divider()
    
    # Sort options
    st.subheader("SORTING")
    sort_by = st.selectbox(
        "Sort By",
        ["Edge (Highest)", "Odds (Best)", "Line (Lowest)", "Player Name"],
        index=0
    )

# --- DEMO DATA BANNER ---
try:
    from dashboard.data_loaders import DB_AVAILABLE
    if not DB_AVAILABLE:
        st.info("""
        📊 **DEMO MODE**: Displaying sample data for portfolio demonstration. All features are fully functional.
        
        💡 **For Production Use**: Configure API keys in `.env` file (The Odds API, Supabase, NBA Stats API). 
        See `API_SETUP.md` for setup instructions.
        """)
except:
    pass

# --- INJURY TICKER ---
injuries = load_recent_injuries(sport)
if injuries:
    render_injury_ticker(injuries)

# Title with refresh button
col_title, col_refresh = st.columns([4, 1])
with col_title:
    st.markdown('<h1 style="font-size: 3rem; margin-bottom: 0;">MARKETPLACE</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color: #CCCCCC; font-size: 1.2rem; margin-top: 5px;">Real-time odds, projections, and value analysis</p>', unsafe_allow_html=True)
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(0, 229, 255, 0.1) 0%, rgba(255, 46, 99, 0.1) 100%); 
                border-left: 4px solid #00E5FF; border-radius: 8px; padding: 15px; margin-top: 15px; margin-bottom: 20px;">
        <p style="color: #E0E0E0; font-size: 0.95rem; margin: 0; line-height: 1.6;">
            <strong style="color: #00E5FF;">Live Player Props Feed:</strong> Browse real-time player prop odds with automated edge calculations, 
            custom projections, and AI-powered insights. Filter by sport, market type, team, or value threshold. 
            Each prop card displays edge percentage, odds comparison, and contextual factors.
        </p>
    </div>
    """, unsafe_allow_html=True)

with col_refresh:
    if st.button("🔄 REFRESH", help="Refetch games, odds, and props (latest 48h)"):
        import subprocess
        import os
        import sys

        def run_worker(cmd: list, label: str):
            result = subprocess.run(
                [sys.executable, *cmd],
                cwd=os.getcwd(),
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                st.error(f"{label} failed:\n{result.stderr}")
            return result

        with st.spinner("Refreshing games, odds, and props..."):
            results = []
            results.append(run_worker(["workers/fetch_odds.py"], "fetch_odds"))
            results.append(run_worker(["workers/fetch_esports.py"], "fetch_esports"))
            results.append(run_worker(["workers/fetch_player_prop_odds.py"], "fetch_player_prop_odds"))
            results.append(run_worker(["workers/build_projection_snapshots.py", "--sport", sport, "--hours", "48"], "build_projection_snapshots"))
            results.append(run_worker(["workers/build_prop_feed_snapshots.py", "--sport", sport, "--hours", "48"], "build_prop_feed_snapshots"))

            # Clear cache explicitly
            load_prop_feed_snapshots.clear()
            load_tonight_games.clear()
            load_recent_injuries.clear()
            load_all_players.clear()

            if all(r.returncode == 0 for r in results):
                st.success("Market data refreshed! Reloading...")
                st.rerun()
            else:
                st.warning("Refresh completed with errors. Check logs above.")

# Load data with loading state
with st.spinner("Loading market data..."):
    games = load_tonight_games(sport)
    game_ids = [g["id"] for g in games] if games else []

if not games:
    st.info(f"No games scheduled for {sport} tonight.")
    
    # Check if other sports have games
    other_sports_counts = {}
    for s in ["NBA", "NFL", "MLB", "NHL", "NCAAB", "NCAAF", "CS2", "LoL", "Dota2", "Valorant"]:
        if s == sport: continue
        try:
            # Manual lightweight check
            # We can't use count="exact" easily with supabase-py sometimes without specific setup
            # So we'll just fetch 1 record
            now_check = datetime.now(timezone.utc)
            count_query = (
                supabase.table("games")
                .select("id", count="exact", head=True)
                .eq("sport", s)
                .gte("start_time", (now_check - timedelta(hours=12)).isoformat())
                .lte("start_time", (now_check + timedelta(hours=48)).isoformat())
                .execute()
            )
            if count_query.count and count_query.count > 0:
                other_sports_counts[s] = count_query.count
        except:
            pass
            
    if other_sports_counts:
        msg = "However, there are games in other sports: "
        parts = [f"**{s}** ({c})" for s, c in other_sports_counts.items()]
        st.markdown(msg + ", ".join(parts))
        
    st.stop()

# Load props with loading state
with st.spinner("Analyzing props..."):
    props = load_prop_feed_snapshots(sport, game_ids)
    
    # Show last update time and prop count
    if props:
        latest_prop_time = max((p.get("snapshot_at", "") for p in props if p.get("snapshot_at")), default="")
        if latest_prop_time:
            from datetime import datetime
            try:
                if isinstance(latest_prop_time, str):
                    latest_dt = datetime.fromisoformat(latest_prop_time.replace('Z', '+00:00'))
                else:
                    latest_dt = latest_prop_time
                now = datetime.now(latest_dt.tzinfo) if latest_dt.tzinfo else datetime.now()
                age_hours = (now - latest_dt).total_seconds() / 3600
                if age_hours > 12:
                    st.warning(f"⚠️ Data is {age_hours:.1f} hours old. Refresh recommended.")
            except Exception as e:
                pass

if not props:
    st.info("No player props available. Try refreshing.")
    st.stop()

# Calculate standard lines for each player+prop_type combination
# Standard line = most common line offered by books (the "main" line)
@st.cache_data(ttl=300)
def calculate_standard_lines(props):
    """Calculate the most common (standard) line for each player+prop_type"""
    from collections import Counter
    
    # Group by player_id + prop_type
    line_counts = {}  # (player_id, prop_type) -> Counter of lines
    
    for prop in props:
        player_id = prop.get("player_id")
        prop_type = prop.get("prop_type")
        line = prop.get("line")
        
        if not all([player_id, prop_type, line is not None]):
            continue
        
        key = (player_id, prop_type)
        if key not in line_counts:
            line_counts[key] = Counter()
        line_counts[key][line] += 1
    
    # Get standard lines - include lines that are:
    # 1. The most common line, OR
    # 2. Within 0.5 of the most common line and appear at least 3 times
    standard_lines = {}  # (player_id, prop_type) -> set of acceptable lines
    for key, counter in line_counts.items():
        if counter:
            # Get the most common line and its count
            most_common_line, most_common_count = counter.most_common(1)[0]
            
            # Acceptable lines: the most common line + lines within 0.5 that appear frequently
            acceptable_lines = {most_common_line}
            
            # Include lines within 0.5 of the standard if they appear at least 3 times
            # This handles cases like 7.5 (standard) and 8.0 (common alt)
            for line, count in counter.items():
                if abs(line - most_common_line) <= 0.5 and count >= 3:
                    acceptable_lines.add(line)
            
            standard_lines[key] = acceptable_lines
    
    return standard_lines

# Calculate standard lines if filtering alt lines
standard_lines = {}
if hide_alt_lines:
    standard_lines = calculate_standard_lines(props)

# Deduplicate props if enabled (show only best odds per player+prop+line)
if dedupe_props:
    deduped_props = {}
    for prop in props:
        player_id = prop.get("player_id")
        prop_type = prop.get("prop_type")
        line = prop.get("line")
        
        if not all([player_id, prop_type, line is not None]):
            continue
        
        key = (player_id, prop_type, line)
        edge = prop.get("edge", 0) or 0
        
        # Keep the prop with the highest edge for this player+prop+line combo
        if key not in deduped_props or edge > (deduped_props[key].get("edge", 0) or 0):
            deduped_props[key] = prop
    
    props = list(deduped_props.values())

# Filter and process props using snapshots
game_lookup = {g.get("id"): g for g in games if isinstance(g, dict) and g.get("id")}
filtered_props = []
seen_prop_ids = set()

for prop in props:
    prop_identifier = prop.get("prop_id") or prop.get("id")
    if prop_identifier in seen_prop_ids:
        continue
    seen_prop_ids.add(prop_identifier)

    prop_type_raw = prop.get("prop_type", "")
    
    # USER REQUEST: Remove "Win" props (Team Wins) for Esports entirely
    if sport == "Esports" and prop_type_raw == "win":
        continue

    if prop_type_raw == "pra":
        prop_type_display = "PRA"
    elif prop_type_raw == "threes":
        prop_type_display = "3PM"
    elif prop_type_raw == "win":
        prop_type_display = "Win"
    elif prop_type_raw == "kills":
        prop_type_display = "Kills"
    elif prop_type_raw == "headshots":
        prop_type_display = "Headshots"
    elif prop_type_raw == "first_kills":
        prop_type_display = "First Kills"
    else:
        prop_type_display = prop_type_raw.replace("_", " ").title()
    if selected_prop_types and prop_type_display not in selected_prop_types:
        continue

    metadata = _parse_metadata(prop.get("metadata"))
    player_info = {
        "id": prop.get("player_id"),
        "name": prop.get("player_name") or metadata.get("player_name"),
        "team": prop.get("team"),
        "position": metadata.get("player_position"),
        "sport": prop.get("sport"),
    }
    player_team = player_info.get("team")
    if selected_teams and player_team and player_team not in selected_teams:
        continue

    edge_data = _build_edge_from_snapshot(prop, metadata)
    sparkline_data = metadata.get("sparkline_values")
    if isinstance(sparkline_data, str):
        try:
            sparkline_data = json.loads(sparkline_data)
        except Exception:
            sparkline_data = None
    if isinstance(sparkline_data, list) and len(sparkline_data) < 2:
        sparkline_data = None
    matchup_stats = metadata.get("matchup_stats")
    if isinstance(matchup_stats, str):
        try:
            matchup_stats = json.loads(matchup_stats)
        except Exception:
            matchup_stats = None
    projection_data = _build_projection_from_snapshot(prop, metadata, show_projections)

    if show_ev_only and (not edge_data or edge_data.get("edge", 0) <= 0):
        continue
    best_odds = prop.get("over_price") or prop.get("under_price")
    if degen_mode and not is_degen_play(edge_data, best_odds):
        continue

    if hide_alt_lines or show_ev_only:
        line = prop.get("line")
        player_id = prop.get("player_id")
        prop_type = prop.get("prop_type")
        if player_id and prop_type and line is not None:
            acceptable_lines = standard_lines.get((player_id, prop_type))
            if acceptable_lines is not None:
                if not any(abs(line - acceptable_line) <= 0.5 for acceptable_line in acceptable_lines):
                    continue

    game_info = game_lookup.get(prop.get("game_id"))
    if not game_info:
        opponent = prop.get("opponent")
        if prop.get("is_home"):
            game_info = {"home_team": player_team, "away_team": opponent, "start_time": None}
        else:
            game_info = {"home_team": opponent, "away_team": player_team, "start_time": None}

    filtered_props.append({
        "prop": prop,
        "edge_data": edge_data,
        "sparkline": sparkline_data,
        "matchup_stats": matchup_stats,
        "projection_data": projection_data,
        "player_info": player_info,
        "game_info": game_info,
        "metadata": metadata,
        "prop_identifier": prop_identifier,
        "prop_type_display": prop_type_display,
        "prop_type_raw": prop_type_raw,
    })

# Sort props
if sort_by == "Edge (Highest)":
    filtered_props.sort(key=lambda x: x["edge_data"].get("edge", -999) if x["edge_data"] else -999, reverse=True)
elif sort_by == "Odds (Best)":
    filtered_props.sort(key=lambda x: x["prop"].get("over_price") or x["prop"].get("under_price") or 999, reverse=True)
elif sort_by == "Line (Lowest)":
    filtered_props.sort(key=lambda x: x["prop"].get("line", 999))
elif sort_by == "Player Name":
    filtered_props.sort(key=lambda x: (x["player_info"].get("name") or "").lower())

# Display stats
col1, col2, col3, col4 = st.columns(4)
with col1:
    render_metric_card("Total Props", len(filtered_props))
with col2:
    positive_ev = sum(1 for t in filtered_props if t["edge_data"] and t["edge_data"].get("edge", 0) > 0)
    render_metric_card("+EV Props", positive_ev, color="success")
with col3:
    degen_count = sum(
        1
        for t in filtered_props
        if is_degen_play(t["edge_data"], t["prop"].get("over_price") or t["prop"].get("under_price"))
    )
    render_metric_card("DEGEN Plays", degen_count, color="danger")
with col4:
    render_metric_card("Games Tonight", len(games))

st.markdown("---")

# Display props in grid - NO DUPLICATES
if filtered_props:
    
    # Create columns for grid layout
    num_cols = 3
    cols = st.columns(num_cols)
    
    # Calculate Implied Probabilities Helper
    def get_prob_str(odds):
        if not odds: return ""
        try:
            prob = american_to_prob(odds)
            return f"({prob*100:.0f}%)"
        except:
            return ""

    for idx, prop_data in enumerate(filtered_props):
        try:
            prop = prop_data["prop"]
            edge_data = prop_data["edge_data"]
            sparkline_data = prop_data["sparkline"]
            matchup_stats = prop_data["matchup_stats"]
            projection_data = prop_data["projection_data"]
            player_info = prop_data["player_info"]
            game_info = prop_data["game_info"]
            prop_identifier = prop_data.get("prop_identifier") or prop.get("id")
            
            with cols[idx % num_cols]:
                # Render Card Content as a single HTML block
                game_time = format_game_time(game_info.get("start_time", "")) if game_info.get("start_time") else "TBD"
                
                # Fix team matching - use normalize_team_name to handle different formats
                from utils.team_mapping import normalize_team_name
                player_team = player_info.get("team", "")
                home_team = game_info.get("home_team", "")
                away_team = game_info.get("away_team", "")
                
                # Normalize all team names for comparison
                player_team_norm = normalize_team_name(player_team)
                home_team_norm = normalize_team_name(home_team)
                away_team_norm = normalize_team_name(away_team)
                
                # Determine opponent using normalized names
                if player_team_norm == home_team_norm or player_team == home_team:
                    opponent = away_team
                elif player_team_norm == away_team_norm or player_team == away_team:
                    opponent = home_team
                else:
                    # Fallback: use original logic if normalization doesn't match
                    opponent = game_info.get("away_team") if game_info.get("home_team") == player_info.get("team") else game_info.get("home_team")
                
                team_label = player_info.get("team")
                if sport == "Esports" and player_info.get("sport"):
                    team_label = f"{player_info.get('sport')} • {team_label}"

                # Use stored prop_type_display from filtering
                prop_type_display = prop_data.get("prop_type_display", prop.get("prop_type", "").replace("_", " ").title())
                prop_type_raw = prop_data.get("prop_type_raw", prop.get("prop_type", ""))
                line = prop.get("line")
                line_display = line
                
                # Check if moneyline (shouldn't happen for Esports due to filter, but keep for other sports)
                is_moneyline = prop_type_raw == "win"

                side = edge_data.get("side", "over").upper() if edge_data else "OVER"
                
                # Build complete card HTML - FLATTENED to avoid indentation issues
                # Escape HTML entities for dynamic content
                prop_type_display_escaped = html.escape(str(prop_type_display))
                line_display_escaped = html.escape(str(line_display))
                
                # Decode HTML entities first, then escape for safe display
                from dashboard.ui_components import decode_html_entities
                player_name_clean = decode_html_entities(player_info.get("name", "Unknown"))
                player_name_escaped = html.escape(str(player_name_clean))
                team_label_escaped = html.escape(str(team_label))
                opponent_escaped = html.escape(str(opponent))
                game_time_escaped = html.escape(str(game_time))
                
                # Get image URL (safely handle None or missing player_id)
                player_id = player_info.get("id")
                player_img_url = player_image_map.get(player_id) if player_id else None
                
                card_html = f"""<div class="prop-card">
{render_prop_card_header(player_name_escaped, team_label_escaped, opponent_escaped, game_time_escaped, image_url=player_img_url)}
<div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 10px;">
<div style="font-size: 0.9rem; color: #888; text-transform: uppercase;">{prop_type_display_escaped}</div>
<div style="font-size: 1.5rem; font-weight: 800; color: #FFF;">{line_display_escaped}</div>
</div>
{render_edge_meter(edge_data.get("edge", 0) * 100) if edge_data else ""}
</div>"""
                
                st.markdown(card_html, unsafe_allow_html=True)
                
                # Actions (Buttons) - Rendered below the card visual
                over_price = prop.get("over_price")
                under_price = prop.get("under_price")
                
                col_act1, col_act2, col_act3 = st.columns([1, 1, 1])
                
            with col_act1:
                if st.button("Insights", key=f"insights_{prop_identifier}_{idx}", use_container_width=True):
                    st.session_state.selected_player_id = player_info.get("id")
                    st.session_state.selected_player_name = player_info.get("name")
                    st.session_state.selected_player_team = player_info.get("team")
                    st.session_state.selected_game_id = game_info.get("id")
                    st.switch_page("player_insights.py")
            
            with col_act2:
                # Add Over / Bet ML
                lbl_over = f"Over {format_odds(over_price)}"
                if is_moneyline:
                    lbl_over = f"{format_odds(over_price)}" # Just Odds
                
                # REMOVE HELP AND EMOJIS TO PREVENT SAFARI CRASHES
                if st.button(lbl_over, key=f"add_over_{prop_identifier}_{idx}", use_container_width=True):
                    leg = {
                        "prop_id": prop.get("prop_id") or prop_identifier,
                        "player_name": player_info.get("name", "Unknown"),
                        "prop_type": "Moneyline" if is_moneyline else prop.get("prop_type", ""),
                        "line": "ML" if is_moneyline else prop.get("line"),
                        "side": "Win" if is_moneyline else "over",
                        "odds": over_price,
                        "book": prop.get("book", "Unknown"),
                        "edge": edge_data.get("edge") if edge_data and edge_data.get("side")=="over" else None,
                        "dfs_line": prop.get("dfs_line"),
                    }
                    st.session_state.slip_legs.append(leg)
                    st.success("Added")
                    st.rerun()
            
            with col_act3:
                # Add Under (Hide for Moneyline)
                if is_moneyline:
                    st.write("") # Spacer
                else:
                    lbl_under = f"Under {format_odds(under_price)}"
                    # REMOVE HELP AND EMOJIS TO PREVENT SAFARI CRASHES
                    if st.button(lbl_under, key=f"add_under_{prop_identifier}_{idx}", use_container_width=True):
                        leg = {
                            "prop_id": prop.get("prop_id") or prop_identifier,
                            "player_name": player_info.get("name", "Unknown"),
                            "prop_type": prop.get("prop_type", ""),
                            "line": prop.get("line"),
                            "side": "under",
                            "odds": under_price,
                            "book": prop.get("book", "Unknown"),
                            "edge": edge_data.get("edge") if edge_data and edge_data.get("side")=="under" else None,
                            "dfs_line": prop.get("dfs_line"),
                        }
                        st.session_state.slip_legs.append(leg)
                        st.success("Added Under")
                        st.rerun()
        except Exception as e:
            # Log error but continue rendering other props
            st.error(f"Error rendering prop {idx}: {str(e)}")
            continue

else:
    st.info("No props match your filters.")

# Enhanced Slip sidebar
with st.sidebar:
    if st.session_state.slip_legs:
        st.divider()
        render_bet_slip(st.session_state.slip_legs)
