"""
Mobile-responsive layout helpers.
On narrow screens (phones) columns collapse to single-column stacks automatically.
CSS breakpoints injected once per session.
"""
import streamlit as st

_CSS_INJECTED = False

MOBILE_CSS = """
<style>
/* ── Phone / narrow viewport overrides ────────────────────── */
@media (max-width: 768px) {

    /* Stack all st.columns side-by-side → single column */
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 0 !important;
    }

    /* Shrink metric numbers slightly */
    .apex-metric-card .apex-odds-mono { font-size: 22px !important; }

    /* Game cards: full width */
    .apex-card { margin-bottom: 12px !important; }

    /* Team names in game card: wrap gracefully */
    .apex-team-row { flex-direction: column !important; align-items: flex-start !important; gap: 4px !important; }

    /* Prop card avatar row: stack on very small screens */
    @media (max-width: 480px) {
        .apex-line-proj-row { flex-direction: column !important; gap: 8px !important; }
    }

    /* Hide sidebar nav on phone — use the dropdown selectbox instead */
    section[data-testid="stSidebar"] { display: none !important; }

    /* Give the page selectbox more breathing room at top */
    [data-testid="stSelectbox"]:first-of-type { margin-bottom: 12px !important; }

    /* Tighten page padding on small screens */
    [data-testid="stMain"] .block-container {
        padding-left: 12px !important;
        padding-right: 12px !important;
        padding-top: 12px !important;
    }

    /* Tabs scroll horizontally on phone */
    [data-testid="stTabs"] [role="tablist"] {
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch !important;
        flex-wrap: nowrap !important;
        scrollbar-width: none !important;
    }
    [data-testid="stTabs"] [role="tablist"]::-webkit-scrollbar { display: none; }

    /* Bigger tap targets for buttons */
    .stButton > button {
        min-height: 44px !important;
        font-size: 15px !important;
    }

    /* DataFrames: horizontal scroll instead of overflow */
    [data-testid="stDataFrame"] {
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch !important;
    }
}

/* ── Tablet (768–1024px) ───────────────────────────────────── */
@media (min-width: 769px) and (max-width: 1024px) {
    [data-testid="stMain"] .block-container {
        padding-left: 20px !important;
        padding-right: 20px !important;
    }
}
</style>
"""


def inject_mobile_css():
    """Call once per page render to inject responsive CSS."""
    global _CSS_INJECTED
    if not _CSS_INJECTED:
        st.markdown(MOBILE_CSS, unsafe_allow_html=True)
        _CSS_INJECTED = True


def metric_columns(count: int = 4):
    """Return columns — on phone these stack via CSS."""
    inject_mobile_css()
    return st.columns(count)


def card_columns(count: int = 2):
    """Return card columns — default 2 (tablet-friendly, stacks on phone)."""
    inject_mobile_css()
    return st.columns(count)
