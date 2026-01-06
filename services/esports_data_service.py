"""
Improved HLTV Data Service - Simpler, more reliable approach
"""
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import re
import json

class EsportsDataService:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.hltv.org/"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def get_player_stats_from_hltv(self, player_name: str, team_name: str = None) -> List[Dict]:
        """
        Simplified HLTV scraper - tries multiple approaches.
        """
        try:
            print(f"    [HLTV] Searching for {player_name}...")
            
            # Approach 1: Direct player URL search (if we know the format)
            # HLTV URLs are like: /player/1234/playername
            # We'll search and try to find the player ID
            
            search_url = f"https://www.hltv.org/search?query={player_name.replace(' ', '%20')}"
            response = self.session.get(search_url, timeout=15, allow_redirects=True)
            
            if response.status_code != 200:
                print(f"    [HLTV] Search failed: HTTP {response.status_code}")
                return []
            
            # Check if we got redirected to a player page
            if '/player/' in response.url:
                player_url = response.url
                print(f"    [HLTV] Found direct player page: {player_url}")
                return self._get_matches_from_player_page(player_url, player_name)
            
            # Parse search results
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for player links in search results
            player_links = soup.find_all('a', href=re.compile(r'/player/\d+/'))
            
            if not player_links:
                # Try alternative search result structure
                player_links = soup.find_all('a', href=True)
                player_links = [l for l in player_links if '/player/' in l.get('href', '')]
            
            if not player_links:
                print(f"    [HLTV] Player {player_name} not found in search results")
                return []
            
            # Use first match (or filter by team if provided)
            player_link = player_links[0].get('href')
            if not player_link.startswith('http'):
                player_link = f"https://www.hltv.org{player_link}"
            
            print(f"    [HLTV] Found player: {player_link}")
            time.sleep(1)
            
            return self._get_matches_from_player_page(player_link, player_name)
            
        except Exception as e:
            print(f"    [HLTV] Error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _get_matches_from_player_page(self, player_url: str, player_name: str) -> List[Dict]:
        """Get matches from player's HLTV profile page."""
        try:
            # Get matches page
            matches_url = f"{player_url}/matches" if not player_url.endswith('/matches') else player_url
            if not matches_url.endswith('/matches'):
                matches_url = f"{player_url.rstrip('/')}/matches"
            
            print(f"    [HLTV] Fetching matches from: {matches_url}")
            response = self.session.get(matches_url, timeout=15)
            
            if response.status_code != 200:
                print(f"    [HLTV] Failed to load matches page: HTTP {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find match links - HLTV uses various structures
            match_links = soup.find_all('a', href=re.compile(r'/matches/\d+'))
            
            if not match_links:
                print(f"    [HLTV] No match links found on page")
                return []
            
            print(f"    [HLTV] Found {len(match_links)} match links")
            
            matches = []
            for link in match_links[:5]:  # Limit to 5 matches
                match_href = link.get('href')
                match_id_match = re.search(r'/matches/(\d+)', match_href)
                if not match_id_match:
                    continue
                
                match_id = match_id_match.group(1)
                
                # Try to get stats from the match page
                match_stats = self._get_player_stats_from_match(match_id, player_name)
                if match_stats:
                    matches.append(match_stats)
                
                time.sleep(2)  # Rate limit
            
            print(f"    [HLTV] Extracted {len(matches)} matches with stats")
            return matches
            
        except Exception as e:
            print(f"    [HLTV] Error getting matches: {e}")
            return []
    
    def _get_player_stats_from_match(self, match_id: str, player_name: str) -> Optional[Dict]:
        """Get player stats from a specific match page."""
        try:
            match_url = f"https://www.hltv.org/matches/{match_id}"
            response = self.session.get(match_url, timeout=15)
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for stats section - HLTV has stats in various places
            # Try to find player name and their stats nearby
            page_text = soup.get_text()
            
            # Simple approach: Look for player name, then find numbers nearby
            # This is a fallback if structured parsing fails
            
            # Try structured approach first
            stats_tables = soup.find_all('table')
            for table in stats_tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    row_text = ' '.join([c.get_text() for c in cells]).lower()
                    
                    if player_name.lower() in row_text:
                        # Found player row - extract stats
                        numbers = []
                        for cell in cells:
                            text = cell.get_text(strip=True)
                            num = self._parse_number(text)
                            if num > 0:
                                numbers.append(num)
                        
                        if len(numbers) >= 3:
                            return {
                                'name': player_name,
                                'kills': numbers[0],
                                'deaths': numbers[1] if len(numbers) > 1 else 0,
                                'assists': numbers[2] if len(numbers) > 2 else 0,
                                'match_id': match_id,
                                'date': datetime.now(timezone.utc).isoformat()
                            }
            
            return None
            
        except Exception as e:
            print(f"    [HLTV] Error getting match {match_id}: {e}")
            return None
    
    def _parse_number(self, text: str) -> int:
        """Parse number from text."""
        try:
            cleaned = re.sub(r'[^\d-]', '', text)
            return int(cleaned) if cleaned else 0
        except:
            return 0

# Global instance
esports_data = EsportsDataService()
