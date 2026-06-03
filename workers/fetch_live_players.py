"""
Fetch tonight's players + recent game logs into Supabase.
Uses FREE public APIs — zero Odds API credits consumed.

Usage:
    python workers/fetch_live_players.py --sport nba
    python workers/fetch_live_players.py --sport mlb
    python workers/fetch_live_players.py --sport nhl
    python workers/fetch_live_players.py --sport all
"""
import sys, argparse, time
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from services.db import supabase
from services.player_service import (
    # NBA
    nba_get_all_players, nba_get_player_gamelog,
    NBA_FULL_TO_ABBR,
    # MLB
    mlb_get_roster, mlb_get_batter_gamelog, mlb_get_pitcher_gamelog,
    mlb_get_team_id,
    # NHL
    nhl_get_roster, nhl_get_player_gamelog,
    NHL_FULL_TO_ABBR,
)

LAST_N_GAMES = 15   # game logs to fetch per player
KEY_PLAYERS_ONLY = True  # only fetch key players (starters / known props candidates)


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
_PLAYER_COLS = None

def _get_player_cols() -> set:
    """Cache the actual columns available in the players table."""
    global _PLAYER_COLS
    if _PLAYER_COLS is None:
        try:
            row = supabase.table("players").select("*").limit(1).execute().data
            if row:
                _PLAYER_COLS = set(row[0].keys())
            else:
                # Insert a probe row to discover columns
                _PLAYER_COLS = {
                    "id","external_id","name","position","team","sport",
                    "raw_data","created_at","updated_at"
                }
        except Exception:
            _PLAYER_COLS = {"id","external_id","name","position","team","sport","raw_data","created_at","updated_at"}
    return _PLAYER_COLS


def upsert_player(player: dict) -> str | None:
    """Upsert player, return internal DB id. Strips unknown columns."""
    cols = _get_player_cols()
    # Always keep headshot + jersey in raw_data for later display
    raw_extra = {}
    for k in ("headshot_url", "jersey_number", "headshot"):
        if k in player:
            raw_extra[k] = player.pop(k)

    # Filter to only columns that exist in the schema
    safe = {k: v for k, v in player.items() if k in cols}

    # Store extra data in raw_data JSON
    if raw_extra:
        import json
        existing_raw = safe.get("raw_data")
        if isinstance(existing_raw, str):
            try:
                existing_raw = json.loads(existing_raw)
            except Exception:
                existing_raw = {}
        if not isinstance(existing_raw, dict):
            existing_raw = {}
        existing_raw.update(raw_extra)
        safe["raw_data"] = json.dumps(existing_raw)

    if not safe.get("external_id"):
        return None

    try:
        supabase.table("players").upsert([safe], on_conflict="external_id").execute()
        rows = supabase.table("players").select("id").eq("external_id", safe["external_id"]).execute().data
        return rows[0]["id"] if rows else None
    except Exception as e:
        print(f"  [upsert_player] {e}")
        return None


def upsert_stats(player_id: str, game_id: str | None, stats: dict):
    """Insert game stats row; skip if already exists."""
    row = {"player_id": player_id, **stats}
    if game_id:
        row["game_id"] = game_id
    try:
        # Use date + player as natural key
        existing = (
            supabase.table("player_game_stats")
            .select("id")
            .eq("player_id", player_id)
            .eq("date", stats.get("date", ""))
            .execute()
            .data
        )
        if not existing:
            supabase.table("player_game_stats").insert([row]).execute()
    except Exception as e:
        print(f"  [stats insert] {e}")


def get_db_game_id(date_str: str, opponent: str, home: bool) -> str | None:
    """Try to find a game ID from the DB for a stat row."""
    # Rough match: look for a game on same date
    try:
        rows = supabase.table("games").select("id,away_team,home_team").execute().data or []
        for g in rows:
            if opponent and (opponent in (g.get("away_team","") or "") or
                             opponent in (g.get("home_team","") or "")):
                return g["id"]
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────────────────────
# NBA
# ─────────────────────────────────────────────────────────────
def fetch_nba():
    print("\n=== NBA Player Fetch ===")

    # Get tonight's NBA games from Supabase
    nba_games = supabase.table("games").select("*").eq("sport", "NBA").execute().data or []
    if not nba_games:
        print("No NBA games in DB. Run fetch_all_odds first.")
        return

    teams_needed = set()
    for g in nba_games:
        away_abbr = NBA_FULL_TO_ABBR.get(g["away_team"])
        home_abbr = NBA_FULL_TO_ABBR.get(g["home_team"])
        if away_abbr: teams_needed.add(away_abbr)
        if home_abbr: teams_needed.add(home_abbr)

    print(f"Teams: {teams_needed}")

    # Fetch full player list once
    print("Fetching all NBA players...")
    all_players = nba_get_all_players()
    print(f"  Found {len(all_players)} active players")

    # Filter to only teams playing tonight
    tonight_players = [p for p in all_players if p.get("team") in teams_needed]
    print(f"  {len(tonight_players)} players on tonight's teams")

    fetched, skipped = 0, 0
    for i, player in enumerate(tonight_players):
        pid_ext = player.get("external_id")
        pname   = player.get("name", "?")

        # Upsert player record
        db_id = upsert_player(player)
        if not db_id:
            skipped += 1
            continue

        # Fetch game logs
        logs = nba_get_player_gamelog(pid_ext, last_n=LAST_N_GAMES)
        if not logs:
            skipped += 1
            time.sleep(0.5)
            continue

        for log in logs:
            gid = get_db_game_id(log["date"], log.get("opponent",""), log.get("home", True))
            upsert_stats(db_id, gid, {
                "date":                     log["date"],
                "opponent":                 log.get("opponent", ""),
                "home":                     log.get("home", True),
                "minutes_played":           log.get("minutes", 0),
                "points":                   log.get("points", 0),
                "rebounds":                 log.get("rebounds", 0),
                "assists":                  log.get("assists", 0),
                "steals":                   log.get("steals", 0),
                "blocks":                   log.get("blocks", 0),
                "turnovers":                log.get("turnovers", 0),
                "field_goals_made":         log.get("fg_made", 0),
                "field_goals_attempted":    log.get("fg_att", 0),
                "three_pointers_made":      log.get("fg3_made", 0),
                "three_pointers_attempted": log.get("fg3_att", 0),
                "free_throws_made":         log.get("ft_made", 0),
                "free_throws_attempted":    log.get("ft_att", 0),
            })

        fetched += 1
        if (i+1) % 10 == 0:
            print(f"  Progress: {i+1}/{len(tonight_players)} ({fetched} fetched, {skipped} skipped)")
        time.sleep(0.8)  # respect NBA stats API rate limit

    print(f"NBA done: {fetched} players fetched, {skipped} skipped")


# ─────────────────────────────────────────────────────────────
# MLB
# ─────────────────────────────────────────────────────────────
def fetch_mlb():
    print("\n=== MLB Player Fetch ===")

    from dashboard.mlb_page import TEAM_ABBR

    mlb_games = supabase.table("games").select("*").eq("sport", "MLB").execute().data or []
    if not mlb_games:
        print("No MLB games in DB.")
        return

    # Collect all team abbreviations from tonight's games
    teams_needed = set()
    for g in mlb_games:
        teams_needed.add(TEAM_ABBR.get(g["away_team"]))
        teams_needed.add(TEAM_ABBR.get(g["home_team"]))
    teams_needed.discard(None)
    print(f"Teams: {teams_needed}")

    fetched = 0
    for team_abbr in teams_needed:
        team_id = mlb_get_team_id(team_abbr)
        if not team_id:
            print(f"  No team ID for {team_abbr}")
            continue

        roster = mlb_get_roster(team_id)
        print(f"  {team_abbr}: {len(roster)} roster players")

        # For MLB, prioritize pitchers + key position players
        pitchers = [p for p in roster if p.get("position") in ("P", "SP", "RP")]
        hitters  = [p for p in roster if p.get("position") not in ("P", "SP", "RP")]

        for player in pitchers[:12] + hitters[:15]:
            pid_ext = player.get("external_id")
            db_id   = upsert_player({**player, "team": team_abbr})
            if not db_id:
                continue

            # Fetch pitching logs
            if player.get("position") in ("P", "SP", "RP"):
                logs = mlb_get_pitcher_gamelog(pid_ext, last_n=10)
                for log in logs:
                    upsert_stats(db_id, None, {
                        "date":     log["date"],
                        "opponent": log["opponent"],
                        "home":     True,
                        "points":   log.get("k", 0),       # K = "points" proxy for pitchers
                        "assists":  log.get("ip", 0),      # IP = assists proxy
                        "turnovers": log.get("bb", 0),     # BB = turnovers proxy
                        "blocks":   log.get("er", 0),      # ER = blocks proxy
                    })
            else:
                logs = mlb_get_batter_gamelog(pid_ext, last_n=LAST_N_GAMES)
                for log in logs:
                    upsert_stats(db_id, None, {
                        "date":         log["date"],
                        "opponent":     log["opponent"],
                        "home":         log.get("home", True),
                        "points":       log.get("hits", 0),
                        "rebounds":     log.get("tb", 0),  # total bases
                        "assists":      log.get("hr", 0),  # home runs
                        "blocks":       log.get("rbi", 0),
                        "turnovers":    log.get("k", 0),
                        "steals":       log.get("bb", 0),
                    })

            fetched += 1
            time.sleep(0.3)

    print(f"MLB done: {fetched} players fetched")


# ─────────────────────────────────────────────────────────────
# NHL
# ─────────────────────────────────────────────────────────────
def fetch_nhl():
    print("\n=== NHL Player Fetch ===")

    nhl_games = supabase.table("games").select("*").eq("sport", "NHL").execute().data or []
    if not nhl_games:
        print("No NHL games in DB.")
        return

    teams_needed = set()
    for g in nhl_games:
        away_abbr = NHL_FULL_TO_ABBR.get(g["away_team"])
        home_abbr = NHL_FULL_TO_ABBR.get(g["home_team"])
        if away_abbr: teams_needed.add(away_abbr)
        if home_abbr: teams_needed.add(home_abbr)

    print(f"Teams: {teams_needed}")
    fetched = 0

    for team_abbr in teams_needed:
        roster = nhl_get_roster(team_abbr)
        print(f"  {team_abbr}: {len(roster)} players")

        for player in roster[:20]:  # top 20 per team
            pid_ext = player.get("external_id")
            db_id   = upsert_player(player)
            if not db_id:
                continue

            logs = nhl_get_player_gamelog(pid_ext, last_n=LAST_N_GAMES)
            for log in logs:
                upsert_stats(db_id, None, {
                    "date":         log["date"],
                    "opponent":     log["opponent"],
                    "home":         log.get("home", True),
                    "points":       log.get("goals", 0),
                    "rebounds":     log.get("assists", 0),
                    "assists":      log.get("points", 0),
                    "steals":       log.get("shots", 0),
                    "blocks":       log.get("hits", 0),
                    "turnovers":    log.get("pims", 0),
                })

            fetched += 1
            time.sleep(0.3)

    print(f"NHL done: {fetched} players fetched")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sport", default="all",
                        help="Sport: nba, mlb, nhl, all")
    args = parser.parse_args()
    sport = args.sport.lower()

    if sport in ("nba", "all"):
        fetch_nba()
    if sport in ("mlb", "all"):
        fetch_mlb()
    if sport in ("nhl", "all"):
        fetch_nhl()

    print("\nDone.")

if __name__ == "__main__":
    main()
