"""
APEX ANALYTICS - The Ultimate Betting Design System
Ultra-modern, high-contrast, data-dense UI inspired by professional trading terminals.
"""
import streamlit as st

# ── APEX DESIGN TOKENS ──────────────────────────────────────────────
TOKENS = {
    # Backgrounds (Deep Midnight / Slate)
    "bg_main":      "#050B14",   # Deepest midnight blue/black
    "bg_panel":     "#0F172A",   # Slate 900 - Card background
    "bg_panel_2":   "#1E293B",   # Slate 800 - Hover state / secondary card
    "bg_input":     "#0F172A",   # Form inputs
    "border":       "#1E293B",   # Subtle dividers
    "border_strong":"#334155",   # Slate 700
    "border_glow":  "rgba(56, 189, 248, 0.3)", # Cyan glow

    # Text
    "text_primary":   "#F8FAFC", # Slate 50
    "text_secondary": "#94A3B8", # Slate 400
    "text_muted":     "#64748B", # Slate 500
    "text_dim":       "#475569", # Slate 600

    # Semantic — Bet Status & EV (Neon Accents)
    "green":        "#10B981",   # Emerald (Hit / Over / +EV)
    "green_bg":     "rgba(16, 185, 129, 0.15)",
    "green_glow":   "rgba(16, 185, 129, 0.4)",
    
    "red":          "#EF4444",   # Rose (Miss / Under / -EV)
    "red_bg":       "rgba(239, 68, 68, 0.15)",
    "red_glow":     "rgba(239, 68, 68, 0.4)",
    
    "amber":        "#F59E0B",   # Amber (Value / Lean)
    "amber_bg":     "rgba(245, 158, 11, 0.15)",
    "amber_glow":   "rgba(245, 158, 11, 0.4)",
    
    "cyan":         "#06B6D4",   # Cyan (Brand Primary / Info)
    "cyan_bg":      "rgba(6, 182, 212, 0.15)",
    "cyan_glow":    "rgba(6, 182, 212, 0.4)",
    
    "purple":       "#8B5CF6",   # Violet (Cross-sport / Special)
    "purple_bg":    "rgba(139, 92, 246, 0.15)",
}

def color(name: str) -> str:
    return TOKENS.get(name, "#FFFFFF")

def apply_premium_theme():
    """Apply the APEX data-focused dashboard theme."""
    st.markdown(f"""
<style>
    /* ── Fonts ─────────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@500;600;700;800&display=swap');

    html, body, [class*="css"], .stApp {{
        font-family: 'Inter', -apple-system, system-ui, sans-serif !important;
        background-color: {TOKENS["bg_main"]} !important;
        color: {TOKENS["text_primary"]} !important;
    }}

    /* ── App background & Layout ───────────────────────── */
    .stApp {{
        background: {TOKENS["bg_main"]} !important;
        background-image: 
            radial-gradient(circle at 15% 50%, rgba(6, 182, 212, 0.03), transparent 25%),
            radial-gradient(circle at 85% 30%, rgba(139, 92, 246, 0.03), transparent 25%);
    }}

    [data-testid="stMain"], .main .block-container {{
        background: transparent;
        padding-top: 2rem !important;
        max-width: 1600px; /* Wider for ultimate dashboard */
    }}

    /* ── Sidebar (The Command Strip) ───────────────────── */
    section[data-testid="stSidebar"] {{
        background: {TOKENS["bg_panel"]} !important;
        border-right: 1px solid {TOKENS["border"]} !important;
    }}

    [data-testid="stSidebarNav"] {{
        padding-top: 1.5rem;
    }}

    [data-testid="stSidebarNav"] a {{
        color: {TOKENS["text_secondary"]} !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 10px 16px !important;
        border-radius: 8px !important;
        margin: 4px 12px !important;
        transition: all 0.2s ease !important;
    }}

    [data-testid="stSidebarNav"] a:hover {{
        background: {TOKENS["bg_panel_2"]} !important;
        color: {TOKENS["text_primary"]} !important;
        transform: translateX(4px);
    }}

    [data-testid="stSidebarNav"] [aria-current="page"] {{
        background: {TOKENS["cyan_bg"]} !important;
        color: {TOKENS["cyan"]} !important;
        border-left: 4px solid {TOKENS["cyan"]} !important;
        box-shadow: inset 20px 0 20px -20px {TOKENS["cyan_glow"]};
    }}

    /* ── Typography ────────────────────────────────────── */
    h1, h2, h3, h4, h5, h6 {{
        color: {TOKENS["text_primary"]} !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 800 !important;
        letter-spacing: -0.03em;
    }}

    h1 {{ font-size: 2.5rem !important; margin-bottom: 1rem !important; }}
    h2 {{ font-size: 1.75rem !important; }}
    h3 {{ font-size: 1.25rem !important; color: {TOKENS["text_primary"]} !important; }}

    p, span, div, label {{
        color: {TOKENS["text_secondary"]};
    }}

    .stCaption, [data-testid="stCaptionContainer"] {{
        color: {TOKENS["text_muted"]} !important;
        font-size: 13px !important;
        font-weight: 500;
    }}

    /* ── Buttons ───────────────────────────────────────── */
    .stButton > button {{
        background: {TOKENS["bg_panel_2"]} !important;
        color: {TOKENS["text_primary"]} !important;
        border: 1px solid {TOKENS["border_strong"]} !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-size: 13px !important;
    }}

    .stButton > button:hover {{
        background: {TOKENS["cyan_bg"]} !important;
        border-color: {TOKENS["cyan"]} !important;
        color: {TOKENS["cyan"]} !important;
        box-shadow: 0 0 15px {TOKENS["cyan_glow"]} !important;
        transform: translateY(-1px) !important;
    }}

    .stButton > button[kind="primary"] {{
        background: {TOKENS["cyan"]} !important;
        color: #000000 !important;
        border: none !important;
    }}

    .stButton > button[kind="primary"]:hover {{
        background: #22D3EE !important; /* Lighter cyan */
        box-shadow: 0 0 20px {TOKENS["cyan_glow"]} !important;
    }}

    /* ── Inputs ────────────────────────────────────────── */
    .stTextInput input, .stNumberInput input, .stSelectbox > div > div,
    textarea, .stDateInput input {{
        background: {TOKENS["bg_main"]} !important;
        color: {TOKENS["text_primary"]} !important;
        border: 1px solid {TOKENS["border_strong"]} !important;
        border-radius: 8px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }}

    .stTextInput input:focus, .stNumberInput input:focus, .stSelectbox > div > div:focus-within {{
        border-color: {TOKENS["cyan"]} !important;
        box-shadow: 0 0 0 2px {TOKENS["cyan_glow"]} !important;
    }}

    label {{
        color: {TOKENS["text_secondary"]} !important;
        font-weight: 600 !important;
        font-size: 12px !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}

    /* ── Metrics (Native Streamlit) ────────────────────── */
    [data-testid="stMetric"] {{
        background: {TOKENS["bg_panel"]};
        padding: 20px;
        border-radius: 12px;
        border: 1px solid {TOKENS["border"]};
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
    }}

    [data-testid="stMetricLabel"] {{
        color: {TOKENS["text_muted"]} !important;
        font-size: 12px !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }}

    [data-testid="stMetricValue"] {{
        color: {TOKENS["text_primary"]} !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 800 !important;
        font-size: 2.2rem !important;
        margin-top: 4px;
    }}

    [data-testid="stMetricDelta"] {{
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
        font-size: 14px !important;
    }}

    /* ── Dataframes ────────────────────────────────────── */
    [data-testid="stDataFrame"] {{
        border: 1px solid {TOKENS["border"]};
        border-radius: 12px;
        overflow: hidden;
    }}

    /* ── Hide Streamlit Branding ───────────────────────── */
    [data-testid="stStatusWidget"], [data-testid="stToolbar"] {{ display: none !important; }}
    footer {{ display: none !important; }}
    #MainMenu {{ visibility: hidden; }}

    /* ── Custom Apex Classes ───────────────────────────── */
    .apex-card {{
        background: {TOKENS["bg_panel"]};
        border: 1px solid {TOKENS["border"]};
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5), 0 4px 6px -2px rgba(0, 0, 0, 0.3);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }}
    
    .apex-card:hover {{
        border-color: {TOKENS["border_strong"]};
        transform: translateY(-2px);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.6), 0 10px 10px -5px rgba(0, 0, 0, 0.4);
    }}

    .apex-card.glow-green:hover {{ border-color: {TOKENS["green"]}; box-shadow: 0 0 30px {TOKENS["green_glow"]}; }}
    .apex-card.glow-cyan:hover  {{ border-color: {TOKENS["cyan"]};  box-shadow: 0 0 30px {TOKENS["cyan_glow"]}; }}
    .apex-card.glow-amber:hover {{ border-color: {TOKENS["amber"]}; box-shadow: 0 0 30px {TOKENS["amber_glow"]}; }}

    .mono-bold {{
        font-family: 'JetBrains Mono', monospace;
        font-weight: 800;
    }}
    
    .text-gradient-cyan {{
        background: linear-gradient(135deg, #06B6D4 0%, #3B82F6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}
    
    .badge {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-family: 'Inter', sans-serif;
    }}
    
    .badge-green {{ background: {TOKENS["green_bg"]}; color: {TOKENS["green"]}; border: 1px solid {TOKENS["green_glow"]}; }}
    .badge-red   {{ background: {TOKENS["red_bg"]};   color: {TOKENS["red"]};   border: 1px solid {TOKENS["red_glow"]}; }}
    .badge-amber {{ background: {TOKENS["amber_bg"]}; color: {TOKENS["amber"]}; border: 1px solid {TOKENS["amber_glow"]}; }}
    .badge-cyan  {{ background: {TOKENS["cyan_bg"]};  color: {TOKENS["cyan"]};  border: 1px solid {TOKENS["cyan_glow"]}; }}

</style>
""", unsafe_allow_html=True)

# Backwards-compat alias
apply_theme = apply_premium_theme
