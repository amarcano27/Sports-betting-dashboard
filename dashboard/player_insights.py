"""
Player Insights & War Room
Detailed analysis, charts, and prop marketplace for a specific player.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import html
from services.db import supabase
from services.context_analysis import get_game_context
from dashboard.ui_components import (
    render_metric_card, render_edge_meter, format_game_time, render_context_badge, render_hit_rate_card, render_bet_slip
)
from dashboard.player_props import calculate_hitrate
from dashboard.charts import create_prop_chart

def render_player_insights_page():
    # Check if a player is selected
    if "selected_player_id" not in st.session_state:
        st.warning("No player selected. Please select a player from the Home or Player Props page.")
        if st.button("Go Home"):
            st.switch_page("home_page.py")
        return

    player_id = st.session_state.selected_player_id
    player_name = st.session_state.get("selected_player_name", "Unknown Player")
    team = st.session_state.get("selected_player_team", "N/A")
    game_id = st.session_state.get("selected_game_id")
    
    # Load player data with fallback to demo data
    try:
        player_data = supabase.table("players").select("*").eq("id", player_id).single().execute().data
    except Exception as e:
        st.warning("⚠️ Database unavailable. Using demo data.")
        # Try to get from demo data
        from dashboard.demo_data_loader import get_demo_players
        demo_players = get_demo_players("NBA")
        player_data = next((p for p in demo_players if p.get("id") == player_id), None)
        if not player_data:
            st.error("Player not found in demo data.")
            return
    
    if not player_data:
        st.error("Player not found.")
        return
        
    is_esports = player_data.get("sport") in ["CS2", "LoL", "Dota2", "Valorant"]
    
    # Load game data if not provided
    opponent = "Unknown"
    is_home = False
    game_time = "TBD"

    if not game_id:
        # Try to find the next game for this player's team
        try:
            next_game = supabase.table("games").select("*").or_(f"home_team.eq.{team},away_team.eq.{team}").gte("start_time", datetime.now().isoformat()).order("start_time").limit(1).execute().data
            if next_game:
                game_id = next_game[0]["id"]
                game_data = next_game[0]
            else:
                game_data = None
        except Exception:
            # Fallback to demo data
            from dashboard.demo_data_loader import get_demo_games
            demo_games = get_demo_games("NBA")
            game_data = next((g for g in demo_games if team in [g.get("home_team"), g.get("away_team")]), None)
            if game_data:
                game_id = game_data.get("id")
    else:
        try:
            game_data = supabase.table("games").select("*").eq("id", game_id).single().execute().data
        except Exception:
            # Fallback to demo data
            from dashboard.demo_data_loader import get_demo_games
            demo_games = get_demo_games("NBA")
            game_data = next((g for g in demo_games if g.get("id") == game_id), None)

    if game_data:
        opponent = game_data["away_team"] if game_data["home_team"] == team else game_data["home_team"]
        is_home = game_data["home_team"] == team
        game_time = format_game_time(game_data["start_time"])

    # Construct image URL - check both direct image_url and external_id
    image_url = player_data.get("image_url")
    if not image_url:
        external_id = player_data.get("external_id")
        if external_id and player_data.get("sport") == "NBA":
            image_url = f"https://cdn.nba.com/headshots/nba/latest/1040x760/{external_id}.png"

    # --- HERO SECTION ---
    if image_url:
        img_html = f'<img src="{image_url}" style="width: 120px; height: 120px; border-radius: 50%; object-fit: cover; border: 4px solid #333; display: block;" onerror="this.style.display=\'none\'; this.nextElementSibling.style.display=\'flex\';">'
        fallback_html = f'<div style="width: 120px; height: 120px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 50%; display: none; align-items: center; justify-content: center; font-size: 48px; font-weight: bold; color: white;">{player_name[0]}</div>'
        avatar_html = f'{img_html}{fallback_html}'
    else:
        avatar_html = f'<div style="width: 120px; height: 120px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 48px; font-weight: bold; color: white;">{player_name[0]}</div>'

    # Decode HTML entities first, then escape for safe display
    from dashboard.ui_components import decode_html_entities
    player_name_decoded = decode_html_entities(player_name)
    player_name_escaped = html.escape(str(player_name_decoded))
    team_escaped = html.escape(str(team))
    position_escaped = html.escape(str(player_data.get('position', 'N/A')))
    
    header_html = f"""<div style="display: flex; align-items: center; gap: 30px; margin-bottom: 40px;">
{avatar_html}
<div>
<h1 style="margin: 0; font-size: 3.5rem; font-weight: 800;">{player_name_escaped}</h1>
<p style="margin: 0; color: #888; font-size: 1.5rem;">{team_escaped} • {position_escaped}</p>
</div>
</div>"""
    st.markdown(header_html, unsafe_allow_html=True)

    if game_data:
        # Escape HTML entities
        opponent_escaped = html.escape(str(opponent))
        game_time_escaped = html.escape(str(game_time))
        home_away = html.escape('Home' if is_home else 'Away')
        
        matchup_html = f"""<div style="background: rgba(30, 41, 59, 0.5); border: 1px solid #475569; border-radius: 12px; padding: 20px; margin-bottom: 30px;">
<div style="display: flex; justify-content: space-between; align-items: center;">
<div>
<div style="color: #888; font-size: 0.9rem; text-transform: uppercase;">Matchup</div>
<div style="font-size: 1.5rem; font-weight: bold;">vs {opponent_escaped} <span style="font-size: 1rem; color: #888;">({home_away})</span></div>
</div>
<div style="text-align: right;">
<div style="color: #888; font-size: 0.9rem; text-transform: uppercase;">Tip-off</div>
<div style="font-size: 1.5rem; font-weight: bold;">{game_time_escaped}</div>
</div>
</div>
</div>"""
        st.markdown(matchup_html, unsafe_allow_html=True)

        # --- PROP SELECTION ---
        if is_esports:
             prop_options = ["Kills", "Assists", "Deaths", "Headshots", "First Kills"]
        else:
             prop_options = ["Points", "Rebounds", "Assists", "Threes", "PRA"]
             
        selected_prop_display = st.selectbox("Select Analysis Metric", prop_options, index=0)
        active_prop_type = selected_prop_display.lower()
        if active_prop_type == "threes":
            active_prop_type = "threes" 
        if active_prop_type == "kills": active_prop_type = "kills"
        # Map deaths to rebounds for context if needed
        
        # --- FETCH PROPS EARLY for Context ---
        try:
            props = supabase.table("player_prop_odds").select("*").eq("player_id", player_id).eq("game_id", game_id).execute().data
        except Exception:
            # Fallback to demo data
            from dashboard.demo_data_loader import get_demo_props
            all_props = get_demo_props("NBA", [game_id] if game_id else None)
            props = [p for p in all_props if p.get("player_id") == player_id]
        
        primary_line = None
        db_prop_type = active_prop_type
        if active_prop_type == "3pm": db_prop_type = "threes"
        if is_esports and active_prop_type == "kills": db_prop_type = "points"
        if is_esports and active_prop_type == "deaths": db_prop_type = "rebounds"
        if is_esports and active_prop_type == "assists": db_prop_type = "assists"
        if is_esports and active_prop_type == "headshots": db_prop_type = "headshots"
        if is_esports and active_prop_type == "first kills": db_prop_type = "first_kills"

        if props:
            target_type = active_prop_type
            if active_prop_type == "first kills": target_type = "first_kills"
            
            relevant_props = [
                p for p in props 
                if p["prop_type"] == db_prop_type 
                or p["prop_type"] == target_type
                or (p["prop_type"] == "kills" and active_prop_type == "kills")
            ]
            
            if relevant_props:
                from collections import Counter
                lines = [p["line"] for p in relevant_props if p.get("line") is not None]
                if lines:
                    primary_line = Counter(lines).most_common(1)[0][0]

        # --- CONTEXT ANALYSIS ---
        # Pass db_prop_type (e.g. "points") to context analysis because it queries stats table
        context = get_game_context(player_id, game_id, db_prop_type, line=primary_line)
        
        if context:
            selected_prop_display_escaped = html.escape(str(selected_prop_display))
            st.markdown(f"### 🧠 AI Analysis ({selected_prop_display_escaped})")
            
            # Summary Badge
            if context.get("context_summary") != "No significant context":
                st.info(context["context_summary"])
            
            # Usage Prediction
            if context.get("usage_prediction"):
                usage = context["usage_prediction"]
                if usage.get("adjustment_pct", 0) != 0:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        render_metric_card("Usage Impact", f"{usage['adjustment_pct']:+.1f}%", color="success" if usage['adjustment_pct'] > 0 else "danger")
                    with col2:
                        render_metric_card("Confidence", usage['confidence'].upper())
                    with col3:
                        st.caption(f"**Reasoning:** {usage['reasoning']}")
            
            # Matchup History & Splits
            col_matchup, col_splits = st.columns(2)
            
            with col_matchup:
                if context.get("matchup_history"):
                    opponent_escaped = html.escape(str(opponent))
                    st.markdown(f"#### 🆚 vs {opponent_escaped}")
                    history = context["matchup_history"]
                    h_df = pd.DataFrame(history)
                    # Show key stats
                    cols_to_show = ["date", "points", "rebounds", "assists"]
                    cols_to_show = [c for c in cols_to_show if c in h_df.columns]
                    st.dataframe(h_df[cols_to_show].head(5), use_container_width=True, hide_index=True)
                else:
                    st.info(f"No recent games vs {opponent}")

            with col_splits:
                if context.get("splits"):
                    splits = context["splits"]
                    selected_prop_display_escaped = html.escape(str(selected_prop_display))
                    st.markdown(f"#### 🏠 Home/Away ({selected_prop_display_escaped})")
                    
                    split_cols = st.columns(2)
                    with split_cols[0]:
                        render_metric_card("Home", splits["home"]["avg"], f"{splits['home']['games']} gms")
                    with split_cols[1]:
                        render_metric_card("Away", splits["away"]["avg"], f"{splits['away']['games']} gms")

            st.markdown("---")

    # --- PROP MARKETPLACE ---
    st.markdown("### 🎯 Available Props")
    
    # Fetch historical stats (up to 50 games for deep analysis)
    try:
        stats = supabase.table("player_game_stats").select("*").eq("player_id", player_id).order("date", desc=True).limit(50).execute().data
    except Exception:
        # Fallback: return empty stats for demo mode
        stats = []
    
    if stats and is_esports:
        for s in stats:
            s["kills"] = s.get("points")
            s["deaths"] = s.get("rebounds")

    if props:
        # Group by prop type
        props_by_type = {}
        for p in props:
            pt = p["prop_type"]
            if pt not in props_by_type:
                props_by_type[pt] = []
            props_by_type[pt].append(p)
            
        # Create tabs for prop types
        tabs = st.tabs([pt.replace("_", " ").title() for pt in props_by_type.keys()])
        
        for i, (pt, p_list) in enumerate(props_by_type.items()):
            with tabs[i]:
                # Sort by line
                p_list.sort(key=lambda x: x["line"])
                
                # Display best lines
                best_lines = {} # line -> {over: price, under: price}
                for p in p_list:
                    line = p["line"]
                    if line not in best_lines:
                        best_lines[line] = {"over": -9999, "under": -9999, "over_book": None, "under_book": None}
                    
                    if p["over_price"] and p["over_price"] > best_lines[line]["over"]:
                        best_lines[line]["over"] = p["over_price"]
                        best_lines[line]["over_book"] = p["book"]
                    if p["under_price"] and p["under_price"] > best_lines[line]["under"]:
                        best_lines[line]["under"] = p["under_price"]
                        best_lines[line]["under_book"] = p["book"]

                # Render grid
                cols = st.columns(3)
                for idx, (line, odds) in enumerate(best_lines.items()):
                    with cols[idx % 3]:
                        # High contrast card design
                        st.markdown(f"""<div style="background: #141414; border-radius: 12px; padding: 20px; border: 1px solid #333; margin-bottom: 15px;">
<div style="text-align: center; font-size: 1.8rem; font-weight: 900; color: #FFF; margin-bottom: 15px;">{line}</div>
<div style="display: flex; gap: 15px;">
<div style="flex: 1; background: rgba(0, 229, 255, 0.1); border: 1px solid #00E5FF; border-radius: 8px; padding: 10px; text-align: center;">
<div style="font-size: 0.9rem; font-weight: bold; color: #00E5FF; margin-bottom: 4px;">OVER</div>
<div style="font-size: 1.2rem; font-weight: 900; color: #FFF;">{odds['over']}</div>
<div style="font-size: 0.8rem; color: #CCC; margin-top: 4px;">{odds['over_book']}</div>
</div>
<div style="flex: 1; background: rgba(255, 46, 99, 0.1); border: 1px solid #FF2E63; border-radius: 8px; padding: 10px; text-align: center;">
<div style="font-size: 0.9rem; font-weight: bold; color: #FF2E63; margin-bottom: 4px;">UNDER</div>
<div style="font-size: 1.2rem; font-weight: 900; color: #FFF;">{odds['under']}</div>
<div style="font-size: 0.8rem; color: #CCC; margin-top: 4px;">{odds['under_book']}</div>
</div>
</div>
</div>""", unsafe_allow_html=True)
                        
                # --- ANALYSIS SECTION (Full Width Below Grid) ---
                if best_lines and stats:
                    st.markdown("---")
                    # Pick the "middle" line or first line for analysis (typically the most balanced one)
                    # For simplicity, pick the first one
                    analysis_line = list(best_lines.keys())[0]
                    
                    analysis_line_escaped = html.escape(str(analysis_line))
                    st.markdown(f"### 📊 Deep Dive: {analysis_line_escaped}")
                    
                    # Calculate hit rates for this line
                    hit_stats = calculate_hitrate(stats, pt, analysis_line)
                    hitrates = hit_stats.get("hitrates", {})
                    averages = hit_stats.get("averages", {})
                    
                    # Hit Rates
                    hr_cols = st.columns(4)
                    with hr_cols[0]:
                        render_hit_rate_card("L5", f"{hitrates.get('L5', 0)}%", f"Avg: {averages.get('L5', 0)}", color="success" if hitrates.get('L5', 0) > 50 else "danger")
                    with hr_cols[1]:
                        render_hit_rate_card("L10", f"{hitrates.get('L10', 0)}%", f"Avg: {averages.get('L10', 0)}", color="success" if hitrates.get('L10', 0) > 50 else "danger")
                    with hr_cols[2]:
                        render_hit_rate_card("L20", f"{hitrates.get('L20', 0)}%", f"Avg: {averages.get('L20', 0)}", color="success" if hitrates.get('L20', 0) > 50 else "danger")
                    with hr_cols[3]:
                        render_hit_rate_card("Season", f"{hitrates.get('Season', 0)}%", f"Avg: {averages.get('Season', 0)}", color="success" if hitrates.get('Season', 0) > 50 else "danger")
                    
                    # Chart
                    st.markdown("#### 📉 Performance Trend")
                    chart_data = [{"date": s["date"], pt: s.get(pt, 0), "opponent": s.get("opponent"), "home": s.get("home", True)} for s in stats[:20]]
                    fig = create_prop_chart(chart_data, pt, analysis_line, title=f"Last 20 Games: {pt.replace('_', ' ').title()}")
                    st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No props available for this game yet.")

    # --- GAME LOG ---
    st.markdown("### 📅 Recent Game Log")
    
    if is_esports:
        col_fetch1, col_fetch2 = st.columns(2)
        with col_fetch1:
             if st.button("🔄 Fetch Real Stats (PandaScore API)", help="Fetches last 10 matches from PandaScore. Safe & Fast."):
                import subprocess
                import sys
                with st.spinner("Fetching history from PandaScore..."):
                    try:
                        # Only pass player_id (PandaScore ID)
                        cmd = [sys.executable, "workers/fetch_player_history.py", "--player_id", str(player_data.get("external_id"))]
                        res = subprocess.run(cmd, capture_output=True, text=True)
                        if res.returncode == 0:
                            st.success("Stats fetched! Reloading...")
                            st.rerun()
                        else:
                            st.error(f"Error: {res.stderr}")
                    except Exception as e:
                        st.error(f"Failed to run worker: {e}")

        with col_fetch2:
             if st.button("🌍 Fetch from HLTV (Scraper)", help="Scrapes HLTV.org directly using Chrome. Use sparingly to avoid IP bans."):
                import subprocess
                import sys
                with st.spinner("Scraping HLTV (this may take 10-20s)..."):
                    try:
                        # Pass player name and UUID
                        cmd = [sys.executable, "workers/fetch_hltv_stats.py", "--player_name", player_name, "--player_id", player_id]
                        res = subprocess.run(cmd, capture_output=True, text=True)
                        if res.returncode == 0:
                            st.success("Scraped HLTV data! Reloading...")
                            st.rerun()
                        else:
                            st.error(f"Scraper Error: {res.stderr}")
                    except Exception as e:
                        st.error(f"Failed to run scraper: {e}")

        if not stats:
            st.info("📊 **Automatic Stats Generation**: Realistic match statistics are automatically generated when you refresh the Marketplace. These stats are based on actual prop lines and CS2 performance patterns, providing accurate analysis for charts and hit rates.")
        else:
            st.caption(f"✓ {len(stats)} matches loaded (Mix of Real & Simulated)")

    if stats:
        df = pd.DataFrame(stats)
        
        if is_esports:
            cols_to_show = ["date", "opponent", "kills", "deaths", "assists"]
        else:
            cols_to_show = ["date", "opponent", "minutes_played", "points", "rebounds", "assists", "threes", "steals", "blocks", "turnovers"]
            
        # Filter cols that exist
        cols_to_show = [c for c in cols_to_show if c in df.columns]
        st.dataframe(df[cols_to_show], use_container_width=True, hide_index=True)
    else:
        st.info("No historical stats available.")

    # --- SIDEBAR SLIP ---
    with st.sidebar:
        if st.session_state.get("slip_legs"):
            st.divider()
            render_bet_slip(st.session_state.slip_legs)

# Always render when page is loaded (for Streamlit navigation)
render_player_insights_page()
