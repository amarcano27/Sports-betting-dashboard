import requests
import os
import json
import logging
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GridDataService:
    """
    Service for interacting with GRID.gg API.
    Uses the Open Platform endpoint by default.
    """
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or os.getenv("GRID_API_KEY")
        if not self.api_key:
            # Fallback to the provided key
            self.api_key = "40kN8GEckgpfH0U88fad1izQ2KjM0FoGREGJMNyf"
            
        # Use the OP endpoint which is confirmed to work
        self.graphql_url = base_url or "https://api-op.grid.gg/central-data/graphql"
        
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

    def check_connection(self) -> bool:
        """
        Check connection to GRID.gg API using introspection.
        """
        query = """
        query {
            __schema {
                queryType {
                    name
                }
            }
        }
        """
        try:
            response = requests.post(self.graphql_url, headers=self.headers, json={"query": query}, timeout=10)
            if response.status_code == 200 and "data" in response.json():
                logger.info("Successfully connected to GRID.gg API")
                return True
            else:
                logger.error(f"Failed to connect: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False

    def get_teams(self, search_term: str = None, limit: int = 10) -> List[Dict]:
        """
        Fetch teams, optionally filtering by name.
        """
        filter_str = f', filter: {{ name: {{ contains: "{search_term}" }} }}' if search_term else ""
        
        query = f"""
        query GetTeams {{
            teams(first: {limit}{filter_str}) {{
                edges {{
                    node {{
                        id
                        name
                        nameShortened
                        code
                        logoUrl
                        rating
                    }}
                }}
            }}
        }}
        """
        
        try:
            response = requests.post(
                self.graphql_url, 
                headers=self.headers, 
                json={"query": query}, 
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if "errors" in data:
                    logger.error(f"GraphQL Errors: {data['errors']}")
                    return []
                
                edges = data.get("data", {}).get("teams", {}).get("edges", [])
                return [edge["node"] for edge in edges]
            else:
                logger.error(f"API Error: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return []

    def get_series(self, limit: int = 10) -> List[Dict]:
        """
        Fetch series (if authorized).
        """
        query = """
        query GetSeries($limit: Int) {
            allSeries(first: $limit) {
                edges {
                    node {
                        id
                        startTimeScheduled
                        format {
                            name
                        }
                        tournament {
                            name
                        }
                        teams {
                            baseInfo {
                                name
                                id
                            }
                        }
                    }
                }
            }
        }
        """
        
        variables = {"limit": limit}
        
        try:
            response = requests.post(
                self.graphql_url, 
                headers=self.headers, 
                json={"query": query, "variables": variables}, 
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if "errors" in data:
                    logger.error(f"GraphQL Errors: {data['errors']}")
                    return []
                
                edges = data.get("data", {}).get("allSeries", {}).get("edges", [])
                return [edge["node"] for edge in edges]
            else:
                logger.error(f"API Error: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return []
            
    def get_tournaments(self, limit: int = 5) -> List[Dict]:
        """
        Fetch tournaments.
        """
        query = """
        query GetTournaments($limit: Int) {
            tournaments(first: $limit) {
                edges {
                    node {
                        id
                        name
                        nameShortened
                    }
                }
            }
        }
        """
        variables = {"limit": limit}
        try:
            response = requests.post(
                self.graphql_url, 
                headers=self.headers, 
                json={"query": query, "variables": variables}, 
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                edges = data.get("data", {}).get("tournaments", {}).get("edges", [])
                return [edge["node"] for edge in edges]
            return []
        except:
            return []

    def get_team_history(self, team_id: str, limit: int = 10) -> List[Dict]:
        """
        Fetch match history for a team.
        """
        query = """
        query GetTeamHistory($teamId: ID!, $limit: Int) {
            allSeries(
                first: $limit, 
                filter: { teamId: $teamId },
                orderBy: startTimeScheduled,
                orderDirection: DESC
            ) {
                edges {
                    node {
                        id
                        startTimeScheduled
                        title {
                            name
                        }
                        tournament {
                            name
                        }
                        format {
                            name
                        }
                        teams {
                            baseInfo {
                                name
                                id
                                logoUrl
                            }
                        }
                    }
                }
            }
        }
        """
        variables = {"teamId": team_id, "limit": limit}
        try:
            response = requests.post(
                self.graphql_url, 
                headers=self.headers, 
                json={"query": query, "variables": variables}, 
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                edges = data.get("data", {}).get("allSeries", {}).get("edges", [])
                return [edge["node"] for edge in edges]
            return []
        except Exception as e:
            logger.error(f"History fetch failed: {e}")
            return []

    def get_players(self, search_term: str = None, limit: int = 10) -> List[Dict]:
        """
        Fetch players, optionally filtering by nickname.
        """
        filter_str = f', filter: {{ nickname: {{ contains: "{search_term}" }} }}' if search_term else ""
        
        query = f"""
        query GetPlayers {{
            players(first: {limit}{filter_str}) {{
                edges {{
                    node {{
                        id
                        nickname
                        fullName
                        age
                        nationality
                        team {{
                            id
                            name
                            logoUrl
                        }}
                        roles
                        imageUrl
                    }}
                }}
            }}
        }}
        """
        
        try:
            response = requests.post(
                self.graphql_url, 
                headers=self.headers, 
                json={"query": query}, 
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if "errors" in data:
                    logger.error(f"GraphQL Errors: {data['errors']}")
                    return []
                
                edges = data.get("data", {}).get("players", {}).get("edges", [])
                return [edge["node"] for edge in edges]
            else:
                logger.error(f"API Error: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return []

# Global instance
grid_service = GridDataService()
