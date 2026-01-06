"""
Main entry point for Sports Betting Dashboard
Uses st.navigation() for multi-page app

IMPORTANT: Run this file with: streamlit run dashboard/main.py
"""
import streamlit as st
import sys
import os
from pathlib import Path

# Add project root to path to allow imports from services and dashboard
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from dashboard.premium_styles import apply_premium_theme as apply_theme
except (KeyError, ImportError):
    # Fallback if dashboard package resolution fails
    sys.path.append(str(Path(__file__).parent))
    try:
        from premium_styles import apply_premium_theme as apply_theme
    except:
        from styles import apply_theme

# Page config
st.set_page_config(
    page_title="Sports Betting Analytics Platform",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📊"
)

# Apply Global Theme
apply_theme()

# Define pages - using relative paths from main.py's directory
pages = [
    st.Page("portfolio_showcase.py", title="PORTFOLIO", icon=":material/dashboard:", default=True),
    st.Page("home_page.py", title="MARKETPLACE", icon=":material/storefront:"),
    st.Page("line_shopping.py", title="LINE SHOPPING", icon=":material/shopping_cart:"),
    st.Page("player_props_page.py", title="PLAYER PROPS", icon=":material/sports_basketball:"),
    st.Page("moneylines_page.py", title="MONEYLINES", icon=":material/attach_money:"),
    st.Page("app.py", title="ANALYTICS", icon=":material/analytics:"),
    # Hidden pages (accessible via st.switch_page)
    st.Page("player_insights.py", title="Player Insights", icon=":material/insights:", default=False),
]

# Create navigation
page = st.navigation(pages, position="sidebar", expanded=True)

# Run the selected page
page.run()
