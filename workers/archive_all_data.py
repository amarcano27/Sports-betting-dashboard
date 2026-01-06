"""
CRITICAL: Archive all API data before subscription expires
This script fetches ALL available data and saves it permanently
"""
import sys
from pathlib import Path
import json
from datetime import datetime
import time

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.odds_api import get_odds_for_sport, get_player_props
from services.db import supabase
import traceback

# Create archive directory
ARCHIVE_DIR = project_root / "data_archive"
ARCHIVE_DIR.mkdir(exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

SPORTS = {
    "NBA": "basketball_nba",
    "NFL": "americanfootball_nfl",
    "MLB": "baseball_mlb",
    "NHL": "icehockey_nhl",
    "NCAAB": "basketball_ncaab",
    "NCAAF": "americanfootball_ncaaf",
}

def archive_to_json(data, filename):
    """Save data to JSON file"""
    filepath = ARCHIVE_DIR / f"{timestamp}_{filename}"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str)
    print(f"Archived to {filepath}")
    return filepath

def fetch_and_archive_odds():
    """Fetch odds for all sports and archive"""
    print("\n" + "="*60)
    print("FETCHING ODDS DATA")
    print("="*60)
    
    all_odds = {}
    
    for sport_name, sport_key in SPORTS.items():
        try:
            print(f"\nFetching {sport_name} odds...")
            odds_data = get_odds_for_sport(sport_key)
            all_odds[sport_name] = odds_data
            print(f"   Got {len(odds_data)} events")
            time.sleep(1)  # Rate limiting
        except Exception as e:
            print(f"   ✗ Error: {e}")
            all_odds[sport_name] = []
    
    # Archive all odds
    archive_to_json(all_odds, "odds_complete.json")
    return all_odds

def fetch_and_archive_player_props():
    """Fetch player props and archive"""
    print("\n" + "="*60)
    print("FETCHING PLAYER PROPS")
    print("="*60)
    
    all_props = {}
    
    # Focus on NBA (most active)
    for sport_name, sport_key in [("NBA", "basketball_nba")]:
        try:
            print(f"\nFetching {sport_name} player props...")
            props_data = get_player_props(sport_key)
            all_props[sport_name] = props_data
            print(f"   Got {len(props_data)} events with props")
            time.sleep(1)
        except Exception as e:
            print(f"   ✗ Error: {e}")
            all_props[sport_name] = []
    
    # Archive props
    archive_to_json(all_props, "player_props_complete.json")
    return all_props

def export_database_snapshot():
    """Export current database state"""
    print("\n" + "="*60)
    print("EXPORTING DATABASE SNAPSHOT")
    print("="*60)
    
    snapshot = {}
    
    tables = ["games", "players", "odds_snapshots", "player_prop_odds", 
              "player_injuries", "prop_feed_snapshots"]
    
    for table in tables:
        try:
            print(f"\nExporting {table}...")
            # Get all records (with pagination if needed)
            data = supabase.table(table).select("*").limit(10000).execute().data
            snapshot[table] = data
            print(f"   Exported {len(data)} records")
        except Exception as e:
            print(f"   ✗ Error: {e}")
            snapshot[table] = []
    
    # Archive snapshot
    archive_to_json(snapshot, "database_snapshot.json")
    return snapshot

def store_odds_to_db(all_odds):
    """Store fetched odds to database"""
    print("\n" + "="*60)
    print("STORING ODDS TO DATABASE")
    print("="*60)
    
    for sport_name, odds_data in all_odds.items():
        if not odds_data:
            continue
            
        print(f"\nStoring {sport_name} data...")
        games_stored = 0
        odds_stored = 0
        
        for event in odds_data:
            try:
                # Store game
                start_time = datetime.fromisoformat(event["commence_time"].replace("Z", "+00:00"))
                game_data = {
                    "sport": sport_name,
                    "external_id": event["id"],
                    "home_team": event["home_team"],
                    "away_team": event["away_team"],
                    "start_time": start_time.isoformat(),
                    "status": "scheduled"
                }
                game_resp = supabase.table("games").upsert(game_data, on_conflict="external_id").execute()
                
                if game_resp.data:
                    game_id = game_resp.data[0]["id"]
                    games_stored += 1
                    
                    # Store odds
                    for bookmaker in event.get("bookmakers", []):
                        for market in bookmaker.get("markets", []):
                            for outcome in market.get("outcomes", []):
                                odds_record = {
                                    "game_id": game_id,
                                    "book": bookmaker["key"],
                                    "market_type": market["key"],
                                    "market_label": outcome["name"],
                                    "price": outcome["price"],
                                    "line": outcome.get("point")
                                }
                                supabase.table("odds_snapshots").insert(odds_record).execute()
                                odds_stored += 1
                                
            except Exception as e:
                print(f"   Error storing event: {e}")
                continue
        
        print(f"   Stored {games_stored} games, {odds_stored} odds")

def main():
    print("\n" + "="*60)
    print("CRITICAL DATA ARCHIVE - API SUBSCRIPTION EXPIRING")
    print("="*60)
    print(f"Archive Directory: {ARCHIVE_DIR}")
    print(f"Timestamp: {timestamp}")
    
    try:
        # 1. Export current database
        print("\n[1/4] Exporting current database...")
        export_database_snapshot()
        
        # 2. Fetch fresh odds
        print("\n[2/4] Fetching fresh odds data...")
        all_odds = fetch_and_archive_odds()
        
        # 3. Fetch player props
        print("\n[3/4] Fetching player props...")
        all_props = fetch_and_archive_player_props()
        
        # 4. Store to database
        print("\n[4/4] Storing to database...")
        store_odds_to_db(all_odds)
        
        print("\n" + "="*60)
        print("ARCHIVE COMPLETE")
        print("="*60)
        print(f"\nAll data saved to: {ARCHIVE_DIR}")
        print(f"Files created:")
        for f in ARCHIVE_DIR.glob(f"{timestamp}_*"):
            print(f"  - {f.name}")
        
    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

