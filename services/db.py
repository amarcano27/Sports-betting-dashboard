"""
Database client
===============
Reads credentials in priority order:
  1. Streamlit secrets  (st.secrets)  — Streamlit Cloud deployment
  2. Environment / .env               — local development
  3. Falls back to local SQLite       — if neither is configured
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _get(key: str) -> str:
    """Read a secret from st.secrets first, then os.environ."""
    # Try Streamlit secrets (works on Streamlit Cloud and locally with secrets.toml)
    try:
        import streamlit as st
        val = st.secrets.get(key, "")
        if val:
            return str(val)
    except Exception:
        pass
    # Fallback to environment variable / .env
    return os.getenv(key, "")


SUPABASE_URL = _get("SUPABASE_URL")
SUPABASE_KEY = _get("SUPABASE_KEY")
DB_MODE      = "sqlite"   # overwritten below if Supabase connects

if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client, Client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        DB_MODE = "supabase"
        print(f"[db] Using supabase backend ({SUPABASE_URL[:40]}...)")
    except Exception as e:
        print(f"[db] Supabase init failed ({e}), falling back to SQLite")
        from services.local_db import LocalDB
        supabase = LocalDB()
else:
    print("[db] No Supabase credentials found — using local SQLite fallback")
    from services.local_db import LocalDB
    supabase = LocalDB()
    DB_MODE = "sqlite"
