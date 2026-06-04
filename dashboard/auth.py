"""
APEX Analytics Auth
===================
Two levels of protection:

1. APP LOGIN  — gates the entire dashboard. Anyone who opens the URL
   must enter the password before they can see anything.
   Unlocked once per browser session.

2. ADMIN GATE — gates destructive actions (odds fetch, data sync).
   Same password, tracked separately so the UI can show "logged in as admin".

Password stored in:
  - .streamlit/secrets.toml  (Streamlit Cloud & local with secrets file)
  - .env                     (local fallback)
"""
import os
import hashlib
import streamlit as st

# ─────────────────────────────────────────────────────────────
# SHARED HELPERS
# ─────────────────────────────────────────────────────────────

def _get_password() -> str:
    """Read ADMIN_PASSWORD from Streamlit secrets → .env fallback."""
    try:
        v = st.secrets.get("ADMIN_PASSWORD", "")
        if v:
            return v
    except Exception:
        pass
    return os.getenv("ADMIN_PASSWORD", "")


def _hash(s: str) -> str:
    return hashlib.sha256(s.strip().encode()).hexdigest()


# ─────────────────────────────────────────────────────────────
# LEVEL 1 — APP LOGIN WALL
# ─────────────────────────────────────────────────────────────

_LOGIN_CSS = """
<style>
/* ── Hide all default Streamlit chrome on login page ── */
#MainMenu, header, footer,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
[data-testid="stSidebarNav"],
section[data-testid="stSidebar"] { display: none !important; }

/* ── Full-page centred flex layout ── */
.stApp {
    background: #050B14 !important;
}
[data-testid="stMain"] .block-container {
    max-width: 400px !important;
    padding: 0 24px !important;
    margin: 0 auto !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    min-height: 100vh !important;
}

/* ── Form fields ── */
[data-testid="stTextInput"] input {
    background: #0F172A !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
    color: #F8FAFC !important;
    font-size: 15px !important;
    padding: 12px 14px !important;
    text-align: center !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #06B6D4 !important;
    box-shadow: 0 0 0 2px rgba(6,182,212,0.25) !important;
}
[data-testid="stTextInput"] input::placeholder { color: #475569 !important; }

/* ── Sign In button ── */
[data-testid="stFormSubmitButton"] button {
    background: #06B6D4 !important;
    color: #050B14 !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 800 !important;
    font-size: 15px !important;
    letter-spacing: 0.04em !important;
    padding: 12px !important;
    width: 100% !important;
    transition: opacity 0.15s !important;
}
[data-testid="stFormSubmitButton"] button:hover { opacity: 0.88 !important; }

/* ── Error message ── */
[data-testid="stAlert"] {
    border-radius: 8px !important;
    text-align: center !important;
}
</style>
"""

def login_wall() -> bool:
    """
    Renders a clean centered login screen.
    Returns True once authenticated, False (+ renders form) when not.
    """
    if st.session_state.get("apex_logged_in"):
        return True

    # Inject login-page CSS (hides sidebar, centres content)
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)

    # Branding header
    st.markdown(
        """
        <div style="text-align:center;padding:40px 0 28px">
          <div style="font-size:52px;line-height:1">⚡</div>
          <div style="font-size:26px;font-weight:900;color:#F8FAFC;
                      letter-spacing:-0.03em;margin-top:10px">
            APEX Analytics
          </div>
          <div style="font-size:13px;color:#475569;margin-top:6px;font-weight:500">
            Enter your password to continue
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Login form
    with st.form("apex_login", clear_on_submit=True):
        pw = st.text_input("pw", type="password",
                           placeholder="Password",
                           label_visibility="collapsed")
        submitted = st.form_submit_button("Sign In", use_container_width=True,
                                          type="primary")

    if submitted:
        correct = _get_password()
        if correct and _hash(pw) == _hash(correct):
            st.session_state["apex_logged_in"]      = True
            st.session_state["apex_admin_unlocked"] = True
            st.rerun()
        else:
            st.error("Incorrect password")

    return False


def logout_button():
    """Renders a 'Sign out' button in the sidebar."""
    if st.session_state.get("apex_logged_in"):
        with st.sidebar:
            st.markdown("---")
            if st.button("🚪 Sign out", use_container_width=True):
                st.session_state.clear()
                st.rerun()


# ─────────────────────────────────────────────────────────────
# LEVEL 2 — ADMIN GATE (for data-destructive actions)
# ─────────────────────────────────────────────────────────────

def require_admin(prompt: str = "Enter password to unlock") -> bool:
    """
    Returns True if the admin gate is unlocked for this session.
    Since login_wall() already validates the same password, once you're
    logged in the admin gate is automatically open.
    """
    # If already logged in via the app wall, admin is unlocked too
    if st.session_state.get("apex_logged_in") or st.session_state.get("apex_admin_unlocked"):
        st.session_state["apex_admin_unlocked"] = True
        return True

    # Standalone admin prompt (for local use without the login wall)
    with st.form("admin_auth_form", clear_on_submit=True):
        st.markdown("🔐 **Admin access required**")
        pw = st.text_input(prompt, type="password",
                           label_visibility="collapsed", placeholder="Password…")
        submitted = st.form_submit_button("Unlock", use_container_width=True)

    if submitted:
        correct = _get_password()
        if correct and _hash(pw) == _hash(correct):
            st.session_state["apex_admin_unlocked"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")

    return False


def admin_lock_button():
    """Show a lock-session button in the sidebar (legacy — use logout_button instead)."""
    if st.session_state.get("apex_admin_unlocked"):
        if st.sidebar.button("🔒 Lock session"):
            st.session_state["apex_admin_unlocked"] = False
            st.rerun()
