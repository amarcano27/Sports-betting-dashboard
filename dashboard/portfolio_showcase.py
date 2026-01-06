"""
E-Portfolio Showcase Page
Highlights the capabilities and features of the Sports Betting Analytics Platform
"""
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
from dashboard.ui_components import render_metric_card, format_game_time
from dashboard.data_loaders import load_tonight_games, load_prop_feed_snapshots

# Page config
st.set_page_config(
    page_title="Portfolio Showcase - Sports Betting Analytics",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Hero Section
st.markdown("""
<div style="text-align: center; padding: 60px 20px; background: linear-gradient(135deg, #0A0A0A 0%, #1a1a2e 100%); border-radius: 20px; margin-bottom: 40px; position: relative; overflow: hidden;">
    <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: radial-gradient(circle at 50% 50%, rgba(0, 229, 255, 0.1) 0%, transparent 70%);"></div>
    <div style="position: relative; z-index: 1;">
        <h1 style="font-size: 4rem; font-weight: 800; background: linear-gradient(45deg, #00E5FF, #FFFFFF); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 20px;">
            Sports Betting Analytics Platform
        </h1>
        <p style="font-size: 1.5rem; color: #E0E0E0; max-width: 800px; margin: 0 auto;">
            A comprehensive data-driven platform for real-time odds analysis, player projections, and value betting opportunities
        </p>
    </div>
</div>
""", unsafe_allow_html=True)

# API Setup Notice
st.markdown("""
<div style="background: linear-gradient(135deg, rgba(0, 229, 255, 0.15) 0%, rgba(138, 43, 226, 0.15) 100%); 
            border: 2px solid rgba(0, 229, 255, 0.3); border-radius: 16px; padding: 25px; margin-bottom: 30px;">
    <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 15px;">
        <div style="font-size: 2.5rem;">🔑</div>
        <div>
            <h3 style="color: #00E5FF; margin: 0; font-size: 1.5rem;">API Integration & Setup</h3>
            <p style="color: #E0E0E0; margin: 5px 0 0 0; font-size: 1rem;">
                This platform is fully integrated with live sports betting APIs and requires API keys for full functionality.
            </p>
        </div>
    </div>
    <div style="background: rgba(0, 0, 0, 0.3); border-radius: 12px; padding: 20px; margin-top: 15px;">
        <h4 style="color: #FFFFFF; margin-top: 0;">📋 Required API Keys:</h4>
        <ul style="color: #E0E0E0; line-height: 1.8; margin: 10px 0;">
            <li><strong>The Odds API</strong> - Real-time odds aggregation from multiple sportsbooks</li>
            <li><strong>Supabase</strong> - PostgreSQL database for data storage and management</li>
            <li><strong>NBA Stats API</strong> - Player statistics and historical performance data</li>
            <li><strong>PandaScore API</strong> - Esports data (CS2, LoL, Dota2, Valorant)</li>
        </ul>
        <div style="background: rgba(255, 255, 255, 0.1); border-left: 4px solid #00E5FF; padding: 15px; margin-top: 15px; border-radius: 8px;">
            <p style="color: #FFFFFF; margin: 0; font-weight: 600;">💡 Note:</p>
            <p style="color: #E0E0E0; margin: 5px 0 0 0;">
                The platform includes a <strong>demo mode</strong> that works without API keys, showcasing all features with sample data. 
                For production use, configure your API keys in the <code style="background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 4px;">.env</code> file.
            </p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Key Capabilities Section
st.markdown("## 🚀 Core Capabilities")

capabilities = [
    {
        "icon": "📊",
        "title": "Real-Time Odds Aggregation",
        "description": "Aggregates odds from multiple sportsbooks in real-time via The Odds API, providing comprehensive market coverage across NBA, NFL, MLB, NHL, NCAAB, NCAAF, and Esports (CS2, LoL, Dota2, Valorant).",
        "features": ["Multi-book odds comparison", "Line shopping optimization", "Live odds updates", "Historical odds tracking", "API Integration"]
    },
    {
        "icon": "🎯",
        "title": "Advanced Player Projections",
        "description": "Custom-built projection models that analyze player performance, matchups, injuries, rest days, and historical trends to predict player prop outcomes.",
        "features": ["Machine learning models", "Injury impact analysis", "Matchup-based adjustments", "Confidence scoring"]
    },
    {
        "icon": "💰",
        "title": "Expected Value (EV) Analysis",
        "description": "Calculates expected value for every bet by comparing book odds against our proprietary probability models, identifying positive EV opportunities.",
        "features": ["Automated EV calculation", "Edge identification", "Value bet filtering", "Risk-adjusted recommendations"]
    },
    {
        "icon": "🤖",
        "title": "AI-Powered Insights",
        "description": "Leverages AI to analyze game context, player trends, and betting patterns to provide actionable insights and recommendations.",
        "features": ["Context-aware analysis", "Trend identification", "Smart parlay suggestions", "Risk profile matching"]
    },
    {
        "icon": "📈",
        "title": "Data Visualization & Analytics",
        "description": "Interactive charts and visualizations showing player trends, hit rates, edge distributions, and market movements over time.",
        "features": ["Interactive Plotly charts", "Performance tracking", "Trend analysis", "Comparative visualizations"]
    },
    {
        "icon": "⚡",
        "title": "Automated Data Pipeline",
        "description": "Robust ETL pipeline that continuously fetches, processes, and stores data from multiple APIs and sources, ensuring data freshness.",
        "features": ["Scheduled data updates", "Error handling & retries", "Data validation", "Snapshot management"]
    }
]

# Display capabilities in a grid
cols = st.columns(3)
for idx, cap in enumerate(capabilities):
    with cols[idx % 3]:
        st.markdown(f"""
        <div style="background: #141414; border: 1px solid #2A2A2A; border-radius: 12px; padding: 25px; margin-bottom: 20px; height: 100%; transition: all 0.3s;">
            <div style="font-size: 3rem; margin-bottom: 15px;">{cap['icon']}</div>
            <h3 style="color: #FFFFFF; margin-bottom: 10px;">{cap['title']}</h3>
            <p style="color: #CCCCCC; font-size: 0.95rem; line-height: 1.6; margin-bottom: 15px;">{cap['description']}</p>
            <ul style="color: #E0E0E0; font-size: 0.85rem; padding-left: 20px;">
        """, unsafe_allow_html=True)
        for feature in cap['features']:
            st.markdown(f"<li>{feature}</li>", unsafe_allow_html=True)
        st.markdown("</ul></div>", unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)

# Live Data Showcase
st.markdown("## 📊 Live Data Showcase")

# Demo data banner
try:
    from dashboard.data_loaders import DB_AVAILABLE
    if not DB_AVAILABLE:
        st.info("""
        📊 **DEMO MODE**: Displaying sample data for portfolio demonstration. All features are fully functional.
        
        💡 **For Production Use**: This platform was built with active API subscriptions. Configure your own API keys in `.env` file 
        (The Odds API, Supabase, NBA Stats API, PandaScore). See `API_SETUP.md` for detailed instructions.
        """)
except:
    pass

# Load sample data to showcase
try:
    # Get data for NBA (most common)
    current_sport = "NBA"
    games = load_tonight_games("NBA")
    if not games:
        # Try other sports
        for sport in ["NFL", "MLB", "NHL", "NCAAB", "NCAAF"]:
            games = load_tonight_games(sport)
            if games:
                current_sport = sport
                break
    
    if games:
        game_ids = [g["id"] for g in games]
        props = load_prop_feed_snapshots(current_sport, game_ids) if game_ids else []
        
        # Stats cards
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            render_metric_card("Active Games", len(games))
        with col2:
            render_metric_card("Player Props", len(props) if props else 0)
        with col3:
            if props:
                def has_positive_edge(prop):
                    edge = prop.get("edge", 0)
                    if isinstance(edge, dict):
                        return edge.get("edge", 0) > 0
                    elif isinstance(edge, (int, float)):
                        return edge > 0
                    return False
                positive_ev = sum(1 for p in props if has_positive_edge(p))
                render_metric_card("+EV Opportunities", positive_ev, color="success")
            else:
                render_metric_card("+EV Opportunities", 0)
        with col4:
            unique_players = len(set(p.get("player_id") for p in props if p.get("player_id"))) if props else 0
            render_metric_card("Unique Players", unique_players)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Sample games display
        if games:
            st.markdown("### 🏀 Upcoming Games")
            for game in games[:5]:  # Show first 5 games
                game_time = format_game_time(game.get("start_time", "")) if game.get("start_time") else "TBD"
                st.markdown(f"""
                <div style="background: #141414; border: 1px solid #2A2A2A; border-radius: 8px; padding: 15px; margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong style="color: #FFFFFF; font-size: 1.1rem;">{game.get('away_team', 'TBD')} @ {game.get('home_team', 'TBD')}</strong>
                            <div style="color: #CCCCCC; font-size: 0.9rem; margin-top: 5px;">{game_time}</div>
                        </div>
                        <div style="color: #00E5FF; font-weight: bold;">{game.get('sport', 'NBA')}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        # Sample props display
        if props:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 🎯 Sample Player Props")
            
            # Get top 5 props by edge (handle both numeric and dict edge values)
            def get_edge_value(prop):
                edge = prop.get("edge")
                if isinstance(edge, dict):
                    return edge.get("edge", 0)
                elif isinstance(edge, (int, float)):
                    return edge
                return 0
            
            top_props = sorted(
                [p for p in props if get_edge_value(p) != 0],
                key=lambda x: get_edge_value(x),
                reverse=True
            )[:5]
            
            for prop in top_props:
                player_name = prop.get("player_name", "Unknown")
                prop_type = prop.get("prop_type", "").replace("_", " ").title()
                line = prop.get("line", "N/A")
                edge_raw = prop.get("edge", 0)
                if isinstance(edge_raw, dict):
                    edge = edge_raw.get("edge", 0) * 100
                elif isinstance(edge_raw, (int, float)):
                    edge = edge_raw * 100
                else:
                    edge = 0
                odds = prop.get("over_price") or prop.get("under_price") or "N/A"
                
                edge_color = "#00E5FF" if edge > 0 else "#FF2E63"
                
                st.markdown(f"""
                <div style="background: #141414; border-left: 4px solid {edge_color}; border-radius: 8px; padding: 15px; margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong style="color: #FFFFFF;">{player_name}</strong>
                            <div style="color: #CCCCCC; font-size: 0.9rem; margin-top: 5px;">
                                {prop_type} {line} • Odds: {odds:+d if isinstance(odds, int) else odds}
                            </div>
                        </div>
                        <div style="color: {edge_color}; font-weight: bold; font-size: 1.1rem;">
                            {edge:+.1f}% Edge
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No live games available at the moment. The system is ready to process data when games are scheduled.")
        
except Exception as e:
    st.warning(f"Live data preview unavailable: {str(e)}")
    st.info("The platform is fully functional and will display live data when games are scheduled.")

st.markdown("<br><br>", unsafe_allow_html=True)

# Technical Stack
st.markdown("## 🛠️ Technical Stack")

tech_stack = {
    "Backend": ["Python 3.11+", "Streamlit", "Supabase (PostgreSQL)", "FastAPI"],
    "Data Processing": ["Pandas", "NumPy", "RapidFuzz"],
    "APIs & Integrations": ["The Odds API", "NBA Stats API", "PandaScore API", "HLTV API"],
    "Visualization": ["Plotly", "Streamlit Charts"],
    "ML/AI": ["Scikit-learn", "Custom Projection Models", "Context Analysis"],
    "Infrastructure": ["Supabase Cloud", "Automated Workers", "Scheduled Tasks"]
}

cols = st.columns(3)
tech_items = list(tech_stack.items())
for idx, (category, techs) in enumerate(tech_items):
    with cols[idx % 3]:
        st.markdown(f"""
        <div style="background: #141414; border: 1px solid #2A2A2A; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
            <h4 style="color: #00E5FF; margin-bottom: 15px;">{category}</h4>
            <ul style="color: #E0E0E0; padding-left: 20px;">
        """, unsafe_allow_html=True)
        for tech in techs:
            st.markdown(f"<li>{tech}</li>", unsafe_allow_html=True)
        st.markdown("</ul></div>", unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)

# Features Highlight
st.markdown("## ✨ Key Features")

features_grid = [
    ("🎲", "Parlay Builder", "Build custom parlays with real-time odds calculation and EV analysis"),
    ("📱", "Line Shopping", "Compare odds across multiple sportsbooks to find the best value"),
    ("📊", "Player Insights", "Deep dive into player performance, trends, and matchup analysis"),
    ("⚡", "Smart Suggestions", "AI-powered bet recommendations based on edge and context"),
    ("📈", "Performance Tracking", "Monitor hit rates and track betting performance over time"),
    ("🔄", "Auto-Refresh", "Automated data pipeline keeps information current and up-to-date"),
]

cols = st.columns(3)
for idx, (icon, title, desc) in enumerate(features_grid):
    with cols[idx % 3]:
        st.markdown(f"""
        <div style="background: #141414; border: 1px solid #2A2A2A; border-radius: 12px; padding: 20px; margin-bottom: 20px; text-align: center;">
            <div style="font-size: 2.5rem; margin-bottom: 10px;">{icon}</div>
            <h4 style="color: #FFFFFF; margin-bottom: 10px;">{title}</h4>
            <p style="color: #CCCCCC; font-size: 0.9rem;">{desc}</p>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)

# Setup & Configuration Section
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("## ⚙️ Setup & Configuration")

setup_cols = st.columns(2)

with setup_cols[0]:
    st.markdown("""
    <div style="background: #141414; border: 1px solid #2A2A2A; border-radius: 12px; padding: 25px; height: 100%;">
        <h4 style="color: #00E5FF; margin-top: 0;">🔧 Quick Start</h4>
        <ol style="color: #E0E0E0; line-height: 2;">
            <li>Clone the repository</li>
            <li>Install dependencies: <code style="background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 4px;">pip install -r requirements.txt</code></li>
            <li>Configure <code style="background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 4px;">.env</code> with API keys</li>
            <li>Run: <code style="background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 4px;">streamlit run dashboard/main.py</code></li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

with setup_cols[1]:
    st.markdown("""
    <div style="background: #141414; border: 1px solid #2A2A2A; border-radius: 12px; padding: 25px; height: 100%;">
        <h4 style="color: #00E5FF; margin-top: 0;">🔑 API Keys Required</h4>
        <ul style="color: #E0E0E0; line-height: 2;">
            <li><strong>The Odds API</strong> - Get your key at theoddsapi.com</li>
            <li><strong>Supabase</strong> - Create project at supabase.com</li>
            <li><strong>NBA Stats API</strong> - Available at stats.nba.com</li>
            <li><strong>PandaScore</strong> - Esports data at pandascore.co</li>
        </ul>
        <p style="color: #CCCCCC; font-size: 0.9rem; margin-top: 15px;">
            <strong>Demo Mode:</strong> Works without API keys using sample data
        </p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)

# Architecture & Design Section
st.markdown("## 🏗️ Architecture Highlights")

arch_features = [
    {
        "title": "Scalable Data Pipeline",
        "description": "ETL workers fetch, process, and store data from multiple APIs with error handling, retries, and data validation.",
        "tech": ["Scheduled Workers", "Error Handling", "Data Validation", "Snapshot Management"]
    },
    {
        "title": "Real-Time Processing",
        "description": "Live odds aggregation, edge calculations, and projection updates with 5-minute cache TTL for optimal performance.",
        "tech": ["Streamlit Caching", "Real-Time Updates", "Edge Calculations", "Performance Optimization"]
    },
    {
        "title": "Advanced Analytics",
        "description": "ML-powered projections, EV analysis, hit rate tracking, and context-aware insights for informed decision-making.",
        "tech": ["Machine Learning", "Statistical Analysis", "Context Analysis", "Performance Metrics"]
    },
    {
        "title": "Production-Ready UI",
        "description": "Premium design system with animations, responsive layouts, and intuitive user experience.",
        "tech": ["Custom CSS/HTML", "Glass Morphism", "Smooth Animations", "Responsive Design"]
    }
]

arch_cols = st.columns(2)
for idx, feature in enumerate(arch_features):
    with arch_cols[idx % 2]:
        st.markdown(f"""
        <div style="background: #141414; border: 1px solid #2A2A2A; border-radius: 12px; padding: 20px; margin-bottom: 20px; height: 100%; transition: all 0.3s ease;">
            <h4 style="color: #FFFFFF; margin-top: 0; margin-bottom: 10px;">{feature['title']}</h4>
            <p style="color: #CCCCCC; font-size: 0.95rem; line-height: 1.6; margin-bottom: 15px;">{feature['description']}</p>
            <div style="display: flex; flex-wrap: wrap; gap: 8px;">
            """, unsafe_allow_html=True)
        for tech in feature['tech']:
            st.markdown(f"""
            <span style="background: rgba(0, 229, 255, 0.15); color: #00E5FF; padding: 4px 10px; border-radius: 6px; font-size: 0.8rem; border: 1px solid rgba(0, 229, 255, 0.3);">
                {tech}
            </span>
            """, unsafe_allow_html=True)
        st.markdown("</div></div>", unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)

# Footer
st.markdown("""
<div style="text-align: center; padding: 40px 20px; background: linear-gradient(135deg, #0A0A0A 0%, #1a1a2e 100%); border-radius: 20px; margin-top: 40px; border: 1px solid rgba(0, 229, 255, 0.1);">
    <p style="color: #CCCCCC; font-size: 1rem; margin-bottom: 10px;">
        Built with ❤️ using Python, Streamlit, and modern data science practices
    </p>
    <p style="color: #888; font-size: 0.9rem; margin: 5px 0;">
        Explore the platform using the navigation menu to see live data and features in action
    </p>
    <p style="color: #00E5FF; font-size: 0.85rem; margin-top: 15px; font-weight: 600;">
        🔑 Configure API keys in .env file for full production functionality
    </p>
</div>
""", unsafe_allow_html=True)

