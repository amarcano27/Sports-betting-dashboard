"""
Demo Data Loader - Fallback for when database is unavailable
Loads data from static JSON file for portfolio demonstration
"""
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Path to demo data
DEMO_DATA_PATH = Path(__file__).parent.parent / "data_archive" / "demo_data.json"

def load_demo_data():
    """Load demo data from JSON file and update timestamps to today"""
    try:
        with open(DEMO_DATA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Update game times to be today/tonight
        now = datetime.now(timezone.utc)
        today_evening = now.replace(hour=19, minute=30, second=0, microsecond=0)
        
        if data.get("games"):
            for i, game in enumerate(data["games"]):
                # Space games 3 hours apart starting at 7:30 PM today
                game_time = today_evening + timedelta(hours=i*3)
                game["start_time"] = game_time.isoformat()
        
        # Update prop snapshot times
        if data.get("prop_feed_snapshots"):
            snapshot_time = now - timedelta(hours=1)  # 1 hour ago
            for prop in data["prop_feed_snapshots"]:
                prop["snapshot_at"] = snapshot_time.isoformat()
        
        return data
    except Exception as e:
        print(f"Error loading demo data: {e}")
        return {"games": [], "players": [], "prop_feed_snapshots": []}

def get_demo_games(sport="NBA"):
    """Get demo games for a sport"""
    data = load_demo_data()
    games = [g for g in data.get("games", []) if g.get("sport") == sport]
    return games

def get_demo_props(sport="NBA", game_ids=None):
    """Get demo props for a sport"""
    data = load_demo_data()
    props = data.get("prop_feed_snapshots", [])
    
    if sport:
        props = [p for p in props if p.get("sport") == sport]
    
    if game_ids:
        props = [p for p in props if p.get("game_id") in game_ids]
    
    return props

def get_demo_players(sport="NBA"):
    """Get demo players for a sport"""
    data = load_demo_data()
    players = [p for p in data.get("players", []) if p.get("sport") == sport]
    return players

