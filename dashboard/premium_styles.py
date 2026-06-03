"""
Sports Betting Dashboard — Clean, Data-Focused Theme
Inspired by professional trading terminals and the BETTING_METHODOLOGY.md cart format.

Design principles:
- High contrast for legibility (WCAG AA+)
- Semantic colors only — no decorative gradients
- Dark navy background for long sessions, accent colors for status
- Card-based layouts with clear hierarchy
"""
import streamlit as st


# ── DESIGN TOKENS ──────────────────────────────────────────────
TOKENS = {
    # Backgrounds (PrizePicks / Modern Dark Mode)
    "bg_main":      "#0a0a0a",   # Deepest black/gray
    "bg_panel":     "#121212",   # Card background
    "bg_panel_2":   "#1a1a1a",   # Hover state / secondary card
    "bg_input":     "#1f1f1f",   # Form inputs
    "border":       "#262626",   # Subtle dividers
    "border_strong":"#333333",

    # Text
    "text_primary":   "#ffffff",
    "text_secondary": "#a3a3a3",
    "text_muted":     "#737373",
    "text_dim":       "#525252",

    # Semantic — bet status (Neon accents)
    "green":        "#10b981",   # Emerald green (Over / Hit)
    "green_bg":     "rgba(16, 185, 129, 0.1)",
    "green_dim":    "#059669",
    "red":          "#ef4444",   # Rose red (Under / Miss)
    "red_bg":       "rgba(239, 68, 68, 0.1)",
    "red_dim":      "#dc2626",
    "amber":        "#f59e0b",   # Amber (Edge / Value)
    "amber_bg":     "rgba(245, 158, 11, 0.1)",
    "blue":         "#3b82f6",   # Info
    "blue_bg":      "rgba(59, 130, 246, 0.1)",
    "purple":       "#8b5cf6",   # NBA
    "teal":         "#06b6d4",   # NHL
    "gold":         "#eab308",   # Rank #1
    "silver":       "#d4d4d8",
    "bronze":       "#b45309",
}


def color(name: str) -> str:
    return TOKENS.get(name, "#FFFFFF")


def apply_premium_theme():
    """Apply clean data-focused dashboard theme."""
    st.markdown(f"""
<style>
    /* ── Fonts ─────────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap');

    html, body, [class*="css"], .stApp {{
        font-family: 'Inter', -apple-system, system-ui, sans-serif !important;
    }}

    /* ── App background ────────────────────────────────── */
    .stApp {{
        background: {TOKENS["bg_main"]} !important;
    }}

    [data-testid="stMain"], .main .block-container {{
        background: {TOKENS["bg_main"]};
        padding-top: 1.5rem !important;
        max-width: 1400px;
    }}

    /* ── Sidebar ───────────────────────────────────────── */
    section[data-testid="stSidebar"] {{
        background: {TOKENS["bg_panel"]} !important;
        border-right: 1px solid {TOKENS["border"]} !important;
    }}

    [data-testid="stSidebarNav"] {{
        padding-top: 1rem;
    }}

    [data-testid="stSidebarNav"] a {{
        color: {TOKENS["text_secondary"]} !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 8px 12px !important;
        border-radius: 6px !important;
        margin: 2px 8px !important;
        transition: all 0.15s ease !important;
    }}

    [data-testid="stSidebarNav"] a:hover {{
        background: {TOKENS["bg_panel_2"]} !important;
        color: {TOKENS["green"]} !important;
    }}

    [data-testid="stSidebarNav"] [aria-current="page"] {{
        background: {TOKENS["green_bg"]} !important;
        color: {TOKENS["green"]} !important;
        border-left: 3px solid {TOKENS["green"]} !important;
    }}

    /* ── Typography ────────────────────────────────────── */
    h1, h2, h3, h4, h5, h6 {{
        color: {TOKENS["text_primary"]} !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em;
    }}

    h1 {{ font-size: 2rem !important; margin-bottom: 0.5rem !important; }}
    h2 {{ font-size: 1.4rem !important; }}
    h3 {{ font-size: 1.15rem !important; color: {TOKENS["text_secondary"]} !important; }}

    p, span, div, label {{
        color: {TOKENS["text_secondary"]};
    }}

    .stCaption, [data-testid="stCaptionContainer"] {{
        color: {TOKENS["text_muted"]} !important;
        font-size: 13px !important;
    }}

    /* ── Buttons ───────────────────────────────────────── */
    .stButton > button {{
        background: {TOKENS["bg_panel_2"]} !important;
        color: {TOKENS["text_primary"]} !important;
        border: 1px solid {TOKENS["border_strong"]} !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.15s ease !important;
    }}

    .stButton > button:hover {{
        background: {TOKENS["green_bg"]} !important;
        border-color: {TOKENS["green"]} !important;
        color: {TOKENS["green"]} !important;
        transform: none !important;
    }}

    .stButton > button[kind="primary"] {{
        background: {TOKENS["green_dim"]} !important;
        color: white !important;
        border-color: {TOKENS["green"]} !important;
    }}

    .stButton > button[kind="primary"]:hover {{
        background: {TOKENS["green"]} !important;
    }}

    /* ── Inputs ────────────────────────────────────────── */
    .stTextInput input, .stNumberInput input, .stSelectbox > div > div,
    textarea, .stDateInput input {{
        background: {TOKENS["bg_input"]} !important;
        color: {TOKENS["text_primary"]} !important;
        border: 1px solid {TOKENS["border"]} !important;
        border-radius: 6px !important;
        font-family: 'JetBrains Mono', monospace !important;
    }}

    .stTextInput input:focus, .stNumberInput input:focus {{
        border-color: {TOKENS["green"]} !important;
        box-shadow: 0 0 0 1px {TOKENS["green"]}33 !important;
    }}

    label {{
        color: {TOKENS["text_secondary"]} !important;
        font-weight: 500 !important;
        font-size: 13px !important;
    }}

    /* ── Metrics ───────────────────────────────────────── */
    [data-testid="stMetric"] {{
        background: {TOKENS["bg_panel"]};
        padding: 16px;
        border-radius: 8px;
        border: 1px solid {TOKENS["border"]};
    }}

    [data-testid="stMetricLabel"] {{
        color: {TOKENS["text_muted"]} !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }}

    [data-testid="stMetricValue"] {{
        color: {TOKENS["text_primary"]} !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
        font-size: 1.8rem !important;
    }}

    [data-testid="stMetricDelta"] {{
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 600 !important;
    }}

    /* ── Tabs ──────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {{
        background: {TOKENS["bg_panel"]};
        border-radius: 8px;
        padding: 4px;
        gap: 2px;
        border: 1px solid {TOKENS["border"]};
    }}

    .stTabs [data-baseweb="tab"] {{
        background: transparent !important;
        color: {TOKENS["text_muted"]} !important;
        font-weight: 600 !important;
        padding: 8px 16px !important;
        border-radius: 6px !important;
        border: none !important;
    }}

    .stTabs [aria-selected="true"] {{
        background: {TOKENS["bg_panel_2"]} !important;
        color: {TOKENS["green"]} !important;
        box-shadow: inset 0 -2px 0 {TOKENS["green"]} !important;
    }}

    /* ── Tables / DataFrames ───────────────────────────── */
    [data-testid="stDataFrame"], [data-testid="stTable"] {{
        background: {TOKENS["bg_panel"]};
        border-radius: 8px;
        border: 1px solid {TOKENS["border"]};
    }}

    [data-testid="stDataFrame"] table {{
        font-family: 'Inter', sans-serif !important;
        font-size: 13px !important;
    }}

    [data-testid="stDataFrame"] thead tr th {{
        background: {TOKENS["bg_panel_2"]} !important;
        color: {TOKENS["text_muted"]} !important;
        font-weight: 700 !important;
        font-size: 11px !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border-bottom: 1px solid {TOKENS["border_strong"]} !important;
    }}

    [data-testid="stDataFrame"] tbody tr {{
        background: {TOKENS["bg_panel"]} !important;
    }}

    [data-testid="stDataFrame"] tbody tr:hover {{
        background: {TOKENS["bg_panel_2"]} !important;
    }}

    [data-testid="stDataFrame"] tbody td {{
        color: {TOKENS["text_primary"]} !important;
        border-bottom: 1px solid {TOKENS["border"]} !important;
    }}

    /* ── Alerts / Info ─────────────────────────────────── */
    [data-baseweb="notification"] {{
        border-radius: 8px !important;
        border-width: 1px !important;
        border-style: solid !important;
    }}

    div[data-testid="stAlert"][data-baseweb="notification"] {{
        background: {TOKENS["bg_panel"]} !important;
        border-color: {TOKENS["border"]} !important;
        color: {TOKENS["text_primary"]} !important;
    }}

    /* Success alert */
    div[role="alert"]:has(svg[fill="currentColor"]) {{
        background: {TOKENS["green_bg"]} !important;
    }}

    /* ── Expander ──────────────────────────────────────── */
    [data-testid="stExpander"] {{
        background: {TOKENS["bg_panel"]} !important;
        border: 1px solid {TOKENS["border"]} !important;
        border-radius: 8px !important;
    }}

    [data-testid="stExpander"] summary {{
        color: {TOKENS["text_primary"]} !important;
        font-weight: 600 !important;
    }}

    /* ── Custom utility classes ───────────────────────── */
    .play-card {{
        background: {TOKENS["bg_panel"]};
        border: 1px solid {TOKENS["border"]};
        border-radius: 10px;
        padding: 18px;
        margin: 12px 0;
        transition: all 0.15s ease;
    }}

    .play-card:hover {{
        border-color: {TOKENS["border_strong"]};
    }}

    .play-card.best-value {{
        border-left: 4px solid {TOKENS["green"]};
        background: linear-gradient(90deg, {TOKENS["green_bg"]}55 0%, {TOKENS["bg_panel"]} 60%);
    }}

    .play-card.strong {{
        border-left: 4px solid {TOKENS["green_dim"]};
    }}

    .play-card.lean {{
        border-left: 4px solid {TOKENS["amber"]};
        background: linear-gradient(90deg, {TOKENS["amber_bg"]}55 0%, {TOKENS["bg_panel"]} 60%);
    }}

    .play-card.skip {{
        border-left: 4px solid {TOKENS["red"]};
        background: linear-gradient(90deg, {TOKENS["red_bg"]}55 0%, {TOKENS["bg_panel"]} 60%);
        opacity: 0.85;
    }}

    .play-card.anchor {{
        border-left: 4px solid {TOKENS["blue"]};
    }}

    /* Status badges */
    .badge {{
        display: inline-block;
        padding: 3px 10px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-family: 'Inter', sans-serif;
    }}

    .badge-best   {{ background: {TOKENS["green"]};      color: #001a08; }}
    .badge-strong {{ background: {TOKENS["green_dim"]};  color: #ffffff; }}
    .badge-play   {{ background: {TOKENS["green_bg"]};   color: {TOKENS["green"]};   border: 1px solid {TOKENS["green"]}; }}
    .badge-value  {{ background: {TOKENS["amber"]};      color: #1a0e00; }}
    .badge-lean   {{ background: {TOKENS["amber_bg"]};   color: {TOKENS["amber"]};   border: 1px solid {TOKENS["amber"]}; }}
    .badge-skip   {{ background: {TOKENS["red"]};        color: #1a0506; }}
    .badge-trap   {{ background: {TOKENS["red_bg"]};     color: {TOKENS["red"]};     border: 1px solid {TOKENS["red"]}; }}
    .badge-anchor {{ background: {TOKENS["blue"]};       color: #001633; }}
    .badge-info   {{ background: {TOKENS["bg_panel_2"]}; color: {TOKENS["text_muted"]}; border: 1px solid {TOKENS["border"]}; }}
    .badge-tier1  {{ background: {TOKENS["green"]};      color: #001a08; }}
    .badge-tier2  {{ background: {TOKENS["green_dim"]};  color: #ffffff; }}
    .badge-tier3  {{ background: {TOKENS["amber"]};      color: #1a0e00; }}
    .badge-tier4  {{ background: {TOKENS["amber_bg"]};   color: {TOKENS["amber"]};   border: 1px solid {TOKENS["amber"]}; }}
    .badge-avoid  {{ background: {TOKENS["red"]};        color: #1a0506; }}

    .odds-plus   {{ color: {TOKENS["green"]} !important; font-weight: 700; font-family: 'JetBrains Mono', monospace; }}
    .odds-minus  {{ color: {TOKENS["red"]}   !important; font-weight: 700; font-family: 'JetBrains Mono', monospace; }}

    .mono {{ font-family: 'JetBrains Mono', monospace; }}

    /* Game header */
    .game-header {{
        background: {TOKENS["bg_panel_2"]};
        border-radius: 8px 8px 0 0;
        padding: 12px 18px;
        border-bottom: 1px solid {TOKENS["border"]};
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}

    .game-time {{
        color: {TOKENS["text_muted"]};
        font-family: 'JetBrains Mono', monospace;
        font-size: 13px;
    }}

    /* Edge indicators */
    .edge-positive {{ color: {TOKENS["green"]}; font-weight: 700; }}
    .edge-neutral  {{ color: {TOKENS["amber"]}; font-weight: 700; }}
    .edge-negative {{ color: {TOKENS["red"]};   font-weight: 700; }}

    /* Slip card */
    .slip-card {{
        background: {TOKENS["bg_panel"]};
        border: 1px solid {TOKENS["border"]};
        border-radius: 12px;
        padding: 20px;
        margin: 16px 0;
    }}

    .slip-header-anchor      {{ background: linear-gradient(90deg, {TOKENS["blue"]} 0%, {TOKENS["blue_bg"]} 100%); }}
    .slip-header-best        {{ background: linear-gradient(90deg, {TOKENS["green"]} 0%, {TOKENS["green_bg"]} 100%); }}
    .slip-header-value       {{ background: linear-gradient(90deg, {TOKENS["amber"]} 0%, {TOKENS["amber_bg"]} 100%); }}
    .slip-header-swing       {{ background: linear-gradient(90deg, {TOKENS["amber"]} 0%, {TOKENS["red_bg"]} 100%); }}
    .slip-header-cross       {{ background: linear-gradient(90deg, {TOKENS["purple"]} 0%, {TOKENS["bg_panel_2"]} 100%); }}

    .slip-header {{
        color: white;
        padding: 14px 20px;
        border-radius: 10px 10px 0 0;
        font-weight: 700;
        margin: 0 -20px -20px -20px;
        margin-bottom: 16px;
    }}

    /* Hide Streamlit branding */
    [data-testid="stStatusWidget"], [data-testid="stToolbar"] {{
        display: none !important;
    }}

    footer {{ display: none !important; }}

    #MainMenu {{ visibility: hidden; }}

    /* Tighten vertical spacing */
    [data-testid="stVerticalBlock"] > [data-testid="element-container"] {{
        margin-bottom: 0.5rem;
    }}
</style>
""", unsafe_allow_html=True)


# ── Helper renderers used by pages ────────────────────────────
def status_badge(status: str) -> str:
    """Render a status as a colored badge HTML span."""
    s = str(status).upper()
    cls_map = {
        "BEST VALUE":   "badge-best",
        "BEST ANCHOR":  "badge-best",
        "STRONG":       "badge-strong",
        "PLAY":         "badge-play",
        "VALUE":        "badge-value",
        "SWING VALUE":  "badge-value",
        "LEAN":         "badge-lean",
        "ANCHOR":       "badge-anchor",
        "SGP ONLY":     "badge-anchor",
        "PARLAY ONLY":  "badge-anchor",
        "SKIP":         "badge-skip",
        "CUT":          "badge-skip",
        "TRAP":         "badge-trap",
        "INFO":         "badge-info",
    }
    cls = "badge-info"
    for key, c in cls_map.items():
        if key in s:
            cls = c
            break
    return f'<span class="badge {cls}">{status}</span>'


def odds_html(odds) -> str:
    """Render American odds with color coding."""
    if odds is None or odds == "":
        return '<span class="mono" style="color:#6E7681">—</span>'
    try:
        v = int(odds)
        if v > 0:
            return f'<span class="odds-plus">+{v}</span>'
        else:
            return f'<span class="odds-minus">{v}</span>'
    except Exception:
        # String odds like "~+120" or "✅ -132"
        s = str(odds)
        if "+" in s.split("(")[0]:
            return f'<span class="odds-plus">{s}</span>'
        if "-" in s.split("(")[0]:
            return f'<span class="odds-minus">{s}</span>'
        return f'<span class="mono">{s}</span>'


def edge_html(edge_pct: float) -> str:
    """Render edge percentage with color."""
    if edge_pct is None:
        return '—'
    cls = "edge-positive" if edge_pct >= 2 else ("edge-neutral" if edge_pct > 0 else "edge-negative")
    sign = "+" if edge_pct >= 0 else ""
    return f'<span class="{cls}">{sign}{edge_pct:.1f}%</span>'


def tier_badge(tier: str) -> str:
    """Pitcher tier badge."""
    t = str(tier).upper()
    if "TIER 1" in t:  return f'<span class="badge badge-tier1">{tier}</span>'
    if "TIER 2" in t:  return f'<span class="badge badge-tier2">{tier}</span>'
    if "TIER 3" in t:  return f'<span class="badge badge-tier3">{tier}</span>'
    if "TIER 4" in t:  return f'<span class="badge badge-tier4">{tier}</span>'
    if "AVOID" in t:   return f'<span class="badge badge-avoid">{tier}</span>'
    return f'<span class="badge badge-info">{tier}</span>'


# Backwards-compat alias
apply_theme = apply_premium_theme
