"""
Fetch recent game stats for all players (for hitrate calculations)
This stores historical stats that will be used for analysis
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from services.nba_stats_api import NBAStatsAPI
import time

def fetch_recent_stats_for_players(limit=None):
    """Fetch recent stats for all players"""
    print("Fetching recent player stats...")
    
    # Get all active players
    query = supabase.table("players").select("*").eq("sport", "NBA")
    if limit:
        query = query.limit(limit)
    
    players = query.execute().data
    
    print(f"Found {len(players)} players")
    
    api = NBAStatsAPI()
    success_count = 0
    total_stats_stored = 0
    
    for i, player in enumerate(players, 1):
        player_name = player.get('name', 'Unknown')
        player_team = player.get('team', 'N/A')
        print(f"\n[{i}/{len(players)}] {player_name} ({player_team})...", end=" ")
        
        try:
            external_id = player.get("external_id")
            if not external_id:
                print("No external_id, skipping")
                continue
            
            # Get game log
            game_log = api.get_player_game_log(external_id)
            
            if not game_log:
                print("No games")
                continue
            
            print(f"Found {len(game_log)} games", end=" ")
            
            # Store all recent games (last 30)
            stored = 0
            for game_stat in game_log[:30]:  # Last 30 games
                if not game_stat.get("date"):
                    continue
                
                game_date = game_stat.get("date")
                
                # Check if stats already exist for this date
                existing = (
                    supabase.table("player_game_stats")
                    .select("id")
                    .eq("player_id", player["id"])
                    .eq("date", game_date)
                    .execute()
                    .data
                )
                
                if existing:
                    # Update
                    supabase.table("player_game_stats").update({
                        "opponent": game_stat.get("opponent"),
                        "home": game_stat.get("home", True),
                        "minutes_played": game_stat.get("minutes_played"),
                        "points": game_stat.get("points"),
                        "rebounds": game_stat.get("rebounds"),
                        "assists": game_stat.get("assists"),
                        "steals": game_stat.get("steals"),
                        "blocks": game_stat.get("blocks"),
                        "turnovers": game_stat.get("turnovers"),
                        "field_goals_made": game_stat.get("field_goals_made"),
                        "field_goals_attempted": game_stat.get("field_goals_attempted"),
                        "three_pointers_made": game_stat.get("three_pointers_made"),
                        "three_pointers_attempted": game_stat.get("three_pointers_attempted"),
                        "free_throws_made": game_stat.get("free_throws_made"),
                        "free_throws_attempted": game_stat.get("free_throws_attempted"),
                        "raw_data": game_stat.get("raw_data")
                    }).eq("id", existing[0]["id"]).execute()
                else:
                    # Insert (without game_id since we don't have matching games)
                    supabase.table("player_game_stats").insert({
                        "player_id": player["id"],
                        "date": game_date,
                        "opponent": game_stat.get("opponent"),
                        "home": game_stat.get("home", True),
                        "minutes_played": game_stat.get("minutes_played"),
                        "points": game_stat.get("points"),
                        "rebounds": game_stat.get("rebounds"),
                        "assists": game_stat.get("assists"),
                        "steals": game_stat.get("steals"),
                        "blocks": game_stat.get("blocks"),
                        "turnovers": game_stat.get("turnovers"),
                        "field_goals_made": game_stat.get("field_goals_made"),
                        "field_goals_attempted": game_stat.get("field_goals_attempted"),
                        "three_pointers_made": game_stat.get("three_pointers_made"),
                        "three_pointers_attempted": game_stat.get("three_pointers_attempted"),
                        "free_throws_made": game_stat.get("free_throws_made"),
                        "free_throws_attempted": game_stat.get("free_throws_attempted"),
                        "raw_data": game_stat.get("raw_data")
                    }).execute()
                    stored += 1
            
            if stored > 0:
                print(f"- Stored {stored} new")
                success_count += 1
                total_stats_stored += stored
            else:
                print("- Up to date")
            
            # Rate limiting
            time.sleep(0.5)  # Faster since we're not matching games
            
        except Exception as e:
            print(f"ERROR: {e}")
            continue
    
    print(f"\n[OK] Completed!")
    print(f"  - Successfully processed: {success_count}/{len(players)} players")
    print(f"  - Total stats stored: {total_stats_stored}")
    print(f"\nStats are now available for hitrate calculations and charts!")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="Limit number of players to process")
    args = parser.parse_args()
    
    fetch_recent_stats_for_players(limit=args.limit)

