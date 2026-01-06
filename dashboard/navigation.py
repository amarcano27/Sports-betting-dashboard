"""
Navigation component for the dashboard
"""
import streamlit as st

def render_navigation():
    """Render navigation bar at the top"""
    st.markdown("""
    <style>
        .nav-container {
            display: flex;
            gap: 1rem;
            padding: 1rem 0;
            margin-bottom: 2rem;
            border-bottom: 2px solid #475569;
        }
        .nav-link {
            padding: 0.5rem 1.5rem;
            background: #334155;
            color: #cbd5e1;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 500;
            transition: all 0.2s;
            border: 1px solid #475569;
        }
        .nav-link:hover {
            background: #475569;
            color: white;
        }
        .nav-link.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-color: #667eea;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Get current page from query params or session state
    current_page = st.query_params.get("page", "home")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🏠 Home", use_container_width=True, 
                   type="primary" if current_page == "home" else "secondary"):
            st.query_params.page = "home"
            st.rerun()
    
    with col2:
        if st.button("🎯 Player Props", use_container_width=True,
                   type="primary" if current_page == "props" else "secondary"):
            st.query_params.page = "props"
            st.rerun()
    
    with col3:
        if st.button("💰 Moneylines", use_container_width=True,
                   type="primary" if current_page == "moneylines" else "secondary"):
            st.query_params.page = "moneylines"
            st.rerun()
    
    with col4:
        if st.button("📊 Analytics", use_container_width=True,
                   type="primary" if current_page == "analytics" else "secondary"):
            st.query_params.page = "analytics"
            st.rerun()

