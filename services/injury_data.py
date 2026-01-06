"""
Free Injury Data Service
Fetches injury data from free sources (ESPN, NBA Stats API, etc.)
"""
import requests
from typing import Dict, List, Optional
from datetime import datetime
from services.db import supabase


def fetch_espn_injury_data(team_abbr: str = None) -> List[Dict]:
    """
    Fetch injury data from ESPN (free, public data)
    
    Args:
        team_abbr: Team abbreviation (e.g., 'LAL', 'BOS') or None for all teams
    
    Returns:
        List of injury dicts with player_name, status, injury_type, etc.
    """
    try:
        # ESPN NBA injury endpoint (public, no API key needed)
        # This is a simplified version - actual endpoint may vary
        url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        injuries = []
        for event in data.get("events", []):
            for team in event.get("competitions", [{}])[0].get("competitors", []):
                team_name = team.get("team", {}).get("abbreviation", "")
                
                if team_abbr and team_name != team_abbr:
                    continue
                
                for athlete in team.get("athletes", []):
                    injury_info = athlete.get("injuries", [])
                    if injury_info:
                        injury = injury_info[0]
                        injuries.append({
                            "player_name": athlete.get("displayName", ""),
                            "team": team_name,
                            "status": injury.get("status", {}).get("name", "").lower(),
                            "injury_type": injury.get("type", ""),
                            "date": injury.get("date", ""),
                            "details": injury.get("details", "")
                        })
        
        return injuries
    except Exception as e:
        print(f"Error fetching ESPN injury data: {e}")
        return []


def fetch_nba_stats_injury_data() -> List[Dict]:
    """
    Fetch injury data from NBA Stats API (free, public)
    
    Returns:
        List of injury dicts
    """
    try:
        # NBA Stats API endpoint for injuries
        url = "https://stats.nba.com/stats/injuryreport"
        
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.nba.com/",
            "Accept": "application/json"
        }
        
        params = {
            "LeagueID": "00",
            "GameDate": datetime.now().strftime("%Y-%m-%d")
        }
        
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        injuries = []
        result_sets = data.get("resultSets", [])
        if result_sets:
            headers_list = result_sets[0].get("headers", [])
            rows = result_sets[0].get("rowSet", [])
            
            for row in rows:
                injury_dict = dict(zip(headers_list, row))
                injuries.append({
                    "player_name": injury_dict.get("PLAYER_NAME", ""),
                    "team": injury_dict.get("TEAM_ABBREVIATION", ""),
                    "status": injury_dict.get("INJURY_STATUS", "").lower(),
                    "injury_type": injury_dict.get("INJURY_TYPE", ""),
                    "date": injury_dict.get("GAME_DATE", ""),
                    "details": injury_dict.get("INJURY_DETAILS", "")
                })
        
        return injuries
    except Exception as e:
        print(f"Error fetching NBA Stats injury data: {e}")
        return []


def store_injury_data(injuries: List[Dict]):
    """
    Store injury data in database
    
    Args:
        injuries: List of injury dicts
    """
    stored = 0
    for injury in injuries:
        try:
            player_name = injury.get("player_name")
            if not player_name:
                continue
            
            # Find player
            player_resp = supabase.table("players").select("id").ilike("name", f"%{player_name}%").limit(1).execute()
            if not player_resp.data:
                continue
            
            player_id = player_resp.data[0]["id"]
            
            # Map status to severity
            status = injury.get("status", "").lower()
            severity_map = {
                "out": "out",
                "doubtful": "doubtful",
                "questionable": "questionable",
                "probable": "probable",
                "day-to-day": "questionable"
            }
            severity = severity_map.get(status, "questionable")
            
            # Calculate impact percentage
            impact_map = {
                "out": 100,
                "doubtful": 50,
                "questionable": 25,
                "probable": 10
            }
            impact_pct = impact_map.get(severity, 25)
            
            # Store or update injury
            record = {
                "player_id": player_id,
                "injury_type": injury.get("injury_type"),
                "severity": severity,
                "status": "active",
                "impact_percentage": impact_pct,
                "reported_date": injury.get("date") or datetime.now().date().isoformat(),
                "notes": injury.get("details")
            }
            
            # Upsert (update if exists, insert if new)
            supabase.table("player_injuries").upsert(
                record,
                on_conflict="player_id"
            ).execute()
            stored += 1
        except Exception as e:
            continue
    
    return stored


def fetch_and_store_injuries():
    """
    Fetch injuries from all free sources and store in database
    """
    print("Fetching injury data from free sources...")
    
    all_injuries = []
    
    # Try NBA Stats API first (most reliable)
    print("  Trying NBA Stats API...")
    nba_injuries = fetch_nba_stats_injury_data()
    all_injuries.extend(nba_injuries)
    print(f"    Found {len(nba_injuries)} injuries from NBA Stats")
    
    # Try ESPN as backup
    if not nba_injuries:
        print("  Trying ESPN...")
        espn_injuries = fetch_espn_injury_data()
        all_injuries.extend(espn_injuries)
        print(f"    Found {len(espn_injuries)} injuries from ESPN")
    
    # Store in database
    if all_injuries:
        stored = store_injury_data(all_injuries)
        print(f"✅ Stored {stored} injuries in database")
    else:
        print("⚠️ No injuries found from free sources")
    
    return all_injuries

