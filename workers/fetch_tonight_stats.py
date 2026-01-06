"""
Fetch player stats for players in tonight's games
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from services.nba_stats_api import NBAStatsAPI
from utils.team_mapping import get_team_abbrev, normalize_team_name
import time

def get_players_in_games(games):
    """Get all players from teams playing in these games"""
    teams = set()
    team_abbrevs = set()
    
    for game in games:
        home_team = game.get("home_team", "")
        away_team = game.get("away_team", "")
        teams.add(home_team)
        teams.add(away_team)
        
        # Try to get abbreviations
        home_abbrev = get_team_abbrev(home_team)
        away_abbrev = get_team_abbrev(away_team)
        team_abbrevs.add(home_abbrev)
        team_abbrevs.add(away_abbrev)
    
    print(f"Looking for players from teams: {teams}")
    print(f"Team abbreviations: {team_abbrevs}")
    
    # Get players from these teams (try both full name and abbreviation)
    players = []
    all_players = (
        supabase.table("players")
        .select("*")
        .eq("sport", "NBA")
        .execute()
        .data
    )
    
    for player in all_players:
        player_team = player.get("team", "")
        # Match by abbreviation or full name
        if player_team in team_abbrevs or player_team in teams:
            players.append(player)
        # Also try normalized matching
        elif normalize_team_name(player_team) in team_abbrevs:
            players.append(player)
    
    return players

def fetch_stats_for_tonight():
    """Fetch stats for players in tonight's games"""
    print("Fetching tonight's games...")
    
    # Get games in next 24 hours
    cutoff = (datetime.now() + timedelta(hours=24)).isoformat()
    games = (
        supabase.table("games")
        .select("*")
        .eq("sport", "NBA")
        .gte("start_time", datetime.now().isoformat())
        .lte("start_time", cutoff)
        .order("start_time")
        .execute()
        .data
    )
    
    if not games:
        print("No games found. Fetch odds data first.")
        return
    
    print(f"Found {len(games)} games tonight")
    for game in games:
        print(f"  - {game['away_team']} @ {game['home_team']}")
    
    # Get players from these teams
    players = get_players_in_games(games)
    print(f"\nFound {len(players)} players in tonight's games")
    
    if not players:
        print("No players found for these teams. Sync players first.")
        return
    
    # Fetch stats for each player
    api = NBAStatsAPI()
    success_count = 0
    
    for i, player in enumerate(players, 1):
        player_name = player.get('name', 'Unknown')
        player_team = player.get('team', 'N/A')
        print(f"\n[{i}/{len(players)}] Fetching stats for {player_name} ({player_team})...")
        
        try:
            external_id = player.get("external_id")
            if not external_id:
                print(f"  No external_id for {player_name}, skipping")
                continue
            
            # Get game log
            game_log = api.get_player_game_log(external_id)
            
            if not game_log:
                print(f"  No game log found")
                continue
            
            print(f"  Found {len(game_log)} games in log")
            
            # Match games and store stats
            stored = 0
            for game_stat in game_log:
                if not game_stat.get("date"):
                    continue
                
                game_date = datetime.fromisoformat(game_stat["date"]).date()
                
                # Find matching game in our database
                matching_game = None
                for game in games:
                    game_db_date = datetime.fromisoformat(game["start_time"].replace("Z", "+00:00")).date()
                    if abs((game_db_date - game_date).days) <= 1:
                        # Check if opponent matches
                        opponent = game_stat.get("opponent", "")
                        if opponent and (opponent in game["home_team"] or opponent in game["away_team"]):
                            matching_game = game
                            break
                
                if matching_game:
                    # Check if stats already exist
                    existing = (
                        supabase.table("player_game_stats")
                        .select("id")
                        .eq("player_id", player["id"])
                        .eq("game_id", matching_game["id"])
                        .execute()
                        .data
                    )
                    
                    if existing.data:
                        # Update
                        supabase.table("player_game_stats").update({
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
                        }).eq("id", existing.data[0]["id"]).execute()
                    else:
                        # Insert
                        supabase.table("player_game_stats").insert({
                            "player_id": player["id"],
                            "game_id": matching_game["id"],
                            "date": game_stat["date"],
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
                print(f"  [OK] Stored {stored} new game stats")
                success_count += 1
            else:
                print(f"  [!] No matching games found")
            
            # Rate limiting
            time.sleep(1)
            
        except Exception as e:
            print(f"  [ERROR] Error: {e}")
            continue
    
    print(f"\n[OK] Completed! Successfully fetched stats for {success_count}/{len(players)} players")

if __name__ == "__main__":
    fetch_stats_for_tonight()

