"""
PREMIUM MILLION-DOLLAR UI STYLES
Enhanced visual design with animations, gradients, and premium effects
"""
import streamlit as st

def apply_premium_theme():
    """Apply premium million-dollar styling"""
    st.markdown("""
<style>
    /* ========== PREMIUM FONTS ========== */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    
    /* ========== PREMIUM BACKGROUND ========== */
    .stApp {
        background: #000000;
        background-image: 
            radial-gradient(circle at 10% 20%, rgba(0, 229, 255, 0.08) 0%, transparent 30%),
            radial-gradient(circle at 90% 80%, rgba(138, 43, 226, 0.08) 0%, transparent 30%),
            radial-gradient(circle at 50% 50%, rgba(255, 46, 99, 0.05) 0%, transparent 40%),
            linear-gradient(180deg, #0a0a0a 0%, #000000 100%);
        background-attachment: fixed;
    }
    
    /* ========== ANIMATED GRADIENT OVERLAY ========== */
    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: 
            radial-gradient(600px circle at var(--mouse-x, 50%) var(--mouse-y, 50%), 
                rgba(0, 229, 255, 0.06), 
                transparent 40%);
        pointer-events: none;
        z-index: 0;
    }
    
    /* ========== SIDEBAR PREMIUM ========== */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0a0a 0%, #000000 100%);
        border-right: 1px solid rgba(0, 229, 255, 0.1);
        box-shadow: 4px 0 24px rgba(0, 0, 0, 0.5);
    }
    
    section[data-testid="stSidebar"]::before {
        content: '';
        position: absolute;
        top: 0;
        right: 0;
        width: 1px;
        height: 100%;
        background: linear-gradient(180deg, 
            transparent 0%, 
            rgba(0, 229, 255, 0.5) 50%, 
            transparent 100%);
        animation: sidebarGlow 3s ease-in-out infinite;
    }
    
    @keyframes sidebarGlow {
        0%, 100% { opacity: 0.3; }
        50% { opacity: 1; }
    }
    
    [data-testid="stSidebarNav"] span,
    [data-testid="stSidebarNav"] a {
        color: #FFFFFF !important;
        font-weight: 600;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    [data-testid="stSidebarNav"] a:hover {
        color: #00E5FF !important;
        transform: translateX(4px);
    }
    
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] label {
        color: #FFFFFF !important;
        font-weight: 700;
    }
    
    /* ========== PREMIUM CARDS ========== */
    .prop-card {
        background: linear-gradient(135deg, 
            rgba(20, 20, 20, 0.95) 0%, 
            rgba(26, 26, 26, 0.95) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 20px;
        position: relative;
        overflow: hidden;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 
            0 4px 24px rgba(0, 0, 0, 0.4),
            inset 0 1px 0 rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(20px);
    }
    
    .prop-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, 
            transparent, 
            rgba(0, 229, 255, 0.8), 
            rgba(138, 43, 226, 0.8),
            transparent);
        opacity: 0;
        transition: opacity 0.4s;
    }
    
    .prop-card::after {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(0, 229, 255, 0.1) 0%, transparent 70%);
        opacity: 0;
        transition: opacity 0.6s;
    }
    
    .prop-card:hover {
        border-color: rgba(0, 229, 255, 0.4);
        transform: translateY(-8px) scale(1.02);
        box-shadow: 
            0 20px 60px rgba(0, 229, 255, 0.2),
            0 0 40px rgba(138, 43, 226, 0.1),
            inset 0 1px 0 rgba(255, 255, 255, 0.1);
    }
    
    .prop-card:hover::before {
        opacity: 1;
        animation: shimmer 2s linear infinite;
    }
    
    .prop-card:hover::after {
        opacity: 1;
    }
    
    @keyframes shimmer {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
    }
    
    /* ========== PREMIUM TYPOGRAPHY ========== */
    h1, h2, h3, h4, h5, h6 {
        font-weight: 800;
        letter-spacing: -0.02em;
        background: linear-gradient(135deg, #FFFFFF 0%, #E0E0E0 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-shadow: none;
        position: relative;
    }
    
    h1 {
        font-size: 3.5rem !important;
        line-height: 1.1;
        margin-bottom: 0.5rem;
    }
    
    h2 {
        font-size: 2.5rem !important;
        margin-top: 2rem;
    }
    
    p, li, span, div {
        color: #E0E0E0;
        line-height: 1.7;
    }
    
    /* ========== PREMIUM BUTTONS ========== */
    .stButton > button, div[data-testid="stButton"] > button {
        width: 100%;
        background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        padding: 12px 24px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.02em !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        position: relative !important;
        overflow: hidden !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
    }
    
    .stButton > button::before, div[data-testid="stButton"] > button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, 
            transparent, 
            rgba(255, 255, 255, 0.1), 
            transparent);
        transition: left 0.5s;
    }
    
    .stButton > button:hover::before, div[data-testid="stButton"] > button:hover::before {
        left: 100%;
    }
    
    .stButton > button:hover, div[data-testid="stButton"] > button:hover {
        background: linear-gradient(135deg, #00E5FF 0%, #00B8CC 100%) !important;
        color: #000000 !important;
        border-color: #00E5FF !important;
        transform: translateY(-2px) !important;
        box-shadow: 
            0 12px 24px rgba(0, 229, 255, 0.3),
            0 0 40px rgba(0, 229, 255, 0.2) !important;
    }
    
    .stButton > button:active, div[data-testid="stButton"] > button:active {
        transform: translateY(0) !important;
    }
    
    /* ========== PREMIUM METRICS ========== */
    div[data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 2.5rem !important;
        font-weight: 700 !important;
        background: linear-gradient(135deg, #FFFFFF 0%, #00E5FF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    div[data-testid="stMetricLabel"] {
        color: #CCCCCC !important;
        font-size: 0.85rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
        font-weight: 600 !important;
    }
    
    /* ========== PREMIUM INPUTS ========== */
    .stSelectbox, .stMultiSelect, .stTextInput, .stNumberInput {
        transition: all 0.3s;
    }
    
    .stSelectbox > div > div,
    .stMultiSelect > div > div,
    .stTextInput > div > div,
    .stNumberInput > div > div {
        background: rgba(26, 26, 26, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        color: #FFFFFF !important;
        backdrop-filter: blur(10px);
        transition: all 0.3s;
    }
    
    .stSelectbox > div > div:hover,
    .stMultiSelect > div > div:hover,
    .stTextInput > div > div:hover,
    .stNumberInput > div > div:hover {
        border-color: rgba(0, 229, 255, 0.4) !important;
        box-shadow: 0 0 20px rgba(0, 229, 255, 0.1);
    }
    
    /* ========== PREMIUM CHECKBOX/RADIO ========== */
    .stCheckbox, .stRadio {
        color: #FFFFFF !important;
    }
    
    /* ========== PREMIUM DATAFRAMES ========== */
    div[data-testid="stDataFrame"] {
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        backdrop-filter: blur(10px);
    }
    
    /* ========== PREMIUM PROGRESS BARS ========== */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #00E5FF 0%, #8A2BE2 100%);
        box-shadow: 0 0 20px rgba(0, 229, 255, 0.5);
    }
    
    /* ========== PREMIUM BADGES ========== */
    .badge {
        padding: 6px 12px;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        display: inline-block;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }
    
    .badge-success { 
        background: linear-gradient(135deg, rgba(0, 229, 255, 0.2) 0%, rgba(0, 229, 255, 0.1) 100%);
        color: #00E5FF;
        border: 1px solid rgba(0, 229, 255, 0.4);
        box-shadow: 0 0 20px rgba(0, 229, 255, 0.2);
    }
    
    .badge-danger { 
        background: linear-gradient(135deg, rgba(255, 46, 99, 0.2) 0%, rgba(255, 46, 99, 0.1) 100%);
        color: #FF2E63;
        border: 1px solid rgba(255, 46, 99, 0.4);
        box-shadow: 0 0 20px rgba(255, 46, 99, 0.2);
    }
    
    .badge-neutral { 
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.15) 0%, rgba(255, 255, 255, 0.05) 100%);
        color: #E0E0E0;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    /* ========== PREMIUM SCROLLBAR ========== */
    ::-webkit-scrollbar {
        width: 12px;
        height: 12px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(0, 0, 0, 0.3);
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #00E5FF 0%, #8A2BE2 100%);
        border-radius: 6px;
        border: 2px solid rgba(0, 0, 0, 0.3);
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(180deg, #00F5FF 0%, #9A3BF2 100%);
        box-shadow: 0 0 10px rgba(0, 229, 255, 0.5);
    }
    
    /* ========== PREMIUM ANIMATIONS ========== */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes pulse {
        0%, 100% {
            opacity: 1;
        }
        50% {
            opacity: 0.7;
        }
    }
    
    @keyframes glow {
        0%, 100% {
            box-shadow: 0 0 20px rgba(0, 229, 255, 0.2);
        }
        50% {
            box-shadow: 0 0 40px rgba(0, 229, 255, 0.4);
        }
    }
    
    /* ========== HIDE STREAMLIT BRANDING ========== */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* ========== PREMIUM LOADING STATES ========== */
    .stSpinner > div {
        border-color: #00E5FF transparent transparent transparent !important;
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    /* ========== PREMIUM DIVIDERS ========== */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, 
            transparent 0%, 
            rgba(0, 229, 255, 0.5) 50%, 
            transparent 100%);
        margin: 2rem 0;
    }
    
    /* ========== PREMIUM ALERTS ========== */
    .stAlert {
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
</style>
""", unsafe_allow_html=True)


