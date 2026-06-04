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

def login_wall() -> bool:
    """
    Call at the top of main.py BEFORE st.navigation().
    Returns True if the user is authenticated; False + renders login screen if not.

    Usage in main.py:
        if not login_wall():
            st.stop()
    """
    if st.session_state.get("apex_logged_in"):
        return True

    # Full-page login screen (set_page_config already called by main.py)
    col = st.columns([1, 2, 1])[1]   # centre column
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="text-align:center;margin-bottom:32px">
              <div style="font-size:48px">⚡</div>
              <div style="font-size:28px;font-weight:900;color:#F8FAFC;letter-spacing:-0.03em">
                APEX Analytics
              </div>
              <div style="font-size:14px;color:#64748B;margin-top:4px">
                Private betting dashboard
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("apex_login", clear_on_submit=True):
            pw = st.text_input("Password", type="password",
                               placeholder="Enter password…",
                               label_visibility="collapsed")
            submitted = st.form_submit_button("Sign In", use_container_width=True,
                                              type="primary")

        if submitted:
            correct = _get_password()
            if correct and _hash(pw) == _hash(correct):
                st.session_state["apex_logged_in"]      = True
                st.session_state["apex_admin_unlocked"] = True   # admin too
                st.rerun()
            else:
                st.error("Incorrect password — try again.")

        st.markdown(
            "<div style='text-align:center;margin-top:24px;"
            "font-size:12px;color:#475569'>Personal use only</div>",
            unsafe_allow_html=True,
        )

    return False   # not logged in yet


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
