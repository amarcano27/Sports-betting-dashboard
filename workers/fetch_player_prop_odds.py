"""
Fetch and store player prop odds (including alt lines where available).

Usage:
  python workers/fetch_player_prop_odds.py --sport nba
  python workers/fetch_player_prop_odds.py --sport mlb
  python workers/fetch_player_prop_odds.py --sport all
"""
import argparse
import json
import sys
from pathlib import Path
from rapidfuzz import process

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from services.odds_api import get_player_props

SPORT_KEY_MAP = {
    "nba": ("basketball_nba", "NBA"),
    "mlb": ("baseball_mlb", "MLB"),
}

PREFERRED_BOOKS = {
    "Pinnacle",
    "Bovada",
    "DraftKings",
    "FanDuel",
    "BetMGM",
    "Caesars",
    "bet365",
}

MARKET_TO_PROP_TYPE = {
    # NBA
    "player_points": "points",
    "player_rebounds": "rebounds",
    "player_assists": "assists",
    "player_threes": "threes",
    "player_steals": "steals",
    "player_blocks": "blocks",
    "player_turnovers": "turnovers",
    # MLB
    "batter_hits": "hits",
    "batter_total_bases": "total_bases",
    "batter_home_runs": "home_runs",
    "batter_rbis": "rbis",
    "batter_runs_scored": "runs_scored",
    "batter_strikeouts": "batter_strikeouts",
    "pitcher_strikeouts": "pitcher_strikeouts",
    "pitcher_hits_allowed": "pitcher_hits_allowed",
    "pitcher_walks": "pitcher_walks",
    "pitcher_outs": "pitcher_outs",
}


def _load_players_for_sport(sport_name: str):
    rows = (
        supabase.table("players")
        .select("id,name,sport")
        .eq("sport", sport_name)
        .execute()
        .data
        or []
    )
    names = {r["name"]: r["id"] for r in rows if r.get("name")}
    return rows, names


def _find_player_id(player_name: str, player_names: dict):
    if not player_name:
        return None
    # exact (case-insensitive)
    for db_name, db_id in player_names.items():
        if db_name.lower() == player_name.lower():
            return db_id
    # contains
    for db_name, db_id in player_names.items():
        if player_name.lower() in db_name.lower() or db_name.lower() in player_name.lower():
            return db_id
    # fuzzy
    matches = process.extract(player_name, list(player_names.keys()), limit=1, score_cutoff=74)
    if matches:
        return player_names[matches[0][0]]
    return None


def _game_id_for_event(event_id: str):
    resp = supabase.table("games").select("id").eq("external_id", event_id).execute()
    if resp.data:
        return resp.data[0]["id"]
    return None


def store_player_prop_odds(sport_key: str, sport_name: str):
    print(f"\n=== Fetching player props for {sport_name} ===")
    events = get_player_props(sport_key)
    if not events:
        print("No player prop events returned.")
        return

    players, player_names = _load_players_for_sport(sport_name)
    if not players:
        print(f"No {sport_name} players found in DB. Run player sync first.")
        return

    inserted = 0
    updated = 0
    skipped_player = 0

    for event in events:
        game_id = _game_id_for_event(event.get("id"))
        if not game_id:
            continue

        for bookmaker in event.get("bookmakers", []):
            book_name = bookmaker.get("title") or bookmaker.get("key") or "unknown"

            for market in bookmaker.get("markets", []):
                market_key = market.get("key", "")
                prop_type = MARKET_TO_PROP_TYPE.get(market_key, market_key.replace("player_", ""))

                # The API provides over/under outcomes per player+line.
                for outcome in market.get("outcomes", []):
                    player_name = outcome.get("description", "")
                    line = outcome.get("point")
                    price = outcome.get("price")
                    side = (outcome.get("name") or "").strip().lower()  # over/under
                    if not player_name or line is None or price is None:
                        continue
                    if side not in ("over", "under"):
                        continue

                    player_id = _find_player_id(player_name, player_names)
                    if not player_id:
                        skipped_player += 1
                        continue

                    existing = (
                        supabase.table("player_prop_odds")
                        .select("id,over_price,under_price")
                        .eq("player_id", player_id)
                        .eq("game_id", game_id)
                        .eq("book", book_name)
                        .eq("prop_type", prop_type)
                        .eq("line", line)
                        .limit(1)
                        .execute()
                    )

                    record = {
                        "player_id": player_id,
                        "game_id": game_id,
                        "book": book_name,
                        "prop_type": prop_type,
                        "line": line,
                        "raw": json.dumps(
                            {
                                "event_id": event.get("id"),
                                "bookmaker": book_name,
                                "market_key": market_key,
                                "outcome": outcome,
                                "preferred_book": book_name in PREFERRED_BOOKS,
                            }
                        ),
                    }
                    if side == "over":
                        record["over_price"] = price
                    else:
                        record["under_price"] = price

                    if existing.data:
                        row_id = existing.data[0]["id"]
                        supabase.table("player_prop_odds").update(record).eq("id", row_id).execute()
                        updated += 1
                    else:
                        supabase.table("player_prop_odds").insert(record).execute()
                        inserted += 1

    print(f"Done: inserted={inserted} updated={updated} skipped_player={skipped_player}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sport", default="nba", help="nba|mlb|all")
    args = parser.parse_args()
    sport_arg = args.sport.lower().strip()

    if sport_arg == "all":
        for s in ("nba", "mlb"):
            key, name = SPORT_KEY_MAP[s]
            store_player_prop_odds(key, name)
        return

    if sport_arg not in SPORT_KEY_MAP:
        raise SystemExit("Invalid --sport. Use nba, mlb, or all.")

    key, name = SPORT_KEY_MAP[sport_arg]
    store_player_prop_odds(key, name)


if __name__ == "__main__":
    main()

