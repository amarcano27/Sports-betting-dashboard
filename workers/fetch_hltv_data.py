"""
Worker to fetch real match data from HLTV and populate player_game_stats
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timezone
import time

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from services.hltv_service import hltv

def fetch_player_match_history(player_id, player_name, team_name=None, limit=10):
    """
    Fetch real match history from HLTV for a player.
    """
    print(f"Fetching HLTV data for {player_name}...")
    
    # Use the improved service method
    player_stats = hltv.get_player_match_history(player_name, team_name, limit=limit)
    
    if not player_stats:
        print(f"No match data found for {player_name} on HLTV")
        return
    
    stats_rows = []
    
    for stat in player_stats:
        # Map to our schema
        row = {
            "player_id": player_id,
            "game_id": f"hltv_{stat.get('match_id', 'unknown')}",  # Use HLTV match ID
            "date": stat.get('date') or datetime.now(timezone.utc).isoformat(),
            "points": stat.get('kills', 0),  # Kills -> points
            "rebounds": stat.get('deaths', 0),  # Deaths -> rebounds
            "assists": stat.get('assists', 0),
            "minutes_played": 0,  # Not available from HLTV
            "opponent": stat.get('opponent', 'Unknown'),
            "home": False  # Unknown from HLTV
        }
        
        stats_rows.append(row)
    
    if stats_rows:
        print(f"Upserting {len(stats_rows)} stats records from HLTV...")
        try:
            supabase.table("player_game_stats").upsert(stats_rows).execute()
            print(f"Successfully stored {len(stats_rows)} matches from HLTV.")
        except Exception as e:
            print(f"Error upserting: {e}")
    else:
        print("No stats extracted from HLTV.")

def fetch_all_esports_players():
    """
    Fetch match history for all Esports players in our database.
    """
    print("Fetching HLTV data for all Esports players...")
    
    # Get all Esports players
    players = (
        supabase.table("players")
        .select("id, name, team, sport, external_id")
        .in_("sport", ["CS2", "Valorant"])
        .execute()
        .data
    )
    
    print(f"Found {len(players)} Esports players")
    
    for player in players:
        player_id = player["id"]
        player_name = player["name"]
        team_name = player.get("team")
        
        # Only fetch for CS2/Valorant (HLTV primarily covers CS)
        if player.get("sport") in ["CS2", "Valorant"]:
            fetch_player_match_history(player_id, player_name, team_name, limit=5)
            time.sleep(2)  # Rate limit between players

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--player_id", help="Supabase Player ID")
    parser.add_argument("--player_name", help="Player Name")
    parser.add_argument("--team_name", help="Team Name (optional)")
    parser.add_argument("--all", action="store_true", help="Fetch for all Esports players")
    
    args = parser.parse_args()
    
    if args.all:
        fetch_all_esports_players()
    elif args.player_id and args.player_name:
        # Resolve player from DB
        player = supabase.table("players").select("*").eq("id", args.player_id).single().execute().data
        if player:
            fetch_player_match_history(
                args.player_id,
                args.player_name,
                args.team_name or player.get("team"),
                limit=10
            )
    else:
        print("Usage: --player_id and --player_name, or --all")

