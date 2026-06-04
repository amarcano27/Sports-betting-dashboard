"""
Database client.
Reads credentials from Streamlit secrets (Cloud) or .env (local).
"""
import os
from dotenv import load_dotenv
load_dotenv()


def _secret(key: str) -> str:
    """Read from st.secrets first, fall back to env var."""
    try:
        import streamlit as st
        v = st.secrets.get(key) or st.secrets.get(key.upper()) or st.secrets.get(key.lower())
        if v:
            return str(v)
    except Exception:
        pass
    return os.getenv(key, "")


SUPABASE_URL = _secret("SUPABASE_URL")
SUPABASE_KEY = _secret("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client, Client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        DB_MODE = "supabase"
    except Exception as e:
        from services.local_db import LocalDB
        supabase = LocalDB()
        DB_MODE = "sqlite"
else:
    from services.local_db import LocalDB
    supabase = LocalDB()
    DB_MODE = "sqlite"


def get_db_mode() -> str:
    return DB_MODE
