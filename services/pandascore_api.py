import requests
import os
from datetime import datetime, timedelta
import time
from dotenv import load_dotenv

load_dotenv()

PANDASCORE_API_KEY = os.getenv("PANDASCORE_API_KEY") or "xent4KgsbMLeZGV42r0v3sriQSWQMP0SGhNYcnWuuAxNyZYuVaA"
BASE_URL = "https://api.pandascore.co"

class PandaScoreAPI:
    def __init__(self, api_key=None):
        self.api_key = api_key or PANDASCORE_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }

    def get_upcoming_matches(self, sport_slug="csgo", page_size=10):
        """
        Fetch upcoming matches.
        """
        if not self.api_key:
            print("! PandaScore API Key missing.")
            return []
            
        url = f"{BASE_URL}/{sport_slug}/matches/upcoming"
        params = {
            "sort": "begin_at",
            "page[size]": page_size,
            "per_page": page_size
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 401:
                print("x PandaScore Unauthorized. Check API Key.")
                return []
            if response.status_code == 429:
                print("! PandaScore Rate Limit Exceeded.")
                return []
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching {sport_slug}: {e}")
            return []

    def get_team_details(self, team_id):
        """
        Fetch team details including roster.
        """
        if not self.api_key:
            return None
            
        url = f"{BASE_URL}/teams/{team_id}"
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None

    def get_player_stats(self, player_id, sport_slug="csgo", limit=5):
        """
        Fetch past matches for a player to calculate stats.
        Cost: 1 request.
        """
        if not self.api_key:
            return []
            
        url = f"{BASE_URL}/players/{player_id}/matches"
        params = {
            "sort": "-begin_at",
            "page[size]": limit,
            "per_page": limit,
            "filter[finished]": "true"
        }
        try:
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error fetching player stats: {e}")
        return []

    def get_match_details(self, match_id):
        """
        Fetch detailed match stats.
        """
        if not self.api_key:
            return None
            
        url = f"{BASE_URL}/matches/{match_id}"
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error fetching match details: {e}")
        return None

    def generate_ai_insight(self, match):
        """
        Generate a text insight based on match data.
        """
        try:
            opponents = match.get("opponents", [])
            if len(opponents) != 2:
                return "Matchup pending opponents."
                
            team_a = opponents[0].get("opponent", {})
            team_b = opponents[1].get("opponent", {})
            name_a = team_a.get("acronym") or team_a.get("name") or "Team A"
            name_b = team_b.get("acronym") or team_b.get("name") or "Team B"
            league = match.get("league", {}).get("name", "Unknown League")
            
            insight = f"{name_a} vs {name_b} in {league}."
            return f"AI Insight: {insight} Watch for map picks favoring {name_a}."
        except Exception:
            return "No insights available."

# Global instance
pandascore = PandaScoreAPI()
