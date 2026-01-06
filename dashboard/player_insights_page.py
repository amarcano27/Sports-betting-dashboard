"""
Player Insights Page - The "War Room" for deep analysis
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from services.db import supabase
from services.context_analysis import get_game_context
from dashboard.ui_components import render_metric_card, format_game_time
from dashboard.player_props import calculate_hitrate, create_prop_chart

def render_player_insights_page():
    # Check if a player/prop is selected in session state
    if "selected_insight_prop" not in st.session_state:
        st.info("Please select a player prop from the Home page to view insights.")
        if st.button("← Back to Home"):
            st.switch_page("dashboard/home_page.py")
        st.stop()
    
    prop_data = st.session_state.selected_insight_prop
    prop = prop_data.get("prop", {})
    player_info = prop_data.get("player_info", {})
    game_info = prop_data.get("game_info", {})
    edge_data = prop_data.get("edge_data", {})
    projection_data = prop_data.get("projection_data", {})
    
    player_name = player_info.get("name", "Unknown Player")
    player_id = player_info.get("id")
    team = player_info.get("team", "N/A")
    # Use normalize_team_name for proper team matching
    from utils.team_mapping import normalize_team_name
    team_norm = normalize_team_name(team)
    home_team_norm = normalize_team_name(game_info.get("home_team", ""))
    away_team_norm = normalize_team_name(game_info.get("away_team", ""))
    
    if team_norm == home_team_norm or team == game_info.get("home_team"):
        opponent = game_info.get("away_team")
    elif team_norm == away_team_norm or team == game_info.get("away_team"):
        opponent = game_info.get("home_team")
    else:
        # Fallback
        opponent = game_info.get("away_team") if game_info.get("home_team") == team else game_info.get("home_team")
    
    # Get player image
    player_id = player_info.get("id")
    image_url = None
    try:
        from dashboard.demo_data_loader import get_demo_players
        demo_players = get_demo_players("NBA")
        player_data = next((p for p in demo_players if p.get("id") == player_id), None)
        if player_data:
            external_id = player_data.get("external_id")
            if external_id and player_data.get("sport") == "NBA":
                image_url = f"https://cdn.nba.com/headshots/nba/latest/1040x760/{external_id}.png"
    except:
        pass
    
    # --- HEADER SECTION ---
    if image_url:
        avatar_html = f'<img src="{image_url}" style="width: 80px; height: 80px; border-radius: 50%; object-fit: cover; border: 3px solid #333;" onerror="this.style.display=\'none\'; this.nextElementSibling.style.display=\'flex\';">'
        fallback_html = f'<div style="width: 80px; height: 80px; background: #222; border-radius: 50%; display: none; align-items: center; justify-content: center; font-size: 2rem; font-weight: bold; color: #666;">{player_name[0]}</div>'
        avatar = f'{avatar_html}{fallback_html}'
    else:
        avatar = f'<div style="width: 80px; height: 80px; background: #222; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 2rem; font-weight: bold; color: #666;">{player_name[0]}</div>'
    
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 20px; margin-bottom: 30px;">
        {avatar}
        <div>
            <h1 style="margin: 0; font-size: 3rem;">{player_name}</h1>
            <div style="color: #888; font-size: 1.2rem;">{team} vs {opponent} • {format_game_time(game_info.get('start_time', ''))}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # --- MAIN PROP ANALYSIS ---
    prop_type = prop.get("prop_type", "").replace("_", " ").title()
    line = prop.get("line")
    
    st.markdown(f"### 🎯 Analysis: {prop_type} {line}")
    
    # Context Analysis
    game_id = prop.get("game_id")
    if game_id:
        context = get_game_context(player_id, game_id, prop.get("prop_type"))
        if context and context.get("context_summary") != "No significant context":
            st.info(f"⚡ **Context Alert**: {context['context_summary']}")
            
            usage_pred = context.get("usage_prediction")
            if usage_pred and usage_pred.get("adjustment_pct", 0) != 0:
                with st.expander("📊 Usage Impact Analysis", expanded=True):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Baseline Avg", f"{usage_pred['baseline_avg']:.1f}")
                    c2.metric("Adjusted Proj", f"{usage_pred['adjusted_avg']:.1f}", delta=f"{usage_pred['adjustment_pct']:+.1f}%")
                    c3.write(f"**Reasoning**: {usage_pred.get('reasoning')}")

    # Metrics Grid
    col1, col2, col3, col4 = st.columns(4)
    
    # 1. Projection
    with col1:
        if projection_data and projection_data.get("projected_line"):
            proj = projection_data["projected_line"]
            diff = proj - line
            color = "success" if abs(diff) > 1 else "neutral"
            render_metric_card("Our Projection", f"{proj:.1f}", delta=f"{diff:+.1f} vs Line", color=color)
        else:
            render_metric_card("Our Projection", "N/A")
            
    # 2. Last 10 Hit Rate
    with col2:
        # Fetch stats for hit rate
        try:
            stats = (
                supabase.table("player_game_stats")
                .select("*")
                .eq("player_id", player_id)
                .order("date", desc=True)
                .limit(20)
                .execute()
                .data
            )
        except Exception:
            # Fallback: no stats in demo mode
            stats = []
        
        if stats:
            hit_data = calculate_hitrate(
                [{"date": s["date"], prop.get("prop_type"): s.get(prop.get("prop_type"), 0)} for s in stats],
                prop.get("prop_type"),
                line
            )
            l10 = hit_data["hitrates"].get("L10", 0)
            color = "success" if l10 > 60 else "danger" if l10 < 40 else "neutral"
            render_metric_card("L10 Hit Rate", f"{l10:.0f}%", color=color)
        else:
            render_metric_card("L10 Hit Rate", "N/A")

    # 3. Edge
    with col3:
        edge = edge_data.get("edge", 0) * 100
        color = "success" if edge > 2 else "neutral"
        render_metric_card("Edge", f"{edge:+.1f}%", color=color)

    # 4. Best Odds
    with col4:
        odds = edge_data.get("odds") or prop.get("over_price") or prop.get("under_price")
        render_metric_card("Best Odds", f"{odds:+d}" if odds else "N/A")

    st.markdown("---")

    # --- CHARTS & LOGS ---
    c_chart, c_logs = st.columns([2, 1])
    
    with c_chart:
        st.subheader("📈 Performance Trend")
        if stats:
            chart_data = [{"date": s["date"], prop.get("prop_type"): s.get(prop.get("prop_type"), 0)} for s in stats]
            fig = create_prop_chart(chart_data, prop.get("prop_type"), line, title=f"Last 20 Games: {prop_type}")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No historical data available for chart.")

    with c_logs:
        st.subheader("📝 Game Log")
        if stats:
            log_data = []
            for s in stats[:10]:
                val = s.get(prop.get("prop_type"), 0)
                res = "✅" if val > line else "❌" if val < line else "➖"
                log_data.append({
                    "Date": s["date"],
                    "Opp": s.get("opponent", "N/A"),
                    "Val": val,
                    "Res": res
                })
            st.dataframe(pd.DataFrame(log_data), hide_index=True, use_container_width=True)

    # --- OTHER PROPS FOR PLAYER ---
    st.markdown("---")
    st.subheader(f"🧩 Other Props for {player_name}")
    
    # Fetch other props
    try:
        other_props = (
            supabase.table("player_prop_odds")
            .select("*")
            .eq("player_id", player_id)
            .eq("game_id", game_id)
            .neq("prop_type", prop.get("prop_type"))
            .execute()
            .data
        )
    except Exception:
        # Fallback to demo data
        from dashboard.demo_data_loader import get_demo_props
        all_props = get_demo_props("NBA", [game_id] if game_id else None)
        other_props = [p for p in all_props if p.get("player_id") == player_id and p.get("prop_type") != prop.get("prop_type")]
    
    if other_props:
        # Dedupe by prop type
        unique_props = {}
        for p in other_props:
            pt = p["prop_type"]
            if pt not in unique_props:
                unique_props[pt] = p
        
        cols = st.columns(4)
        for i, (pt, p) in enumerate(unique_props.items()):
            with cols[i % 4]:
                pt_display = pt.replace("_", " ").title()
                st.markdown(f"""
                <div style="background: #1A1A1A; padding: 15px; border-radius: 8px; border: 1px solid #333;">
                    <div style="color: #888; font-size: 0.8rem;">{pt_display}</div>
                    <div style="font-size: 1.5rem; font-weight: bold;">{p['line']}</div>
                    <div style="font-size: 0.9rem;">Over: {p.get('over_price')}</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No other props found for this game.")

    # Back button
    st.markdown("---")
    if st.button("← Back to Marketplace", use_container_width=True):
        st.switch_page("dashboard/home_page.py")

if __name__ == "__main__":
    render_player_insights_page()

