import sys
import os
from pathlib import Path
import argparse
from datetime import datetime, timezone

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from services.pandascore_api import pandascore

def fetch_history(player_id, limit=10):
    print(f"Fetching history for player {player_id}...")
    
    # Resolve UUID from DB
    try:
        # external_id is stored as string
        db_player = supabase.table("players").select("id").eq("external_id", str(player_id)).single().execute().data
        if not db_player:
            print(f"Player {player_id} not found in DB.")
            return
        db_player_uuid = db_player["id"]
    except Exception as e:
        print(f"Error resolving player UUID: {e}")
        return

    # 1. Fetch Match List
    matches = pandascore.get_player_stats(player_id, limit=limit)
    if not matches:
        print("No matches found.")
        return

    stats_rows = []
    
    for m in matches:
        match_id = m.get("id")
        begin_at = m.get("begin_at")
        if not begin_at: continue
        
        # 2. Fetch Match Detail for Stats
        detailed_match = pandascore.get_match_details(match_id)
        if not detailed_match:
            continue
            
        games = detailed_match.get("games", [])
        for g in games:
            if not g.get("finished"): continue
            
            # Find player in players list
            players_stats = g.get("players", [])
            if not players_stats:
                continue
                
            # Find our player
            p_stat = next((p for p in players_stats if str(p.get("player_id")) == str(player_id) or str(p.get("id")) == str(player_id)), None)
            
            if p_stat:
                # Found stats!
                kills = p_stat.get("kills", 0)
                deaths = p_stat.get("deaths", 0)
                assists = p_stat.get("assists", 0)
                
                row = {
                    "player_id": db_player_uuid, # Use UUID
                    "game_id": str(g.get("id")), # Use Game ID (sub-match) as string
                    "date": begin_at,
                    "points": kills,
                    "rebounds": deaths,
                    "assists": assists,
                    "minutes_played": 0,
                    "opponent": "Unknown" 
                }
                
                # Derive opponent if possible
                opponents = detailed_match.get("opponents", [])
                if len(opponents) == 2:
                    # Assume player is on one team, opponent is the other
                    # But we don't know which team the player is on from just ID here easily without roster check
                    # p_stat might have team_id?
                    # Often players list has team info?
                    # Let's check if p_stat has opponent info? Unlikely.
                    # Just leave Unknown for now.
                    pass
                
                stats_rows.append(row)

    if stats_rows:
        print(f"Upserting {len(stats_rows)} stats records...")
        try:
            # Upsert to player_game_stats
            data = supabase.table("player_game_stats").upsert(stats_rows).execute()
            print("Success.")
        except Exception as e:
            print(f"Error upserting: {e}")
    else:
        print("No stats extracted.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--player_id", required=True, help="PandaScore Player ID")
    args = parser.parse_args()
    
    fetch_history(args.player_id)
