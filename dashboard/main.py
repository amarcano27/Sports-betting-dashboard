"""
APEX ANALYTICS - Main Entry Point
Run: streamlit run dashboard/main.py
"""
import streamlit as st
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from dashboard.premium_styles import apply_theme
except Exception:
    sys.path.append(str(Path(__file__).parent))
    from premium_styles import apply_theme

st.set_page_config(
    page_title="APEX Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="⚡",
)
apply_theme()

pages = [
    # ── The Hub ──────────────────────────────────────────────────
    st.Page("portfolio_showcase.py", title="Command Center", icon=":material/dashboard:", default=True),

    # ── Player Props ───────────────────────────────────────────
    st.Page("player_props_page.py",  title="Prop Matrix",   icon=":material/grid_view:"),

    # ── Game Models ───────────────────────────────────────────
    st.Page("mlb_page.py",           title="MLB Model",     icon=":material/sports_baseball:"),
    st.Page("nba_page.py",           title="NBA Model",     icon=":material/sports_basketball:"),
    st.Page("nhl_page.py",           title="NHL Model",     icon=":material/sports_hockey:"),

    # ── Tools ─────────────────────────────────────────────────
    st.Page("priority_rankings.py",  title="Top Edges",     icon=":material/bolt:"),
    st.Page("slip_builder.py",       title="Bet Slip",      icon=":material/receipt_long:"),
    st.Page("moneylines_page.py",    title="Line Shopping", icon=":material/compare_arrows:"),
    st.Page("data_manager.py",       title="Data Sync",     icon=":material/sync:"),

    # ── Hidden detail pages ───────────────────────────────────
    st.Page("player_insights.py",    title="Player Insights",icon=":material/insights:", default=False),
]

page = st.navigation(pages, position="sidebar", expanded=True)
page.run()
