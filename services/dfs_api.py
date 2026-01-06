"""
Third-Party DFS API Integration
Supports OpticOdds, WagerAPI, and Odds-API.io for PrizePicks/Underdog data
"""
import os
import requests
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

# API Configuration
OPTICODDS_API_KEY = os.getenv("OPTICODDS_API_KEY")
OPTICODDS_BASE_URL = "https://api.opticodds.com/v1"

WAGERAPI_KEY = os.getenv("WAGERAPI_KEY")
WAGERAPI_BASE_URL = "https://api.wagerapi.com/v1"

ODDS_API_IO_KEY = os.getenv("ODDS_API_IO_KEY")
ODDS_API_IO_BASE_URL = "https://api.odds-api.io/v1"

# DailyFantasyAPI.io - Most popular solution according to research
DAILYFANTASYAPI_KEY = os.getenv("DAILYFANTASYAPI_KEY")
DAILYFANTASYAPI_BASE_URL = "https://api.dailyfantasyapi.io/v1"


def get_prizepicks_props_opticodds(sport_key: str = "nba") -> List[Dict]:
    """
    Fetch PrizePicks player props from OpticOdds API
    
    Args:
        sport_key: Sport key (nba, nfl, etc.)
    
    Returns:
        List of prop dicts with player_name, prop_type, line, etc.
    """
    if not OPTICODDS_API_KEY:
        print("⚠️ OPTICODDS_API_KEY not found in .env")
        return []
    
    url = f"{OPTICODDS_BASE_URL}/prizepicks/props"
    headers = {
        "Authorization": f"Bearer {OPTICODDS_API_KEY}",
        "Content-Type": "application/json"
    }
    
    params = {
        "sport": sport_key,
        "format": "american"
    }
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        
        # Parse response (adjust based on actual API response structure)
        props = []
        for item in data.get("props", []):
            props.append({
                "player_name": item.get("player_name"),
                "prop_type": item.get("prop_type"),  # points, rebounds, etc.
                "line": item.get("line"),
                "side": item.get("side"),  # over/under
                "source": "prizepicks",
                "book": "PrizePicks",
                "raw": item
            })
        
        return props
    except requests.exceptions.HTTPError as e:
        print(f"Error fetching PrizePicks props from OpticOdds: {e}")
        if e.response.status_code == 401:
            print("  → Check your OPTICODDS_API_KEY")
        return []
    except Exception as e:
        print(f"Error fetching PrizePicks props: {e}")
        return []


def get_underdog_props_oddsapiio(sport_key: str = "nba") -> List[Dict]:
    """
    Fetch Underdog Fantasy player props from Odds-API.io
    
    Args:
        sport_key: Sport key (nba, nfl, etc.)
    
    Returns:
        List of prop dicts
    """
    if not ODDS_API_IO_KEY:
        print("⚠️ ODDS_API_IO_KEY not found in .env")
        return []
    
    url = f"{ODDS_API_IO_BASE_URL}/underdog/props"
    headers = {
        "Authorization": f"Bearer {ODDS_API_IO_KEY}",
        "Content-Type": "application/json"
    }
    
    params = {
        "sport": sport_key
    }
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        
        # Parse response (adjust based on actual API response structure)
        props = []
        for item in data.get("props", []):
            props.append({
                "player_name": item.get("player_name"),
                "prop_type": item.get("prop_type"),
                "line": item.get("line"),
                "side": item.get("side"),
                "source": "underdog",
                "book": "Underdog",
                "raw": item
            })
        
        return props
    except requests.exceptions.HTTPError as e:
        print(f"Error fetching Underdog props from Odds-API.io: {e}")
        if e.response.status_code == 401:
            print("  → Check your ODDS_API_IO_KEY")
        return []
    except Exception as e:
        print(f"Error fetching Underdog props: {e}")
        return []


def get_dfs_props_wagerapi(sport_key: str = "nba", source: str = "prizepicks") -> List[Dict]:
    """
    Fetch DFS props from WagerAPI (supports both PrizePicks and Underdog)
    
    Args:
        sport_key: Sport key (nba, nfl, etc.)
        source: 'prizepicks' or 'underdog'
    
    Returns:
        List of prop dicts
    """
    if not WAGERAPI_KEY:
        print("⚠️ WAGERAPI_KEY not found in .env")
        return []
    
    url = f"{WAGERAPI_BASE_URL}/dfs/{source}/props"
    headers = {
        "Authorization": f"Bearer {WAGERAPI_KEY}",
        "Content-Type": "application/json"
    }
    
    params = {
        "sport": sport_key
    }
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        
        # Parse response (adjust based on actual API response structure)
        props = []
        for item in data.get("props", []):
            props.append({
                "player_name": item.get("player_name"),
                "prop_type": item.get("prop_type"),
                "line": item.get("line"),
                "side": item.get("side"),
                "source": source,
                "book": source.title(),
                "raw": item
            })
        
        return props
    except requests.exceptions.HTTPError as e:
        print(f"Error fetching {source} props from WagerAPI: {e}")
        if e.response.status_code == 401:
            print("  → Check your WAGERAPI_KEY")
        return []
    except Exception as e:
        print(f"Error fetching {source} props: {e}")
        return []


def get_prizepicks_props_dailyfantasyapi(sport_key: str = "nba") -> List[Dict]:
    """
    Fetch PrizePicks/Underdog props from DailyFantasyAPI.io
    This is the MOST POPULAR solution according to developer communities
    
    Args:
        sport_key: Sport key (nba, nfl, etc.)
    
    Returns:
        List of prop dicts
    """
    if not DAILYFANTASYAPI_KEY:
        print("⚠️ DAILYFANTASYAPI_KEY not found in .env")
        print("  → Sign up at: https://www.dailyfantasyapi.io")
        return []
    
    url = f"{DAILYFANTASYAPI_BASE_URL}/props"
    headers = {
        "Authorization": f"Bearer {DAILYFANTASYAPI_KEY}",
        "Content-Type": "application/json"
    }
    
    params = {
        "sport": sport_key,
        "platforms": "prizepicks,underdog"  # Get both
    }
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        
        # Parse response (adjust based on actual API response structure)
        props = []
        for item in data.get("props", []):
            props.append({
                "player_name": item.get("player_name"),
                "prop_type": item.get("prop_type"),
                "line": item.get("line"),
                "side": item.get("side"),
                "source": item.get("platform", "unknown"),  # prizepicks or underdog
                "book": item.get("platform", "Unknown").title(),
                "raw": item
            })
        
        return props
    except requests.exceptions.HTTPError as e:
        print(f"Error fetching DFS props from DailyFantasyAPI.io: {e}")
        if e.response.status_code == 401:
            print("  → Check your DAILYFANTASYAPI_KEY")
            print("  → Sign up at: https://www.dailyfantasyapi.io")
        return []
    except Exception as e:
        print(f"Error fetching DFS props: {e}")
        return []


def get_all_dfs_props(sport_key: str = "nba") -> List[Dict]:
    """
    Fetch DFS props from all available APIs
    
    Priority order (based on popularity):
    1. DailyFantasyAPI.io (most popular in developer communities)
    2. OpticOdds
    3. WagerAPI
    4. Odds-API.io
    
    Returns:
        Combined list of props from all sources
    """
    all_props = []
    
    # Try DailyFantasyAPI.io first (most popular solution)
    if DAILYFANTASYAPI_KEY:
        print("Fetching DFS props from DailyFantasyAPI.io (most popular solution)...")
        dailyfantasy_props = get_prizepicks_props_dailyfantasyapi(sport_key)
        all_props.extend(dailyfantasy_props)
        print(f"  Found {len(dailyfantasy_props)} DFS props")
    
    # Try OpticOdds for PrizePicks
    if OPTICODDS_API_KEY:
        print("Fetching PrizePicks props from OpticOdds...")
        prizepicks_props = get_prizepicks_props_opticodds(sport_key)
        all_props.extend(prizepicks_props)
        print(f"  Found {len(prizepicks_props)} PrizePicks props")
    
    # Try Odds-API.io for Underdog
    if ODDS_API_IO_KEY:
        print("Fetching Underdog props from Odds-API.io...")
        underdog_props = get_underdog_props_oddsapiio(sport_key)
        all_props.extend(underdog_props)
        print(f"  Found {len(underdog_props)} Underdog props")
    
    # Try WagerAPI (supports both)
    if WAGERAPI_KEY:
        print("Fetching DFS props from WagerAPI...")
        wager_prizepicks = get_dfs_props_wagerapi(sport_key, "prizepicks")
        wager_underdog = get_dfs_props_wagerapi(sport_key, "underdog")
        all_props.extend(wager_prizepicks)
        all_props.extend(wager_underdog)
        print(f"  Found {len(wager_prizepicks)} PrizePicks props, {len(wager_underdog)} Underdog props")
    
    if not all_props:
        print("⚠️ No DFS props found. Check API keys in .env:")
        print("  - DAILYFANTASYAPI_KEY (recommended - most popular)")
        print("  - OPTICODDS_API_KEY (for PrizePicks)")
        print("  - ODDS_API_IO_KEY (for Underdog)")
        print("  - WAGERAPI_KEY (for both)")
        print("\n  → DailyFantasyAPI.io: https://www.dailyfantasyapi.io")
    
    return all_props

