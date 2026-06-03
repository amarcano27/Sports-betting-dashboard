"""
Sports Betting Analytics Dashboard
Run: streamlit run dashboard/main.py
"""
import streamlit as st
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from dashboard.premium_styles import apply_premium_theme as apply_theme
except Exception:
    sys.path.append(str(Path(__file__).parent))
    from premium_styles import apply_premium_theme as apply_theme

st.set_page_config(
    page_title="Sports Betting Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📊",
)
apply_theme()

pages = [
    # ── Home ──────────────────────────────────────────────────
    st.Page("portfolio_showcase.py", title="Command Center", icon=":material/dashboard:", default=True),

    # ── Sport Analysis Pages ───────────────────────────────────
    st.Page("mlb_page.py",           title="MLB",           icon=":material/sports_baseball:"),
    st.Page("nba_page.py",           title="NBA",           icon=":material/sports_basketball:"),
    st.Page("nhl_page.py",           title="NHL",           icon=":material/sports_hockey:"),

    # ── Tools ─────────────────────────────────────────────────
    st.Page("player_props_page.py",  title="Player Props",  icon=":material/person_search:"),
    st.Page("priority_rankings.py",  title="RANKINGS",      icon=":material/leaderboard:"),
    st.Page("slip_builder.py",       title="SLIP BUILDER",  icon=":material/receipt_long:"),
    st.Page("moneylines_page.py",    title="LINE SHOPPING", icon=":material/attach_money:"),

    # ── Settings ──────────────────────────────────────────────
    st.Page("data_manager.py",       title="DATA MANAGER",  icon=":material/sync:"),

    # ── Hidden detail pages ───────────────────────────────────
    st.Page("player_insights.py",    title="Player Insights",icon=":material/insights:",           default=False),
]

page = st.navigation(pages, position="sidebar", expanded=True)
page.run()
