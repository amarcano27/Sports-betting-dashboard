"""
CS2 Data Service - Using BO3.gg API (more reliable than scraping)
"""
import requests
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

class CS2DataService:
    def __init__(self):
        self.base_url = "https://api.bo3.gg/api/v1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }
    
    def get_player_stats(self, player_name: str, team_name: str = None) -> List[Dict]:
        """
        Get player match history from BO3.gg API.
        Returns list of match stats.
        """
        try:
            print(f"    Searching BO3.gg for {player_name}...")
            
            # Search for player
            search_url = f"{self.base_url}/players/search"
            params = {"q": player_name}
            response = requests.get(search_url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"    BO3.gg search failed: {response.status_code}")
                return []
            
            data = response.json()
            players = data.get('data', []) if isinstance(data, dict) else data
            
            if not players:
                print(f"    Player {player_name} not found on BO3.gg")
                return []
            
            # Get first match (or filter by team if provided)
            player_id = None
            for p in players:
                if team_name and team_name.lower() in p.get('team', {}).get('name', '').lower():
                    player_id = p.get('id')
                    break
                elif not player_id:
                    player_id = p.get('id')
            
            if not player_id:
                return []
            
            print(f"    Found player ID: {player_id}")
            time.sleep(1)
            
            # Get player matches
            matches_url = f"{self.base_url}/players/{player_id}/matches"
            matches_response = requests.get(matches_url, headers=self.headers, timeout=10)
            
            if matches_response.status_code != 200:
                print(f"    Failed to get matches: {matches_response.status_code}")
                return []
            
            matches_data = matches_response.json()
            matches = matches_data.get('data', []) if isinstance(matches_data, dict) else matches_data
            
            if not matches:
                return []
            
            print(f"    Found {len(matches)} matches")
            
            # Get detailed stats for each match
            player_stats = []
            for match in matches[:5]:  # Limit to 5
                match_id = match.get('id')
                if not match_id:
                    continue
                
                # Get match details
                match_url = f"{self.base_url}/matches/{match_id}"
                match_response = requests.get(match_url, headers=self.headers, timeout=10)
                
                if match_response.status_code != 200:
                    continue
                
                match_data = match_response.json()
                match_details = match_data.get('data', match_data)
                
                # Find player in match stats
                players_stats = match_details.get('players', [])
                for p_stat in players_stats:
                    if p_stat.get('player', {}).get('id') == player_id:
                        stats = p_stat.get('stats', {})
                        player_stats.append({
                            'name': player_name,
                            'kills': stats.get('kills', 0),
                            'deaths': stats.get('deaths', 0),
                            'assists': stats.get('assists', 0),
                            'match_id': str(match_id),
                            'date': match.get('date') or datetime.now(timezone.utc).isoformat()
                        })
                        break
                
                time.sleep(1)  # Rate limit
            
            print(f"    Extracted {len(player_stats)} match stats")
            return player_stats
            
        except Exception as e:
            print(f"    Error fetching BO3.gg data: {e}")
            import traceback
            traceback.print_exc()
            return []

# Generate realistic simulated stats based on prop lines
def generate_simulated_stats(player_id, player_name, sport, limit=15, base_line=None):
    """
    Generate realistic simulated match stats.
    If base_line is provided, stats will center around it for consistency.
    Otherwise uses sport-specific defaults.
    """
    import random
    from datetime import datetime, timedelta, timezone
    
    # Use provided line or sport default
    if base_line is None:
        if sport == "CS2":
            base_kills = 13.5
        elif sport == "Valorant":
            base_kills = 14.5
        elif sport == "LoL":
            base_kills = 3.5
        elif sport == "Dota2":
            base_kills = 6.5
        else:
            base_kills = 10.0
    else:
        base_kills = float(base_line)
    
    stats = []
    
    # Seed random for consistency per player
    random.seed(hash(f"{player_id}_{player_name}") % 10000)
    
    for i in range(limit):
        # Generate kills around the line with realistic variance
        # Use normal distribution centered on base_line
        kills = max(0, round(base_kills + random.gauss(0, 2.5)))
        
        # Deaths typically 60-80% of kills for good players
        death_ratio = random.uniform(0.6, 0.85)
        deaths = max(0, round(kills * death_ratio + random.gauss(0, 1.5)))
        
        # Assists typically 30-50% of kills
        assist_ratio = random.uniform(0.3, 0.5)
        assists = max(0, round(kills * assist_ratio + random.gauss(0, 1.5)))
        
        # Date: spread matches over last 30-45 days
        days_ago = i * 2.5 + random.uniform(0, 2)
        date = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
        
        stats.append({
            "player_id": player_id,
            "game_id": f"sim_{player_id}_{i}",
            "date": date,
            "points": kills,
            "rebounds": deaths,
            "assists": assists,
            "minutes_played": 0,
            "opponent": "Unknown",
            "home": False
        })
    
    return stats

# Global instance
cs2_data = CS2DataService()

