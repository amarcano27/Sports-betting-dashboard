"""
Database client — lazy Supabase initialization.

Credential resolution order:
  1. Streamlit secrets (st.secrets)  — Streamlit Cloud
  2. Environment variables / .env    — local development
  3. Local SQLite fallback           — if neither configured
"""
import os
from dotenv import load_dotenv
load_dotenv()

# ── Lazy client wrapper ──────────────────────────────────────
# We delay reading st.secrets until the first DB call so that
# the Streamlit runtime is guaranteed to be fully initialized.

_client = None
_db_mode = None


def _resolve(key: str) -> str:
    """Read a key from st.secrets → os.environ, in that order."""
    # Streamlit secrets (works on Streamlit Cloud and locally with secrets.toml)
    try:
        import streamlit as st
        # Use dict-style access first (works when the key exists)
        if hasattr(st, "secrets"):
            try:
                return str(st.secrets[key])
            except KeyError:
                pass
            # Fallback to .get() in case of different Streamlit version
            val = st.secrets.get(key, "")
            if val:
                return str(val)
    except Exception:
        pass
    # Environment variable / .env
    return os.getenv(key, "")


def _init():
    global _client, _db_mode
    if _client is not None:
        return

    url = _resolve("SUPABASE_URL")
    key = _resolve("SUPABASE_KEY")

    if url and key:
        try:
            from supabase import create_client
            _client  = create_client(url, key)
            _db_mode = "supabase"
            print(f"[db] ✓ Supabase connected ({url[:45]}...)")
            return
        except Exception as e:
            print(f"[db] ✗ Supabase init failed: {e}")

    print("[db] ✗ No Supabase credentials — using SQLite fallback")
    from services.local_db import LocalDB
    _client  = LocalDB()
    _db_mode = "sqlite"


class _LazyDB:
    """Proxy that initialises the real client on first use."""

    def __getattr__(self, name):
        _init()
        return getattr(_client, name)

    def table(self, *args, **kwargs):
        _init()
        return _client.table(*args, **kwargs)


supabase = _LazyDB()


def get_db_mode() -> str:
    _init()
    return _db_mode or "unknown"


# Legacy alias — module-level string updated on first access
# (pages that do `from services.db import DB_MODE` get the string directly)
def _lazy_db_mode():
    _init()
    return _db_mode or "unknown"
