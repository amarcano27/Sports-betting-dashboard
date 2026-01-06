"""
Fetch stats for key players (star players and players in upcoming games)
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from services.nba_stats_api import NBAStatsAPI
from utils.team_mapping import get_team_abbrev
import time

# Key players to prioritize (star players)
KEY_PLAYERS = [
    "LeBron James", "Stephen Curry", "Kevin Durant", "Luka Doncic",
    "Jayson Tatum", "Giannis Antetokounmpo", "Joel Embiid", "Nikola Jokic",
    "Devin Booker", "Damian Lillard", "Anthony Edwards", "Shai Gilgeous-Alexander",
    "Jayson Tatum", "Jaylen Brown", "Kawhi Leonard", "Paul George",
    "James Harden", "Russell Westbrook", "Kyle Kuzma", "Josh Hart"
]

def fetch_key_players_stats():
    """Fetch stats for key/star players"""
    print("Fetching stats for key players...")
    
    # Get key players from database
    all_players = supabase.table("players").select("*").eq("sport", "NBA").execute().data
    
    key_players = []
    for player in all_players:
        if player.get("name") in KEY_PLAYERS:
            key_players.append(player)
    
    print(f"Found {len(key_players)} key players")
    
    # Also get players from upcoming games
    cutoff = (datetime.now() + timedelta(hours=48)).isoformat()
    games = (
        supabase.table("games")
        .select("*")
        .eq("sport", "NBA")
        .gte("start_time", datetime.now().isoformat())
        .lte("start_time", cutoff)
        .execute()
        .data
    )
    
    if games:
        teams = set()
        for game in games:
            teams.add(get_team_abbrev(game.get("home_team", "")))
            teams.add(get_team_abbrev(game.get("away_team", "")))
        
        # Get players from these teams
        for player in all_players:
            if player.get("team") in teams and player not in key_players:
                key_players.append(player)
    
    print(f"Total players to fetch: {len(key_players)}")
    
    api = NBAStatsAPI()
    success_count = 0
    total_stats = 0
    
    for i, player in enumerate(key_players, 1):
        player_name = player.get('name', 'Unknown')
        player_team = player.get('team', 'N/A')
        print(f"\n[{i}/{len(key_players)}] {player_name} ({player_team})...", end=" ")
        
        try:
            external_id = player.get("external_id")
            if not external_id:
                print("No external_id")
                continue
            
            game_log = api.get_player_game_log(external_id)
            
            if not game_log:
                print("No games")
                continue
            
            print(f"{len(game_log)} games", end=" ")
            
            stored = 0
            for game_stat in game_log[:30]:
                if not game_stat.get("date"):
                    continue
                
                game_date = game_stat.get("date")
                
                existing = (
                    supabase.table("player_game_stats")
                    .select("id")
                    .eq("player_id", player["id"])
                    .eq("date", game_date)
                    .execute()
                    .data
                )
                
                if existing:
                    # Update existing
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
                    # Insert new
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
                total_stats += stored
            else:
                print("- Up to date")
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"ERROR: {e}")
            continue
    
    print(f"\n[OK] Completed!")
    print(f"  - Processed: {success_count}/{len(key_players)} players")
    print(f"  - Total stats: {total_stats}")

if __name__ == "__main__":
    fetch_key_players_stats()

