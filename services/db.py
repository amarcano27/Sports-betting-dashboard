"""
Database client — reads credentials from (in priority order):
  1. Streamlit secrets  (st.secrets) — used when deployed to Streamlit Cloud
  2. .env file / environment variables — used locally
  3. Falls back to local SQLite if neither is configured
"""
import os
from dotenv import load_dotenv

load_dotenv()

def _get_creds():
    # Priority 1: Streamlit secrets (Streamlit Cloud deployment)
    try:
        import streamlit as st
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY", "")
        if url and key:
            return url, key
    except Exception:
        pass
    # Priority 2: environment / .env
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    return url, key

SUPABASE_URL, SUPABASE_KEY = _get_creds()

if SUPABASE_URL and SUPABASE_KEY:
    from supabase import create_client, Client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    DB_MODE = "supabase"
else:
    from services.local_db import LocalDB
    supabase = LocalDB()
    DB_MODE = "sqlite"

print(f"[db] Using {DB_MODE} backend")
