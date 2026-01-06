"""
NBA Stats API integration
Using the public NBA Stats API (stats.nba.com)
"""
import requests
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta


class NBAStatsAPI:
    """Client for NBA Stats API"""
    
    BASE_URL = "https://stats.nba.com/stats"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nba.com/",
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
    
    def get_players(self, season: str = None, team_id: int = None) -> List[Dict]:
        """
        Get all players or players for a specific team.
        
        Args:
            season: Season year (e.g., "2023-24")
            team_id: Optional team ID to filter
        
        Returns:
            List of player dictionaries
        """
        if not season:
            # Default to current season
            current_year = datetime.now().year
            if datetime.now().month >= 10:  # NBA season starts in October
                season = f"{current_year}-{str(current_year + 1)[-2:]}"
            else:
                season = f"{current_year - 1}-{str(current_year)[-2:]}"
        
        endpoint = "commonallplayers"
        params = {
            "LeagueID": "00",
            "Season": season,
            "IsOnlyCurrentSeason": "1"
        }
        
        try:
            response = self.session.get(f"{self.BASE_URL}/{endpoint}", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            players = []
            if "resultSets" in data and len(data["resultSets"]) > 0:
                headers = data["resultSets"][0]["headers"]
                rows = data["resultSets"][0]["rowSet"]
                
                for row in rows:
                    player = dict(zip(headers, row))
                    # Use DISPLAY_FIRST_LAST if available, otherwise try to parse DISPLAY_LAST_COMMA_FIRST
                    name = player.get("DISPLAY_FIRST_LAST", "")
                    if not name and player.get("DISPLAY_LAST_COMMA_FIRST"):
                        # Convert "Last, First" to "First Last"
                        parts = player.get("DISPLAY_LAST_COMMA_FIRST", "").split(", ")
                        if len(parts) == 2:
                            name = f"{parts[1]} {parts[0]}"
                    players.append({
                        "external_id": str(player.get("PERSON_ID", "")),
                        "name": name.strip(),
                        "position": player.get("POSITION", ""),
                        "team": player.get("TEAM_ABBREVIATION", ""),
                        "jersey_number": player.get("JERSEY", None),
                        "raw_data": player
                    })
            
            # Filter by team if specified
            if team_id:
                # Note: team_id filtering would need team mapping
                pass
            
            return players
        
        except Exception as e:
            print(f"Error fetching players: {e}")
            return []
    
    def get_player_game_log(self, player_id: str, season: str = None) -> List[Dict]:
        """
        Get game log for a specific player.
        
        Args:
            player_id: NBA player ID
            season: Season year (e.g., "2023-24")
        
        Returns:
            List of game stat dictionaries
        """
        if not season:
            current_year = datetime.now().year
            if datetime.now().month >= 10:
                season = f"{current_year}-{str(current_year + 1)[-2:]}"
            else:
                season = f"{current_year - 1}-{str(current_year)[-2:]}"
        
        endpoint = "playergamelog"
        params = {
            "PlayerID": player_id,
            "Season": season,
            "SeasonType": "Regular Season"
        }
        
        try:
            response = self.session.get(f"{self.BASE_URL}/{endpoint}", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            games = []
            if "resultSets" in data and len(data["resultSets"]) > 0:
                headers = data["resultSets"][0]["headers"]
                rows = data["resultSets"][0]["rowSet"]
                
                for row in rows:
                    game = dict(zip(headers, row))
                    
                    # Parse game date
                    game_date_str = game.get("GAME_DATE", "")
                    try:
                        game_date = datetime.strptime(game_date_str, "%b %d, %Y").date()
                    except:
                        game_date = None
                    
                    # Determine if home game
                    matchup = game.get("MATCHUP", "")
                    is_home = "@" not in matchup
                    opponent = matchup.replace("@ ", "").replace("vs. ", "").split()[0] if matchup else ""
                    
                    games.append({
                        "date": game_date.isoformat() if game_date else None,
                        "opponent": opponent,
                        "home": is_home,
                        "minutes_played": game.get("MIN", 0),
                        "points": game.get("PTS", 0),
                        "rebounds": game.get("REB", 0),
                        "assists": game.get("AST", 0),
                        "steals": game.get("STL", 0),
                        "blocks": game.get("BLK", 0),
                        "turnovers": game.get("TOV", 0),
                        "field_goals_made": game.get("FGM", 0),
                        "field_goals_attempted": game.get("FGA", 0),
                        "three_pointers_made": game.get("FG3M", 0),
                        "three_pointers_attempted": game.get("FG3A", 0),
                        "free_throws_made": game.get("FTM", 0),
                        "free_throws_attempted": game.get("FTA", 0),
                        "raw_data": game
                    })
            
            return games
        
        except Exception as e:
            print(f"Error fetching player game log: {e}")
            return []
    
    def search_players(self, query: str, season: str = None) -> List[Dict]:
        """
        Search for players by name.
        
        Args:
            query: Search query (player name)
            season: Season year
        
        Returns:
            List of matching players
        """
        all_players = self.get_players(season)
        query_lower = query.lower()
        
        matches = []
        for player in all_players:
            if query_lower in player["name"].lower():
                matches.append(player)
        
        return matches


# Alternative: ESPN API (simpler but may have rate limits)
class ESPNBAStats:
    """ESPN NBA Stats - Alternative source"""
    
    BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
    
    def get_players_by_team(self, team_abbrev: str) -> List[Dict]:
        """
        Get players for a specific team from ESPN.
        
        Args:
            team_abbrev: Team abbreviation (e.g., "NY", "LAL")
        
        Returns:
            List of player dictionaries
        """
        # ESPN team ID mapping would be needed
        # This is a placeholder structure
        return []

