"""
Fetch DFS lines from third-party APIs (OpticOdds, WagerAPI, Odds-API.io)
This is the SAFE, legal way to get PrizePicks/Underdog data
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.dfs_api import get_all_dfs_props
from services.db import supabase
from rapidfuzz import process
from datetime import datetime


def store_dfs_lines_from_api(sport_key: str = "nba"):
    """
    Fetch DFS lines from APIs and store in database
    
    Args:
        sport_key: Sport key (nba, nfl, etc.)
    """
    print(f"Fetching DFS lines for {sport_key.upper()}...")
    
    # Fetch props from all available APIs
    props = get_all_dfs_props(sport_key)
    
    if not props:
        print("No DFS props found. Make sure you have at least one API key configured:")
        print("  - DAILYFANTASYAPI_KEY (recommended - most popular solution)")
        print("    → Sign up: https://www.dailyfantasyapi.io")
        print("  - OPTICODDS_API_KEY (for PrizePicks via OpticOdds)")
        print("  - ODDS_API_IO_KEY (for Underdog via Odds-API.io)")
        print("  - WAGERAPI_KEY (for both via WagerAPI)")
        return
    
    print(f"Found {len(props)} DFS props to process")
    
    # Load all players for matching
    print("Loading players for matching...")
    sport_label = "NBA" if sport_key == "nba" else sport_key.upper()
    all_players = supabase.table("players").select("id,name").eq("sport", sport_label).execute().data
    player_names = {p["name"]: p["id"] for p in all_players}
    print(f"Loaded {len(player_names)} players")
    
    stored = 0
    skipped = 0
    
    for prop in props:
        try:
            player_name = prop.get("player_name")
            if not player_name:
                continue
            
            # Find player by name (exact match first, then fuzzy)
            player_id = None
            
            # Strategy 1: Exact match (case-insensitive)
            for db_name, db_id in player_names.items():
                if db_name.lower() == player_name.lower():
                    player_id = db_id
                    break
            
            # Strategy 2: Fuzzy match
            if not player_id:
                matches = process.extract(player_name, list(player_names.keys()), limit=1, score_cutoff=85)
                if matches:
                    matched_name = matches[0][0]
                    player_id = player_names[matched_name]
            
            if not player_id:
                skipped += 1
                if skipped <= 5:
                    print(f"  Player '{player_name}' not found in database")
                continue
            
            # Find game (optional - can be None)
            game_id = None
            # TODO: Match game based on date/teams if available in prop data
            
            # Store DFS line
            record = {
                "player_id": player_id,
                "prop_type": prop.get("prop_type"),
                "line": prop.get("line"),
                "side": prop.get("side"),
                "source": prop.get("source", "unknown"),
                "scraped_at": datetime.now().isoformat()
            }
            
            if game_id:
                record["game_id"] = game_id
            
            # Insert or update
            try:
                supabase.table("dfs_lines").upsert(
                    record,
                    on_conflict="player_id,prop_type,line,source,game_id"
                ).execute()
                stored += 1
            except Exception as e:
                print(f"  Error storing DFS line for {player_name}: {e}")
                continue
                
        except Exception as e:
            print(f"Error processing prop: {e}")
            continue
    
    print(f"\n✅ Done!")
    print(f"  Stored: {stored} DFS lines")
    print(f"  Skipped: {skipped} (player not found)")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch DFS lines from third-party APIs")
    parser.add_argument("--sport", default="nba", help="Sport key (nba, nfl, etc.)")
    args = parser.parse_args()
    
    store_dfs_lines_from_api(args.sport)

