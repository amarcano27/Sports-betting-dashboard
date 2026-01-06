"""Quick script to get player ID"""
import sys
from pathlib import Path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.db import supabase

# Search for Josh Hart
players = supabase.table("players").select("id, name, team").ilike("name", "%Josh Hart%").execute().data

if players:
    print(f"Found: {players[0]['name']} ({players[0]['team']})")
    print(f"ID: {players[0]['id']}")
else:
    # Get any Knicks player
    knicks = supabase.table("players").select("id, name, team").eq("team", "NYK").limit(1).execute().data
    if knicks:
        print(f"Sample player: {knicks[0]['name']} ({knicks[0]['team']})")
        print(f"ID: {knicks[0]['id']}")

