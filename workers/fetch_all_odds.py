"""
Multi-sport odds fetcher — pulls NBA, MLB, NHL, NFL, PGA from The Odds API
and stores games + odds_snapshots in the local database.

Usage:
    python workers/fetch_all_odds.py                  # all active sports
    python workers/fetch_all_odds.py --sport mlb       # single sport
"""
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime, timezone

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from services.db import supabase
from services.odds_api import get_odds_for_sport, get_events

# The Odds API sport keys → display names
SPORT_KEYS = {
    "basketball_nba":       "NBA",
    "baseball_mlb":         "MLB",
    "icehockey_nhl":        "NHL",
    "americanfootball_nfl": "NFL",
    "golf_pga_championship":"PGA",
    "golf_the_masters":     "PGA",
    "golf_us_open":         "PGA",
}

MARKET_MAP = {
    "NBA": "h2h,spreads,totals",
    "MLB": "h2h,spreads,totals",
    "NHL": "h2h,spreads,totals",
    "NFL": "h2h,spreads,totals",
    "PGA": "h2h",
}

# Free tier: 500 req/month (~16/day). Each sport fetch = 1 credit.
# Do NOT auto-fetch player props (1 credit per event = very expensive).
MIN_CREDITS_TO_PROCEED = 10   # stop fetching if below this


def check_credits() -> int:
    """Returns remaining API credits without burning a real request (uses /sports/ which is free)."""
    import requests
    api_key = os.getenv("ODDS_API_KEY", "")
    try:
        r = requests.get(f"https://api.the-odds-api.com/v4/sports/?apiKey={api_key}", timeout=10)
        return int(r.headers.get("x-requests-remaining", 0))
    except Exception:
        return 0


def fetch_sport(sport_key: str, display_name: str):
    markets = MARKET_MAP.get(display_name, "h2h")
    print(f"\n-- {display_name} ({sport_key}) --")
    try:
        games_data = get_odds_for_sport(sport_key, markets=markets)
    except Exception as e:
        print(f"  ERROR fetching odds: {e}")
        return

    if not games_data:
        print("  No games found.")
        return

    games_upserted = 0
    odds_inserted = 0

    for game in games_data:
        external_id = game.get("id")
        home_team   = game.get("home_team", "")
        away_team   = game.get("away_team", "")
        start_time  = game.get("commence_time", "")

        # Upsert game record
        game_row = {
            "sport":       display_name,
            "external_id": external_id,
            "home_team":   home_team,
            "away_team":   away_team,
            "start_time":  start_time,
            "status":      "scheduled",
        }
        result = supabase.table("games").upsert([game_row], on_conflict="external_id").execute()
        db_game = result.data[0] if result.data else None
        if not db_game:
            # Re-fetch to get the id
            rows = supabase.table("games").select("id").eq("external_id", external_id).execute().data
            db_game = rows[0] if rows else None
        if not db_game:
            continue
        game_id = db_game.get("id") or db_game.get("external_id")
        games_upserted += 1

        # Insert odds snapshots
        for bookmaker in game.get("bookmakers", []):
            book = bookmaker.get("key", "unknown")
            for market in bookmaker.get("markets", []):
                market_key = market.get("key", "")
                for outcome in market.get("outcomes", []):
                    label = outcome.get("name", "")
                    price = outcome.get("price")
                    point = outcome.get("point")

                    snap = {
                        "game_id":      game_id,
                        "book":         book,
                        "market_type":  market_key,
                        "market_label": label,
                        "line":         point,
                        "price":        price,
                        "created_at":   datetime.now(timezone.utc).isoformat(),
                    }
                    supabase.table("odds_snapshots").insert([snap]).execute()
                    odds_inserted += 1

    print(f"  Games upserted: {games_upserted} | Odds rows: {odds_inserted}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sport", default="all",
                        help="Sport filter: nba, mlb, nhl, nfl, pga, or all")
    args = parser.parse_args()
    sport_filter = args.sport.lower()

    credits = check_credits()
    print(f"API credits remaining: {credits}")
    if credits < MIN_CREDITS_TO_PROCEED:
        print(f"⚠️  Only {credits} credits left — aborting to preserve budget.")
        return

    fetched = 0
    for key, name in SPORT_KEYS.items():
        if sport_filter != "all" and sport_filter not in (key.lower(), name.lower()):
            continue
        remaining = credits - fetched
        if remaining < MIN_CREDITS_TO_PROCEED:
            print(f"⚠️  Credit guard: {remaining} left, stopping early.")
            break
        fetch_sport(key, name)
        fetched += 1

    print(f"\nDone. Used ~{fetched} credits. Approx {credits - fetched} remaining.")


if __name__ == "__main__":
    main()
