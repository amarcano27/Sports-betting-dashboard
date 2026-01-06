import os

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ODDS_API_KEY")
BASE_URL = "https://api.the-odds-api.com/v4"


def get_sports():
    url = f"{BASE_URL}/sports/?apiKey={API_KEY}"
    r = requests.get(url)
    r.raise_for_status()
    return r.json()


def get_odds_for_sport(sport_key, regions="us", markets="h2h,spreads,totals", odds_format="american"):
    url = (
        f"{BASE_URL}/sports/{sport_key}/odds/"
        f"?apiKey={API_KEY}&regions={regions}&markets={markets}&oddsFormat={odds_format}"
    )
    r = requests.get(url)
    r.raise_for_status()
    return r.json()


def get_events(sport_key):
    """Get list of events for a sport"""
    url = f"{BASE_URL}/sports/{sport_key}/events/?apiKey={API_KEY}"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Error fetching events: {e}")
        return []


def get_player_props(sport_key, regions="us", odds_format="american"):
    """
    Get player prop odds from The Odds API v4.
    Player props are non-featured markets and must be fetched per event using /events/{eventId}/odds
    
    Args:
        sport_key: Sport key (e.g., "basketball_nba")
        regions: Comma-separated regions
        odds_format: Odds format (american, decimal, etc.)
    
    Returns:
        List of events with player prop odds
    """
    # For NBA, use specific player prop markets
    # Note: player_pra is not a valid market in v4 API - it must be calculated from points+rebounds+assists
    if sport_key == "basketball_nba":
        markets = "player_points,player_rebounds,player_assists,player_threes,player_steals,player_blocks,player_turnovers"
    elif sport_key == "americanfootball_nfl":
        markets = "player_pass_tds,player_pass_yds,player_pass_completions,player_rush_yds,player_rush_attempts,player_receptions,player_reception_yds,player_anytime_td"
    else:
        markets = "player_props"
    
    # First, get list of events
    print("Fetching events...")
    events = get_events(sport_key)
    
    if not events:
        print("No events found")
        return []
    
    # Filter events to only those happening today or in the next 48 hours
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(hours=48)
    
    filtered_events = []
    for event in events:
        commence_time = event.get("commence_time")
        if commence_time:
            try:
                if isinstance(commence_time, str):
                    event_time = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
                else:
                    event_time = commence_time
                # Only include events happening in the next 48 hours
                if now <= event_time <= cutoff:
                    filtered_events.append(event)
            except:
                # If we can't parse the time, include it anyway
                filtered_events.append(event)
        else:
            # If no time, include it
            filtered_events.append(event)
    
    print(f"Found {len(events)} total events, {len(filtered_events)} within next 48 hours")
    print(f"Fetching player props for {len(filtered_events)} events...")
    
    # Fetch player props for each event
    results = []
    successful = 0
    failed_422 = 0  # 422 = props not available (normal)
    failed_other = 0
    
    for event in filtered_events:
        event_id = event.get("id")
        if not event_id:
            continue
        
        # Fetch odds for this event with player prop markets
        url = (
            f"{BASE_URL}/sports/{sport_key}/events/{event_id}/odds/"
            f"?apiKey={API_KEY}&regions={regions}&markets={markets}&oddsFormat={odds_format}"
        )
        
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            
            event_data = r.json()
            # Only include events that have player props
            if event_data.get("bookmakers"):
                # Check if any bookmaker has player prop markets
                has_player_props = False
                player_prop_count = 0
                for bookmaker in event_data.get("bookmakers", []):
                    for market in bookmaker.get("markets", []):
                        market_key = market.get("key", "")
                        if market_key and market_key.startswith("player_"):
                            has_player_props = True
                            player_prop_count += len(market.get("outcomes", []))
                            break  # Found player props in this bookmaker
                    if has_player_props:
                        break  # Found player props, no need to check more bookmakers
                
                if has_player_props:
                    results.append(event_data)
                    successful += 1
                    if successful <= 3:  # Log first few successes
                        print(f"  Found player props for {event.get('away_team', '?')} @ {event.get('home_team', '?')} ({player_prop_count} outcomes)")
                # else: no props for this event (but no error)
            
            # Log usage info periodically
            if len(results) % 5 == 0 and 'x-requests-remaining' in r.headers:
                print(f"Progress: {len(results)} events with props | Credits remaining: {r.headers['x-requests-remaining']}")
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 422:
                # 422 means player props not available for this event - this is normal, don't spam
                failed_422 += 1
                continue
            elif e.response.status_code == 404:
                # 404 = event not found, skip silently
                continue
            else:
                # Other errors - log but don't spam
                failed_other += 1
                if failed_other <= 3:  # Only show first 3 errors
                    print(f"Error fetching props for event {event_id}: {e}")
            continue
        except Exception as e:
            failed_other += 1
            if failed_other <= 3:  # Only show first 3 errors
                print(f"Error fetching props for event {event_id}: {e}")
            continue
    
    # Summary
    print(f"\nResults: {successful} events with props, {failed_422} events without props (422), {failed_other} other errors")
    
    # Log final usage
    if results and 'x-requests-remaining' in r.headers:
        print(f"\nAPI Credits Remaining: {r.headers['x-requests-remaining']}")
        print(f"API Credits Used: {r.headers.get('x-requests-used', 'N/A')}")
    
    print(f"Found {len(results)} events with player props")
    return results

