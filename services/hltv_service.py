"""
Enhanced HLTV Data Service
Fetches real match data from HLTV.org using multiple methods
"""
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
from typing import Dict, List, Optional
import re
import json

class HLTVService:
    def __init__(self):
        self.base_url = "https://www.hltv.org"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def search_player(self, player_name: str) -> Optional[str]:
        """
        Search for a player and return their HLTV profile URL.
        """
        try:
            search_url = f"{self.base_url}/search?query={player_name.replace(' ', '+')}"
            response = self.session.get(search_url, timeout=10)
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find player link - HLTV search results structure
            player_link = soup.find('a', href=re.compile(r'/player/\d+/[^/]+'))
            if player_link:
                return player_link['href']
            
            return None
            
        except Exception as e:
            print(f"Error searching player: {e}")
            return None
    
    def get_player_stats(self, player_url: str) -> Optional[Dict]:
        """
        Get player statistics from their HLTV profile.
        """
        try:
            full_url = f"{self.base_url}{player_url}/stats"
            response = self.session.get(full_url, timeout=10)
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            stats = {
                'source': 'HLTV',
                'url': full_url
            }
            
            # Extract player name
            name_elem = soup.find('h1', class_='playerNickname')
            if name_elem:
                stats['player_name'] = name_elem.get_text(strip=True)
            
            # Extract overall stats
            stats_table = soup.find('div', class_='stats-row')
            if stats_table:
                # Parse key metrics
                stat_items = stats_table.find_all('div', class_='stat')
                for item in stat_items:
                    label = item.find('span', class_='stat-label')
                    value = item.find('span', class_='stat-value')
                    if label and value:
                        key = label.get_text(strip=True).lower().replace(' ', '_')
                        stats[key] = value.get_text(strip=True)
            
            return stats
            
        except Exception as e:
            print(f"Error fetching player stats: {e}")
            return None
    
    def get_player_matches(self, player_url: str, limit: int = 10) -> List[Dict]:
        """
        Get recent matches for a player.
        """
        try:
            matches_url = f"{self.base_url}{player_url}/matches"
            response = self.session.get(matches_url, timeout=10)
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            matches = []
            
            # Find match rows - HLTV structure
            match_rows = soup.find_all('tr', class_='match-row')[:limit]
            
            for row in match_rows:
                match_link = row.find('a', href=re.compile(r'/matches/\d+'))
                if match_link:
                    match_href = match_link['href']
                    match_id = re.search(r'/matches/(\d+)', match_href).group(1)
                    
                    # Extract date
                    date_cell = row.find('td', class_='date-cell')
                    date_str = date_cell.get_text(strip=True) if date_cell else None
                    
                    # Extract opponent
                    opponent_cell = row.find('td', class_='opponent-cell')
                    opponent = opponent_cell.get_text(strip=True) if opponent_cell else "Unknown"
                    
                    # Extract result (win/loss)
                    result_cell = row.find('td', class_='result-cell')
                    result = result_cell.get_text(strip=True) if result_cell else None
                    
                    matches.append({
                        'match_id': match_id,
                        'match_url': match_href,
                        'date': date_str,
                        'opponent': opponent,
                        'result': result
                    })
            
            return matches
            
        except Exception as e:
            print(f"Error fetching player matches: {e}")
            return []
    
    def get_match_details(self, match_id: str) -> Optional[Dict]:
        """
        Get detailed match statistics including player performance.
        """
        try:
            match_url = f"{self.base_url}/matches/{match_id}"
            response = self.session.get(match_url, timeout=10)
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            match_data = {
                'match_id': match_id,
                'source': 'HLTV'
            }
            
            # Extract team names
            team_elems = soup.find_all('div', class_='team')
            teams = []
            for team_elem in team_elems:
                team_name = team_elem.find('div', class_='teamName')
                if team_name:
                    teams.append(team_name.get_text(strip=True))
            
            match_data['teams'] = teams
            
            # Extract player stats from stats table
            stats_section = soup.find('div', class_='stats-section')
            if stats_section:
                players_stats = []
                
                # Find all player stat rows
                stat_rows = stats_section.find_all('tr')[1:]  # Skip header
                
                for row in stat_rows:
                    cells = row.find_all('td')
                    if len(cells) >= 6:
                        player_name = cells[0].get_text(strip=True)
                        
                        # Parse stats (structure may vary)
                        kills = self._parse_int(cells[1].get_text(strip=True))
                        deaths = self._parse_int(cells[2].get_text(strip=True))
                        assists = self._parse_int(cells[3].get_text(strip=True))
                        
                        # Try to get headshots if available
                        headshots = 0
                        if len(cells) > 6:
                            headshots = self._parse_int(cells[6].get_text(strip=True))
                        
                        players_stats.append({
                            'name': player_name,
                            'kills': kills,
                            'deaths': deaths,
                            'assists': assists,
                            'headshots': headshots
                        })
                
                match_data['players'] = players_stats
            
            return match_data
            
        except Exception as e:
            print(f"Error fetching match details: {e}")
            return None
    
    def get_player_match_history(self, player_name: str, team_name: str = None, limit: int = 10) -> List[Dict]:
        """
        Complete workflow: Search player, get matches, get details.
        Returns list of match stats for the player.
        """
        try:
            # Step 1: Search for player
            player_url = self.search_player(player_name)
            if not player_url:
                print(f"Player {player_name} not found on HLTV")
                return []
            
            time.sleep(1)  # Rate limit
            
            # Step 2: Get recent matches
            matches = self.get_player_matches(player_url, limit=limit)
            if not matches:
                return []
            
            time.sleep(1)  # Rate limit
            
            # Step 3: Get match details and extract player stats
            player_stats = []
            
            for match_info in matches:
                match_id = match_info['match_id']
                match_details = self.get_match_details(match_id)
                
                if match_details:
                    # Find this player in the match
                    players = match_details.get('players', [])
                    for p in players:
                        if p['name'].lower() == player_name.lower():
                            # Add match context
                            p['match_id'] = match_id
                            p['date'] = match_info.get('date')
                            p['opponent'] = match_info.get('opponent')
                            p['result'] = match_info.get('result')
                            player_stats.append(p)
                            break
                
                time.sleep(1)  # Rate limit between matches
            
            return player_stats
            
        except Exception as e:
            print(f"Error in get_player_match_history: {e}")
            return []
    
    def _parse_int(self, text: str) -> int:
        """Parse integer from text."""
        try:
            # Remove all non-numeric except minus
            cleaned = re.sub(r'[^\d-]', '', text)
            return int(cleaned) if cleaned else 0
        except:
            return 0
    
    def _parse_float(self, text: str) -> float:
        """Parse float from text."""
        try:
            cleaned = re.sub(r'[^\d.]', '', text)
            return float(cleaned) if cleaned else 0.0
        except:
            return 0.0

# Global instance
hltv = HLTVService()
