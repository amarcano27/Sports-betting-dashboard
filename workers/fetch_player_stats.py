"""
Worker to fetch and store player statistics
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from services.nba_stats_api import NBAStatsAPI
from services.odds_api import get_odds_for_sport


def sync_players(season: str = None):
    """
    Sync all NBA players to database.
    
    Args:
        season: Season year (e.g., "2023-24")
    """
    print("Fetching NBA players...")
    api = NBAStatsAPI()
    players = api.get_players(season)
    
    print(f"Found {len(players)} players")
    
    for player in players:
        # Check if player exists
        existing = supabase.table("players").select("id").eq("external_id", player["external_id"]).execute()
        
        if existing.data:
            # Update existing player
            player_id = existing.data[0]["id"]
            supabase.table("players").update({
                "name": player["name"],
                "position": player.get("position"),
                "team": player.get("team"),
                "jersey_number": player.get("jersey_number"),
                "raw_data": player.get("raw_data"),
                "updated_at": datetime.now().isoformat()
            }).eq("id", player_id).execute()
        else:
            # Insert new player
            supabase.table("players").insert({
                "external_id": player["external_id"],
                "name": player["name"],
                "position": player.get("position"),
                "team": player.get("team"),
                "sport": "NBA",
                "jersey_number": player.get("jersey_number"),
                "raw_data": player.get("raw_data")
            }).execute()
    
    print(f"Synced {len(players)} players to database")


def fetch_player_game_log(player_id: str, season: str = None):
    """
    Fetch and store game log for a specific player.
    
    Args:
        player_id: Player UUID from database
        season: Season year
    """
    # Get player external ID
    player = supabase.table("players").select("external_id").eq("id", player_id).execute()
    if not player.data:
        print(f"Player {player_id} not found")
        return
    
    external_id = player.data[0]["external_id"]
    
    print(f"Fetching game log for player {external_id}...")
    api = NBAStatsAPI()
    games = api.get_player_game_log(external_id, season)
    
    print(f"Found {len(games)} games")
    
    # Get all games from our database to match
    db_games = supabase.table("games").select("id, external_id, home_team, away_team, start_time").eq("sport", "NBA").execute().data
    
    # Create lookup by date
    game_lookup = {}
    for game in db_games:
        game_date = datetime.fromisoformat(game["start_time"].replace("Z", "+00:00")).date()
        game_lookup[game_date] = game
    
    stored_count = 0
    for game_stat in games:
        if not game_stat.get("date"):
            continue
        
        game_date = datetime.fromisoformat(game_stat["date"]).date()
        
        # Try to find matching game
        matching_game = game_lookup.get(game_date)
        if not matching_game:
            # Try to match by opponent
            for game in db_games:
                game_db_date = datetime.fromisoformat(game["start_time"].replace("Z", "+00:00")).date()
                if abs((game_db_date - game_date).days) <= 1:  # Within 1 day
                    # Check opponent
                    opponent = game_stat.get("opponent", "")
                    if opponent and (opponent in game["home_team"] or opponent in game["away_team"]):
                        matching_game = game
                        break
        
        if matching_game:
            # Check if stats already exist
            existing = supabase.table("player_game_stats").select("id").eq(
                "player_id", player_id
            ).eq("game_id", matching_game["id"]).execute()
            
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
                    "player_id": player_id,
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
                stored_count += 1
    
    print(f"Stored {stored_count} new game stats")


def fetch_all_active_players_stats():
    """Fetch stats for all active NBA players"""
    # Get all active players
    players = supabase.table("players").select("id, name").eq("sport", "NBA").execute().data
    
    print(f"Fetching stats for {len(players)} players...")
    
    for i, player in enumerate(players, 1):
        print(f"[{i}/{len(players)}] Fetching stats for {player['name']}...")
        try:
            fetch_player_game_log(player["id"])
            # Rate limiting
            import time
            time.sleep(1)  # 1 second between requests
        except Exception as e:
            print(f"Error fetching stats for {player['name']}: {e}")
    
    print("Done fetching player stats")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch NBA player statistics")
    parser.add_argument("--sync-players", action="store_true", help="Sync all players")
    parser.add_argument("--player-id", type=str, help="Fetch stats for specific player ID")
    parser.add_argument("--all", action="store_true", help="Fetch stats for all players")
    
    args = parser.parse_args()
    
    if args.sync_players:
        sync_players()
    elif args.player_id:
        fetch_player_game_log(args.player_id)
    elif args.all:
        fetch_all_active_players_stats()
    else:
        print("Use --sync-players to sync players, --player-id <id> for specific player, or --all for all players")

