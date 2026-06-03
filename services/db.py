"""
Database client — uses Supabase if SUPABASE_URL is configured,
otherwise falls back to local SQLite (via services/local_db.py).
"""
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

if SUPABASE_URL and SUPABASE_KEY:
    from supabase import create_client, Client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    DB_MODE = "supabase"
else:
    from services.local_db import LocalDB
    supabase = LocalDB()
    DB_MODE = "sqlite"

print(f"[db] Using {DB_MODE} backend")
