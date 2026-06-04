"""
APEX ANALYTICS - Main Entry Point
Run: streamlit run dashboard/main.py
"""
import streamlit as st
import sys
from pathlib import Path
import socket

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
    initial_sidebar_state="auto",
    page_icon="⚡",
)
apply_theme()

PAGE_ROUTES = {
    "Command Center":  "portfolio_showcase.py",
    "MLB Model":       "mlb_page.py",
    "NBA Model":       "nba_page.py",
    "NHL Model":       "nhl_page.py",
    "NFL Model":       "nfl_page.py",
    "PGA Golf":        "pga_page.py",
    "Prop Matrix":     "player_props_page.py",
    "Top Edges":       "priority_rankings.py",
    "Power Rankings":  "power_rankings.py",
    "Bet Slip":        "slip_builder.py",
    "SGP Builder":     "sgp_builder.py",
    "Bet Tracker":     "bet_tracker.py",
    "Line Shopping":   "moneylines_page.py",
    "Injuries":        "injury_feed.py",
    "Data Sync":       "data_manager.py",
}

def _local_lan_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        return "127.0.0.1"

def _go_to_selected_page():
    target = st.session_state.get("apex_page_picker")
    path   = PAGE_ROUTES.get(target)
    if path:
        st.switch_page(path)

# Mobile-friendly top-of-page dropdown (hidden on desktop by CSS)
st.selectbox(
    "Go to page",
    options=list(PAGE_ROUTES.keys()),
    key="apex_page_picker",
    on_change=_go_to_selected_page,
)

pages = [
    # ── Core ──────────────────────────────────────────────────
    st.Page("portfolio_showcase.py", title="Command Center", icon=":material/dashboard:",        default=True),
    # ── Sport Models ──────────────────────────────────────────
    st.Page("mlb_page.py",           title="MLB Model",      icon=":material/sports_baseball:"),
    st.Page("nba_page.py",           title="NBA Model",      icon=":material/sports_basketball:"),
    st.Page("nhl_page.py",           title="NHL Model",      icon=":material/sports_hockey:"),
    st.Page("nfl_page.py",           title="NFL Model",      icon=":material/sports_football:"),
    st.Page("pga_page.py",           title="PGA Golf",       icon=":material/sports_golf:"),
    # ── Props & Edges ─────────────────────────────────────────
    st.Page("player_props_page.py",  title="Prop Matrix",    icon=":material/grid_view:"),
    st.Page("priority_rankings.py",  title="Top Edges",      icon=":material/bolt:"),
    # ── Betting Tools ─────────────────────────────────────────
    st.Page("slip_builder.py",       title="Bet Slip",       icon=":material/receipt_long:"),
    st.Page("sgp_builder.py",        title="SGP Builder",    icon=":material/link:"),
    st.Page("bet_tracker.py",        title="Bet Tracker",    icon=":material/track_changes:"),
    st.Page("moneylines_page.py",    title="Line Shopping",  icon=":material/compare_arrows:"),
    st.Page("power_rankings.py",     title="Power Rankings", icon=":material/emoji_events:"),
    # ── Info ──────────────────────────────────────────────────
    st.Page("injury_feed.py",        title="Injuries",       icon=":material/medical_services:"),
    # ── Admin ─────────────────────────────────────────────────
    st.Page("data_manager.py",       title="Data Sync",      icon=":material/sync:"),
    # ── Hidden detail pages ───────────────────────────────────
    st.Page("player_insights.py",    title="Player Insights",icon=":material/insights:",        default=False),
]

page = st.navigation(pages, position="sidebar")
page.run()

with st.sidebar:
    st.markdown("---")
    st.caption("📱 Phone access (same Wi-Fi)")
    st.code(f"http://{_local_lan_ip()}:8501", language=None)
    st.caption("🌐 Remote access → see Data Sync")
