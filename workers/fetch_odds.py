import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.odds_api import get_odds_for_sport
from services.db import supabase
from datetime import datetime

SPORTS = {
    "NBA": "basketball_nba",
    "NFL": "americanfootball_nfl",
    "MLB": "baseball_mlb",
    "NHL": "icehockey_nhl",
    "NCAAB": "basketball_ncaab",
    "NCAAF": "americanfootball_ncaaf",
    "Soccer": "soccer_usa_mls",
    # Esports are not supported by The Odds API currently.
    # Using PandaScore API (separate worker) for Esports data.
    # "CS2": "esports_csgo",
    # "LoL": "esports_league_of_legends",
    # "Dota2": "esports_dota_2",
    # "Valorant": "esports_valorant"
}


def upsert_game(sport, event):
    start_time = datetime.fromisoformat(event["commence_time"].replace("Z", "+00:00"))
    data = {
        "sport": sport,
        "external_id": event["id"],
        "home_team": event["home_team"],
        "away_team": event["away_team"],
        "start_time": start_time.isoformat(),
        "status": "scheduled"
    }
    supabase.table("games").upsert(data, on_conflict="external_id").execute()


def store_odds(sport_key, sport_label):
    try:
        print(f"Fetching odds for {sport_label} ({sport_key})...")
        odds_data = get_odds_for_sport(sport_key)
        print(f"Found {len(odds_data)} events for {sport_label}")
    except Exception as e:
        print(f"Error fetching odds for {sport_label} ({sport_key}): {e}")
        import traceback
        traceback.print_exc()
        return
    
    games_stored = 0
    odds_stored = 0
    
    # Batch odds records for faster inserts
    odds_batch = []
    BATCH_SIZE = 50
    
    for event in odds_data:
        try:
            upsert_game(sport_label, event)
            games_stored += 1
            game_resp = supabase.table("games").select("id").eq("external_id", event["id"]).execute()
            if not game_resp.data:
                continue
            game_id = game_resp.data[0]["id"]
            
            for bookmaker in event.get("bookmakers", []):
                book_name = bookmaker["title"]
                for market in bookmaker.get("markets", []):
                    m_key = market["key"]
                    for outcome in market.get("outcomes", []):
                        record = {
                            "game_id": game_id,
                            "book": book_name,
                            "market_type": m_key,
                            "market_label": outcome["name"],
                            "line": outcome.get("point"),
                            "price": outcome["price"],
                            "raw": outcome,
                        }
                        odds_batch.append(record)
                        
                        # Insert in batches to avoid timeouts
                        if len(odds_batch) >= BATCH_SIZE:
                            try:
                                supabase.table("odds_snapshots").insert(odds_batch).execute()
                                odds_stored += len(odds_batch)
                                odds_batch = []
                            except Exception as batch_error:
                                print(f"  Warning: Batch insert failed, retrying individually...")
                                # Fallback: insert one by one with retry
                                for r in odds_batch:
                                    try:
                                        supabase.table("odds_snapshots").insert(r).execute()
                                        odds_stored += 1
                                    except:
                                        pass
                                odds_batch = []
        except Exception as event_error:
            print(f"  Error processing event: {event_error}")
            continue
    
    # Insert remaining batch
    if odds_batch:
        try:
            supabase.table("odds_snapshots").insert(odds_batch).execute()
            odds_stored += len(odds_batch)
        except Exception as final_error:
            print(f"  Warning: Final batch insert failed: {final_error}")
    
    print(f"Stored {games_stored} games and {odds_stored} odds records for {sport_label}")


def run_all():
    print("Starting to fetch odds for all sports...")
    for label, key in SPORTS.items():
        try:
            store_odds(key, label)
        except Exception as e:
            print(f"Failed to fetch odds for {label}: {e}")
            import traceback
            traceback.print_exc()
            continue  # Continue with next sport
    print("Done fetching odds!")


if __name__ == "__main__":
    run_all()

