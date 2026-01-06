"""
Global Design System for the Dashboard
Theme: Midnight Terminal
"""
import streamlit as st

def apply_theme():
    """Injects global CSS for the million-dollar aesthetic"""
    # Inject CSS using st.markdown - must be properly formatted
    css_content = """
<style>
        /* --- GLOBAL RESET & FONTS --- */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            color: #E0E0E0;
        }
        
        /* --- BACKGROUND & LAYOUT --- */
        .stApp {
            background-color: #0A0A0A; /* Deep Onyx */
            background-image: 
                radial-gradient(circle at 20% 50%, rgba(0, 229, 255, 0.05) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(255, 46, 99, 0.05) 0%, transparent 50%),
                radial-gradient(circle at 50% 0%, #1a1a2e 0%, #0A0A0A 70%);
        }
        
        /* Hide Streamlit Branding but KEEP Header for Sidebar toggle */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* --- SIDEBAR --- */
        section[data-testid="stSidebar"] {
            background-color: #050505;
            border-right: 1px solid #222;
        }
        
        /* Force Sidebar Navigation Text Color to White/Bright Grey */
        [data-testid="stSidebarNav"] span {
            color: #E0E0E0 !important;
            font-weight: 500;
        }
        [data-testid="stSidebarNav"] a {
            color: #E0E0E0 !important;
        }
        /* Sidebar Headers */
        section[data-testid="stSidebar"] h1, 
        section[data-testid="stSidebar"] h2, 
        section[data-testid="stSidebar"] h3,
        section[data-testid="stSidebar"] label {
            color: #FFFFFF !important;
        }
        
        /* --- CONTAINERS & CARDS --- */
        div[data-testid="stVerticalBlock"] > div {
            background-color: transparent;
        }
        
        .prop-card {
            background: linear-gradient(135deg, #141414 0%, #1a1a1a 100%);
            border: 1px solid #2A2A2A;
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 16px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            position: relative;
            overflow: hidden;
        }
        
        .prop-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, transparent, #00E5FF, transparent);
            opacity: 0;
            transition: opacity 0.3s;
        }
        
        .prop-card:hover {
            border-color: #00E5FF;
            transform: translateY(-4px);
            box-shadow: 0 12px 40px rgba(0, 229, 255, 0.2);
        }
        
        .prop-card:hover::before {
            opacity: 1;
        }
        
        /* --- TYPOGRAPHY --- */
        h1, h2, h3 {
            font-weight: 800;
            letter-spacing: -0.5px;
            color: #FFFFFF;
            text-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
        }
        
        h1 {
            background: linear-gradient(135deg, #FFFFFF 0%, #E0E0E0 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        /* Brighten standard text */
        p, li, span {
            color: #E0E0E0;
        }
        
        .stat-value {
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            font-size: 1.1rem;
        }
        
        .big-stat {
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(45deg, #FFFFFF, #A0A0A0);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        /* --- BADGES & TAGS --- */
        .badge {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .badge-success { background: rgba(0, 229, 255, 0.15); color: #00E5FF; border: 1px solid rgba(0, 229, 255, 0.3); }
        .badge-danger { background: rgba(255, 46, 99, 0.15); color: #FF2E63; border: 1px solid rgba(255, 46, 99, 0.3); }
        .badge-neutral { background: rgba(255, 255, 255, 0.1); color: #E0E0E0; border: 1px solid rgba(255, 255, 255, 0.2); }
        
        /* --- METRICS --- */
        div[data-testid="stMetricValue"] {
            font-family: 'JetBrains Mono', monospace;
            color: #FFFFFF !important;
        }
        
        div[data-testid="stMetricLabel"] {
            color: #E0E0E0 !important;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        /* --- BUTTONS --- */
        .stButton > button, div[data-testid="stButton"] > button {
            width: 100%;
            background: linear-gradient(135deg, #1F1F1F 0%, #2A2A2A 100%) !important;
            color: #FFFFFF !important;
            border: 1px solid #333 !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }
        
        .stButton > button::before, div[data-testid="stButton"] > button::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            border-radius: 50%;
            background: rgba(0, 229, 255, 0.2);
            transform: translate(-50%, -50%);
            transition: width 0.6s, height 0.6s;
        }
        
        .stButton > button:hover::before, div[data-testid="stButton"] > button:hover::before {
            width: 300px;
            height: 300px;
        }
        
        .stButton > button:hover, div[data-testid="stButton"] > button:hover {
            background: linear-gradient(135deg, #00E5FF 0%, #0099CC 100%) !important;
            color: #000000 !important;
            border-color: #00E5FF !important;
            box-shadow: 0 8px 25px rgba(0, 229, 255, 0.4);
            transform: translateY(-2px);
        }
        
        .stButton > button:active, div[data-testid="stButton"] > button:active {
            transform: translateY(0);
        }
        
        /* --- PROGRESS BARS --- */
        .stProgress > div > div > div > div {
            background-color: #00E5FF;
        }
        
        /* --- DATAFRAMES --- */
        div[data-testid="stDataFrame"] {
            border: 1px solid #222;
            border-radius: 8px;
            overflow: hidden;
        }
        
        /* --- PREVENT MARKDOWN AUTOLINK PARSING ERRORS --- */
        /* Ensure text rendering is clean and readable */
        .prop-card-wrapper, .prop-card {
            text-rendering: optimizeLegibility;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }
        
        .prop-card-wrapper * {
            color: inherit;
            font-family: inherit;
        }
        
        /* Ensure buttons are visible and styled correctly */
        .prop-card-wrapper + div[data-testid="stVerticalBlock"] {
            margin-top: 10px;
        }
        </style>
        """
    
    # Inject CSS globally using st.markdown
    st.markdown(css_content, unsafe_allow_html=True)

def render_header(title, subtitle=None):
    import html as html_module
    title_escaped = html_module.escape(str(title))
    subtitle_escaped = html_module.escape(str(subtitle)) if subtitle else ''
    st.markdown(f"""
        <div style="margin-bottom: 30px;">
            <h1 style="margin-bottom: 0; font-size: 3rem; color: #FFFFFF;">{title_escaped}</h1>
            {f'<p style="color: #E0E0E0; font-size: 1.2rem; margin-top: 5px;">{subtitle_escaped}</p>' if subtitle else ''}
        </div>
    """, unsafe_allow_html=True)
