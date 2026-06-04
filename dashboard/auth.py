"""
Lightweight admin auth for APEX Analytics.
Password stored in .streamlit/secrets.toml (local) and Streamlit Cloud secrets.
Session-scoped — you unlock once per browser session.
"""
import os
import hashlib
import streamlit as st


def _get_admin_password() -> str:
    """Read password from Streamlit secrets, then .env fallback."""
    try:
        return st.secrets.get("ADMIN_PASSWORD", "")
    except Exception:
        pass
    return os.getenv("ADMIN_PASSWORD", "")


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def require_admin(prompt: str = "Enter admin password to continue") -> bool:
    """
    Returns True if the user is authenticated for this session.
    Shows a password input if not. Call at the top of any gated section.

    Usage:
        if require_admin():
            st.button("Do sensitive thing")
    """
    if st.session_state.get("apex_admin_unlocked"):
        return True

    correct_hash = _hash(_get_admin_password())

    with st.form("admin_auth_form", clear_on_submit=True):
        st.markdown(
            "🔐 **Admin Required**",
            help="Only the account owner can trigger data refreshes.",
        )
        pw = st.text_input(prompt, type="password", label_visibility="collapsed",
                           placeholder="Password…")
        submitted = st.form_submit_button("Unlock", use_container_width=True)

    if submitted:
        if _hash(pw) == correct_hash:
            st.session_state["apex_admin_unlocked"] = True
            st.success("✅ Unlocked for this session.")
            st.rerun()
        else:
            st.error("Incorrect password.")

    return False


def admin_lock_button():
    """Optional: show a 'Lock session' button in the sidebar."""
    if st.session_state.get("apex_admin_unlocked"):
        if st.sidebar.button("🔒 Lock session"):
            st.session_state["apex_admin_unlocked"] = False
            st.rerun()
