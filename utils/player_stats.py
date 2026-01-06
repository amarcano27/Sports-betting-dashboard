"""
Player statistics utilities (structure for future expansion)
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class PlayerStats:
    """
    Structure for player statistics.
    This is a placeholder for future expansion when player data is available.
    """
    
    def __init__(self, player_name: str, team: str, position: str = None):
        self.player_name = player_name
        self.team = team
        self.position = position
        self.stats = {}
        self.recent_games = []
        self.opponent_history = {}
    
    def add_game_stats(self, game_date: datetime, opponent: str, stats: Dict):
        """Add stats from a single game"""
        self.recent_games.append({
            "date": game_date,
            "opponent": opponent,
            "stats": stats
        })
        
        # Keep only last 10 games
        self.recent_games.sort(key=lambda x: x["date"], reverse=True)
        if len(self.recent_games) > 10:
            self.recent_games = self.recent_games[:10]
    
    def get_recent_average(self, stat_name: str, games: int = 5) -> Optional[float]:
        """Get average of a stat over recent games"""
        if not self.recent_games:
            return None
        
        recent = self.recent_games[:games]
        values = [g["stats"].get(stat_name) for g in recent if stat_name in g["stats"]]
        
        if not values:
            return None
        
        return sum(values) / len(values)
    
    def get_opponent_average(self, opponent: str, stat_name: str) -> Optional[float]:
        """Get average stat against a specific opponent"""
        if opponent not in self.opponent_history:
            return None
        
        games = self.opponent_history[opponent]
        values = [g["stats"].get(stat_name) for g in games if stat_name in g["stats"]]
        
        if not values:
            return None
        
        return sum(values) / len(values)


def get_player_performance_vs_team(player_name: str, team: str, stats: List[PlayerStats]) -> Optional[Dict]:
    """
    Get a player's historical performance against a specific team.
    
    Args:
        player_name: Name of the player
        team: Opponent team name
        stats: List of PlayerStats objects
    
    Returns:
        Dictionary with performance metrics or None
    """
    player = next((p for p in stats if p.player_name == player_name), None)
    
    if not player:
        return None
    
    opponent_games = player.opponent_history.get(team, [])
    
    if not opponent_games:
        return None
    
    # Calculate averages
    all_stats = {}
    for game in opponent_games:
        for stat_name, value in game["stats"].items():
            if stat_name not in all_stats:
                all_stats[stat_name] = []
            all_stats[stat_name].append(value)
    
    averages = {stat: sum(values) / len(values) for stat, values in all_stats.items()}
    
    return {
        "player": player_name,
        "opponent": team,
        "games_played": len(opponent_games),
        "averages": averages,
        "recent_trend": "improving" if len(opponent_games) >= 3 else "insufficient_data"
    }


# Placeholder function for when player data API is integrated
def fetch_player_stats(player_name: str, team: str, sport: str) -> Optional[PlayerStats]:
    """
    Fetch player statistics from external API.
    This is a placeholder for future integration.
    
    Args:
        player_name: Name of the player
        team: Team name
        sport: Sport (NBA, NFL, etc.)
    
    Returns:
        PlayerStats object or None
    """
    # TODO: Integrate with player stats API (e.g., ESPN, NBA Stats API, etc.)
    return None

