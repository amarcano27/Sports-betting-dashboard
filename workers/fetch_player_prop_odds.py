"""
Worker to fetch and store player prop odds
"""
import sys
from pathlib import Path
import json
from rapidfuzz import process

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from services.odds_api import get_player_props


def store_player_prop_odds(sport_key="basketball_nba"):
    """
    Fetch and store player prop odds.
    
    Args:
        sport_key: Sport key for the API
    """
    print("Fetching player prop odds...")
    props_data = get_player_props(sport_key)
    
    if not props_data:
        print("No player prop odds available")
        return
    
    print(f"Found {len(props_data)} events with player props")
    
    # Load all players once at the start for efficient matching
    print("Loading players from database...")
    all_players = supabase.table("players").select("id,name").eq("sport", "NBA").execute().data
    if not all_players:
        print("No players in database. Run: python workers/fetch_player_stats.py --sync-players")
        return
    
    print(f"Loaded {len(all_players)} players for matching")
    player_names = {p["name"]: p["id"] for p in all_players}
    
    props_stored = 0
    props_skipped = 0
    
    for event in props_data:
        # Find or create game
        game_resp = supabase.table("games").select("id").eq("external_id", event["id"]).execute()
        
        if not game_resp.data:
            print(f"Game {event['id']} not found, skipping...")
            continue
        
        game_id = game_resp.data[0]["id"]
        
        # Process bookmakers
        for bookmaker in event.get("bookmakers", []):
            book_name = bookmaker["title"]
            
            # Look for player props in markets
            # According to v4 API docs, markets are like: player_points, player_rebounds, etc.
            for market in bookmaker.get("markets", []):
                market_key = market.get("key", "")
                
                # Check if this is a player prop market
                # NBA: player_points, player_rebounds, player_assists, player_threes, player_pra, etc.
                # NFL: player_pass_tds, player_pass_yds, player_rush_yds, etc.
                if not market_key.startswith("player_"):
                    continue
                
                # Map market key to prop type
                market_to_prop_type = {
                    "player_points": "points",
                    "player_rebounds": "rebounds",
                    "player_assists": "assists",
                    "player_threes": "threes",
                    "player_steals": "steals",
                    "player_blocks": "blocks",
                    "player_turnovers": "turnovers",
                    "player_pra": "pra",
                    # NFL props
                    "player_pass_tds": "pass_tds",
                    "player_pass_yds": "pass_yds",
                    "player_pass_completions": "pass_completions",
                    "player_rush_yds": "rush_yds",
                    "player_rush_attempts": "rush_attempts",
                    "player_receptions": "receptions",
                    "player_reception_yds": "reception_yds",
                }
                
                prop_type = market_to_prop_type.get(market_key, market_key.replace("player_", ""))
                
                # Process outcomes - v4 API structure:
                # outcomes have: name ("Over"/"Under"), description (player name), point (line), price (odds)
                for outcome in market.get("outcomes", []):
                    # Extract player name from description (v4 API format)
                    player_name = outcome.get("description", "")
                    if not player_name:
                        continue
                    
                    # Get line and price
                    line = outcome.get("point")
                    price = outcome.get("price")
                    outcome_name = outcome.get("name", "").lower()
                    
                    if not line or price is None:
                        continue
                    
                    # Try to find player in database using multiple matching strategies
                    player_id = None
                    
                    # Strategy 1: Exact match (case-insensitive)
                    for db_name, db_id in player_names.items():
                        if db_name.lower() == player_name.lower():
                            player_id = db_id
                            break
                    
                    # Strategy 2: Partial match (contains)
                    if not player_id:
                        for db_name, db_id in player_names.items():
                            if player_name.lower() in db_name.lower() or db_name.lower() in player_name.lower():
                                player_id = db_id
                                break
                    
                    # Strategy 3: Fuzzy matching with lower threshold (70 instead of 80)
                    if not player_id:
                        matches = process.extract(player_name, list(player_names.keys()), limit=1, score_cutoff=70)
                        if matches:
                            matched_name = matches[0][0]
                            player_id = player_names[matched_name]
                    
                    if not player_id:
                        props_skipped += 1
                        if props_skipped <= 10:  # Only print first 10 to avoid spam
                            print(f"Player '{player_name}' not found in database (from market {market_key})")
                        continue
                    
                    # Determine if over or under
                    is_over = outcome_name == "over"
                    
                    # Store prop odds - need to handle both over and under for same prop
                    # First, try to find existing record
                    existing = supabase.table("player_prop_odds").select("id").eq(
                        "player_id", player_id
                    ).eq("game_id", game_id).eq("book", book_name).eq("prop_type", prop_type).eq("line", line).execute()
                    
                    if existing.data:
                        # Update existing record
                        prop_record = existing.data[0]
                        if is_over:
                            prop_record["over_price"] = price
                        else:
                            prop_record["under_price"] = price
                        prop_record["raw"] = outcome
                        supabase.table("player_prop_odds").update(prop_record).eq("id", prop_record["id"]).execute()
                    else:
                        # Insert new record
                        prop_record = {
                            "player_id": player_id,
                            "game_id": game_id,
                            "book": book_name,
                            "prop_type": prop_type,
                            "line": line,
                            "raw": outcome
                        }
                        if is_over:
                            prop_record["over_price"] = price
                        else:
                            prop_record["under_price"] = price
                        supabase.table("player_prop_odds").insert(prop_record).execute()
                        props_stored += 1
    
    print(f"\nDone storing player prop odds!")
    print(f"Props stored: {props_stored}")
    print(f"Props skipped (player not found): {props_skipped}")


if __name__ == "__main__":
    store_player_prop_odds()

