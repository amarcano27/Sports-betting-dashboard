import os
import requests
import json
import websockets
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Constants
GRID_API_KEY = os.getenv("GRID_API_KEY") or "40kN8GEckgpfH0U88fad1izQ2KjM0FoGREGJMNyf"
GRID_CENTRAL_URL = "https://api.grid.gg/central-data/graphql"
GRID_LIVE_URL = "wss://api.grid.gg/live-data-feed/v1"  # Example WebSocket URL

class GridDataService:
    """
    Service for interacting with GRID.gg Static Data (Central Data) API.
    """
    def __init__(self, api_key: str = None):
        self.api_key = api_key or GRID_API_KEY
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        self.url = GRID_CENTRAL_URL

    def query(self, query: str, variables: Dict = None) -> Dict:
        """
        Execute a GraphQL query against the Central Data API.
        """
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            response = requests.post(self.url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"GRID API Request failed: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response: {e.response.text}")
            return {}

    def get_active_tournaments(self) -> List[Dict]:
        """
        Fetch active tournaments.
        """
        query = """
        query ActiveTournaments {
            tournaments(filter: { active: true }) {
                edges {
                    node {
                        id
                        name
                        series {
                            id
                            name
                            gameTitle {
                                name
                            }
                        }
                    }
                }
            }
        }
        """
        data = self.query(query)
        return [edge['node'] for edge in data.get('data', {}).get('tournaments', {}).get('edges', [])]

    def get_matches_by_tournament(self, tournament_id: str) -> List[Dict]:
        """
        Fetch matches for a specific tournament.
        """
        query = """
        query TournamentMatches($tournamentId: ID!) {
            tournament(id: $tournamentId) {
                matches {
                    edges {
                        node {
                            id
                            startAt
                            format
                            teams {
                                team {
                                    id
                                    name
                                    code
                                }
                            }
                            games {
                                id
                                status
                            }
                        }
                    }
                }
            }
        }
        """
        data = self.query(query, variables={"tournamentId": tournament_id})
        return [edge['node'] for edge in data.get('data', {}).get('tournament', {}).get('matches', {}).get('edges', [])]

class GridLiveClient:
    """
    Client for connecting to GRID.gg Live Data Feed via WebSocket.
    """
    def __init__(self, api_key: str = None, on_message_callback: Callable[[str], None] = None):
        self.api_key = api_key or GRID_API_KEY
        self.uri = GRID_LIVE_URL
        self.on_message = on_message_callback
        self.running = False

    async def connect(self):
        """
        Connect to the WebSocket feed.
        """
        # Note: Authentication for WebSocket might differ (e.g., query param or initial message)
        # Assuming query param for now: ?key=API_KEY
        # Or header if supported by the client
        
        headers = {"x-api-key": self.api_key}
        
        try:
            logger.info(f"Connecting to GRID Live Feed at {self.uri}...")
            async with websockets.connect(self.uri, extra_headers=headers) as websocket:
                self.running = True
                logger.info("Connected to GRID Live Feed.")
                
                # You might need to send a subscription message here
                # await websocket.send(json.dumps({"type": "subscribe", "topic": "all"}))

                while self.running:
                    message = await websocket.recv()
                    if self.on_message:
                        self.on_message(message)
                    else:
                        print(f"Received: {message[:100]}...")
                        
        except Exception as e:
            logger.error(f"GRID WebSocket Error: {e}")
            self.running = False

    def start(self):
        """
        Start the WebSocket client in an event loop.
        """
        asyncio.run(self.connect())

# Singleton instances
grid_data = GridDataService()
grid_live = GridLiveClient()

