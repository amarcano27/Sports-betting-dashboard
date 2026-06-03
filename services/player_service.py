"""
Unified Player Data Service
===========================
Fetches players, rosters, headshots, and game logs from FREE public APIs.
Zero Odds API credits consumed.

Sources:
  NBA  → stats.nba.com (public, no key required)
  MLB  → statsapi.mlb.com (official MLB API, free)
  NHL  → api-web.nhle.com (official NHL API v2, free)

Headshots:
  NBA  → cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png
  MLB  → img.mlbstatic.com (requires mlb people ID)
  NHL  → assets.nhle.com/mugs/nhl/.../{player_id}.png
"""
import requests
import time
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────
NBA_BASE = "https://stats.nba.com/stats"
MLB_BASE = "https://statsapi.mlb.com/api/v1"
NHL_BASE = "https://api-web.nhle.com/v1"

NBA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer":    "https://www.nba.com/",
    "Origin":     "https://www.nba.com",
    "Accept":     "application/json, text/plain, */*",
}

REQUEST_TIMEOUT = 20
CURRENT_SEASON  = "2025-26"
CURRENT_YEAR    = "2026"

# ─────────────────────────────────────────────────────────────
# NBA
# ─────────────────────────────────────────────────────────────

def nba_headshot_url(player_id: int | str) -> str:
    return f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"


def nba_team_logo_url(team_id: int | str) -> str:
    return f"https://cdn.nba.com/logos/nba/{team_id}/global/L/logo.svg"


def nba_get_scoreboard() -> list[dict]:
    """Today's NBA games with team IDs and scores."""
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
    try:
        r = requests.get(url, headers=NBA_HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        return data.get("scoreboard", {}).get("games", [])
    except Exception as e:
        print(f"[NBA scoreboard] {e}")
        return []


def nba_get_all_players(season: str = CURRENT_SEASON) -> list[dict]:
    """
    All active NBA players for a season.
    Returns list of dicts with: id, name, team, position, jersey.
    """
    url = f"{NBA_BASE}/commonallplayers"
    params = {
        "Season":           season,
        "LeagueID":         "00",
        "IsOnlyCurrentSeason": "1",
    }
    try:
        r = requests.get(url, headers=NBA_HEADERS, params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data   = r.json()
        rs     = data["resultSets"][0]
        cols   = [c.lower() for c in rs["headers"]]
        players = []
        for row in rs["rowSet"]:
            d = dict(zip(cols, row))
            players.append({
                "external_id":   str(d.get("person_id", "")),
                "name":          d.get("display_first_last", ""),
                "team":          d.get("team_abbreviation", ""),
                "position":      d.get("position", ""),
                "jersey_number": d.get("jersey", ""),
                "sport":         "NBA",
                "headshot_url":  nba_headshot_url(d.get("person_id", "")),
            })
        return players
    except Exception as e:
        print(f"[NBA all players] {e}")
        return []


def nba_get_team_roster(team_abbr: str, season: str = CURRENT_SEASON) -> list[dict]:
    """Get roster for a specific NBA team abbreviation."""
    all_players = nba_get_all_players(season)
    return [p for p in all_players if p.get("team") == team_abbr]


def nba_get_player_gamelog(player_id: int | str, season: str = CURRENT_SEASON,
                            last_n: int = 15) -> list[dict]:
    """
    Recent game logs for one NBA player.
    Returns last_n games sorted newest first.
    Fields: date, opponent, home, min, pts, reb, ast, stl, blk, tov, fg, 3p, ft, result
    """
    url = f"{NBA_BASE}/playergamelog"
    params = {
        "PlayerID":   player_id,
        "Season":     season,
        "SeasonType": "Regular Season",
    }
    try:
        r = requests.get(url, headers=NBA_HEADERS, params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        rs   = data["resultSets"][0]
        cols = [c.lower() for c in rs["headers"]]
        games = []
        for row in rs["rowSet"][:last_n]:
            d = dict(zip(cols, row))
            games.append({
                "date":       d.get("game_date", ""),
                "matchup":    d.get("matchup", ""),
                "home":       "@" not in d.get("matchup", ""),
                "minutes":    d.get("min", 0),
                "points":     d.get("pts", 0),
                "rebounds":   d.get("reb", 0),
                "assists":    d.get("ast", 0),
                "steals":     d.get("stl", 0),
                "blocks":     d.get("blk", 0),
                "turnovers":  d.get("tov", 0),
                "fg_made":    d.get("fgm", 0),
                "fg_att":     d.get("fga", 0),
                "fg3_made":   d.get("fg3m", 0),
                "fg3_att":    d.get("fg3a", 0),
                "ft_made":    d.get("ftm", 0),
                "ft_att":     d.get("fta", 0),
                "plus_minus": d.get("plus_minus", 0),
                "result":     d.get("wl", ""),
                "opponent":   _parse_opponent(d.get("matchup", "")),
            })
        return games
    except Exception as e:
        print(f"[NBA gamelog {player_id}] {e}")
        return []


def _parse_opponent(matchup: str) -> str:
    """'LAL @ BOS' → 'BOS',  'LAL vs. BOS' → 'BOS'"""
    if "@" in matchup:
        return matchup.split("@")[-1].strip()
    if "vs." in matchup:
        return matchup.split("vs.")[-1].strip()
    return matchup


def nba_get_player_stats(player_id: int | str, season: str = CURRENT_SEASON) -> dict:
    """Season averages for a player."""
    url = f"{NBA_BASE}/playerdashboardbyyearoveryear"
    params = {
        "PlayerID":      player_id,
        "Season":        season,
        "SeasonType":    "Regular Season",
        "PerMode":       "PerGame",
        "MeasureType":   "Base",
    }
    try:
        r = requests.get(url, headers=NBA_HEADERS, params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data  = r.json()
        rs    = data["resultSets"][0]
        cols  = [c.lower() for c in rs["headers"]]
        rows  = rs["rowSet"]
        if not rows:
            return {}
        d = dict(zip(cols, rows[-1]))   # last row = current season
        return {
            "games":     d.get("gp", 0),
            "points":    d.get("pts", 0),
            "rebounds":  d.get("reb", 0),
            "assists":   d.get("ast", 0),
            "steals":    d.get("stl", 0),
            "blocks":    d.get("blk", 0),
            "turnovers": d.get("tov", 0),
            "fg_pct":    d.get("fg_pct", 0),
            "fg3_pct":   d.get("fg3_pct", 0),
            "ft_pct":    d.get("ft_pct", 0),
            "minutes":   d.get("min", 0),
        }
    except Exception as e:
        print(f"[NBA season avg {player_id}] {e}")
        return {}


def nba_search_player(name: str) -> list[dict]:
    """Search all players by name (fuzzy)."""
    try:
        from rapidfuzz import process
        all_players = nba_get_all_players()
        names = [p["name"] for p in all_players]
        matches = process.extract(name, names, limit=5, score_cutoff=60)
        result = []
        for match_name, score, idx in matches:
            result.append({**all_players[idx], "match_score": score})
        return result
    except Exception as e:
        print(f"[NBA search] {e}")
        return []


# ─────────────────────────────────────────────────────────────
# MLB
# ─────────────────────────────────────────────────────────────

def mlb_headshot_url(mlb_id: int | str) -> str:
    return (
        f"https://img.mlbstatic.com/mlb-photos/image/upload/"
        f"d_people:generic:headshot:67:current.png/w_213,q_auto:best/"
        f"v1/people/{mlb_id}/headshot/67/current"
    )


def mlb_get_roster(team_id: int, season: str = CURRENT_YEAR) -> list[dict]:
    """Get 40-man roster for an MLB team."""
    url = f"{MLB_BASE}/teams/{team_id}/roster"
    params = {"rosterType": "40Man", "season": season}
    try:
        r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        players = []
        for entry in data.get("roster", []):
            p = entry.get("person", {})
            pid = p.get("id")
            players.append({
                "external_id":  str(pid),
                "name":         p.get("fullName", ""),
                "position":     entry.get("position", {}).get("abbreviation", ""),
                "jersey_number": entry.get("jerseyNumber", ""),
                "sport":        "MLB",
                "headshot_url": mlb_headshot_url(pid),
            })
        return players
    except Exception as e:
        print(f"[MLB roster {team_id}] {e}")
        return []


def mlb_get_batter_gamelog(player_id: int | str, season: str = CURRENT_YEAR,
                            last_n: int = 15) -> list[dict]:
    """Recent game-by-game hitting stats for an MLB batter."""
    url = f"{MLB_BASE}/people/{player_id}/stats"
    params = {
        "stats":  "gameLog",
        "group":  "hitting",
        "season": season,
    }
    try:
        r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        splits = data.get("stats", [{}])[0].get("splits", [])
        splits = splits[-last_n:]   # most recent last_n
        splits.reverse()             # newest first
        games = []
        for s in splits:
            stat = s.get("stat", {})
            opp  = s.get("opponent", {}).get("abbreviation", "?")
            games.append({
                "date":     s.get("date", ""),
                "opponent": opp,
                "home":     s.get("isHome", True),
                "ab":       stat.get("atBats", 0),
                "hits":     stat.get("hits", 0),
                "hr":       stat.get("homeRuns", 0),
                "rbi":      stat.get("rbi", 0),
                "bb":       stat.get("baseOnBalls", 0),
                "k":        stat.get("strikeOuts", 0),
                "tb":       stat.get("totalBases", 0),
                "avg":      stat.get("avg", ".000"),
                "obp":      stat.get("obp", ".000"),
                "slg":      stat.get("slg", ".000"),
            })
        return games
    except Exception as e:
        print(f"[MLB batter gamelog {player_id}] {e}")
        return []


def mlb_get_pitcher_gamelog(player_id: int | str, season: str = CURRENT_YEAR,
                             last_n: int = 10) -> list[dict]:
    """Recent game-by-game pitching stats."""
    url = f"{MLB_BASE}/people/{player_id}/stats"
    params = {"stats": "gameLog", "group": "pitching", "season": season}
    try:
        r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data   = r.json()
        splits = data.get("stats", [{}])[0].get("splits", [])
        splits = splits[-last_n:]
        splits.reverse()
        games = []
        for s in splits:
            stat = s.get("stat", {})
            opp  = s.get("opponent", {}).get("abbreviation", "?")
            games.append({
                "date":     s.get("date", ""),
                "opponent": opp,
                "ip":       stat.get("inningsPitched", "0.0"),
                "k":        stat.get("strikeOuts", 0),
                "bb":       stat.get("baseOnBalls", 0),
                "er":       stat.get("earnedRuns", 0),
                "h":        stat.get("hits", 0),
                "result":   stat.get("note", ""),
            })
        return games
    except Exception as e:
        print(f"[MLB pitcher gamelog {player_id}] {e}")
        return []


def mlb_get_team_id(team_abbr: str) -> int | None:
    """Map team abbreviation to MLB team ID."""
    MLB_TEAM_IDS = {
        "ARI": 109, "ATL": 144, "BAL": 110, "BOS": 111, "CHC": 112,
        "CHW": 145, "CIN": 113, "CLE": 114, "COL": 115, "DET": 116,
        "HOU": 117, "KC":  118, "LAA": 108, "LAD": 119, "MIA": 146,
        "MIL": 158, "MIN": 142, "NYM": 121, "NYY": 147, "OAK": 133,
        "PHI": 143, "PIT": 134, "SD":  135, "SEA": 136, "SF":  137,
        "STL": 138, "TB":  139, "TEX": 140, "TOR": 141, "WSH": 120,
    }
    return MLB_TEAM_IDS.get(team_abbr.upper())


# ─────────────────────────────────────────────────────────────
# NHL
# ─────────────────────────────────────────────────────────────

def nhl_headshot_url(player_id: int | str) -> str:
    return f"https://assets.nhle.com/mugs/nhl/20252026/{player_id}.png"


def nhl_get_roster(team_abbr: str) -> list[dict]:
    """Get current NHL roster via new NHL API."""
    url = f"{NHL_BASE}/roster/{team_abbr}/current"
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data    = r.json()
        players = []
        for group in ["forwards", "defensemen", "goalies"]:
            for p in data.get(group, []):
                pid  = p.get("id")
                fname = p.get("firstName", {}).get("default", "")
                lname = p.get("lastName", {}).get("default", "")
                players.append({
                    "external_id":   str(pid),
                    "name":          f"{fname} {lname}".strip(),
                    "position":      p.get("positionCode", ""),
                    "jersey_number": str(p.get("sweaterNumber", "")),
                    "sport":         "NHL",
                    "headshot_url":  p.get("headshot", nhl_headshot_url(pid)),
                    "team":          team_abbr,
                })
        return players
    except Exception as e:
        print(f"[NHL roster {team_abbr}] {e}")
        return []


def nhl_get_player_gamelog(player_id: int | str, season: str = "20252026",
                            last_n: int = 10) -> list[dict]:
    """Recent NHL player game logs."""
    url = f"{NHL_BASE}/player/{player_id}/game-log/{season}/2"
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data  = r.json()
        games = data.get("gameLog", [])[:last_n]
        result = []
        for g in games:
            result.append({
                "date":     g.get("gameDate", ""),
                "opponent": g.get("opponentAbbrev", "?"),
                "home":     g.get("homeRoadFlag", "H") == "H",
                "goals":    g.get("goals", 0),
                "assists":  g.get("assists", 0),
                "points":   g.get("points", 0),
                "shots":    g.get("shots", 0),
                "toi":      g.get("toi", "0:00"),
                "hits":     g.get("hits", 0),
                "pims":     g.get("pim", 0),
                "result":   "W" if g.get("teamScore", 0) > g.get("opponentScore", 0) else "L",
            })
        return result
    except Exception as e:
        print(f"[NHL gamelog {player_id}] {e}")
        return []


def nhl_get_skater_stats(player_id: int | str, season: str = "20252026") -> dict:
    """Season stats for an NHL skater."""
    url = f"{NHL_BASE}/player/{player_id}/landing"
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data  = r.json()
        # Find the current season stats
        feat  = data.get("featuredStats", {})
        reg   = feat.get("regularSeason", {}).get("subSeason", {})
        return {
            "games":   reg.get("gamesPlayed", 0),
            "goals":   reg.get("goals", 0),
            "assists": reg.get("assists", 0),
            "points":  reg.get("points", 0),
            "shots":   reg.get("shots", 0),
            "plusminus": reg.get("plusMinus", 0),
        }
    except Exception as e:
        print(f"[NHL stats {player_id}] {e}")
        return {}


# ─────────────────────────────────────────────────────────────
# PROP LINE GENERATOR  (synthetic, based on recent stats)
# ─────────────────────────────────────────────────────────────

def compute_prop_line(values: list[float], n_recent: int = 5) -> float:
    """
    Generate a realistic betting prop line from recent stats.
    Method: weighted average of last n_recent games, rounded to nearest 0.5.
    Uses same recency weighting as Clutchwrap Supreme model.
    """
    if not values:
        return 0.5
    v = [float(x) for x in values[:n_recent]]
    weights = [5, 4, 3, 2, 1][:len(v)]
    weighted = sum(x*w for x,w in zip(v, weights)) / sum(weights[:len(v)])
    # Round to nearest 0.5
    return max(0.5, round(weighted * 2) / 2)


def hit_rate(values: list[float], line: float) -> dict:
    """
    Calculate over/under hit rate for a prop line.
    Returns: over_pct, under_pct, push_pct, streak (current over/under run)
    """
    if not values:
        return {"over": 0.0, "under": 0.0, "push": 0.0, "streak": 0, "streak_dir": ""}
    overs  = sum(1 for v in values if v > line)
    unders = sum(1 for v in values if v < line)
    pushes = sum(1 for v in values if v == line)
    total  = len(values)

    # Current streak
    streak, streak_dir = 0, ""
    for v in values:
        cur = "O" if v > line else ("U" if v < line else "P")
        if streak == 0:
            streak_dir = cur
            streak = 1
        elif cur == streak_dir:
            streak += 1
        else:
            break

    return {
        "over":       round(overs  / total * 100, 1),
        "under":      round(unders / total * 100, 1),
        "push":       round(pushes / total * 100, 1),
        "streak":     streak,
        "streak_dir": streak_dir,
        "sample":     total,
    }


def matchup_history(game_logs: list[dict], opponent: str,
                    stat_key: str = "points") -> dict:
    """
    Filter game logs for games vs a specific opponent.
    Returns avg and last 5 values vs that opponent.
    """
    opp_games = [g for g in game_logs if opponent.upper() in g.get("opponent","").upper()]
    if not opp_games:
        return {"avg": None, "games": [], "n": 0}
    values = [g.get(stat_key, 0) for g in opp_games[:5]]
    return {
        "avg":   round(sum(values) / len(values), 1),
        "games": opp_games[:5],
        "n":     len(opp_games),
    }


# ─────────────────────────────────────────────────────────────
# TEAM ABBR LOOKUPS
# ─────────────────────────────────────────────────────────────
NBA_TEAM_IDS = {
    "ATL": 1610612737, "BOS": 1610612738, "BKN": 1610612751,
    "CHA": 1610612766, "CHI": 1610612741, "CLE": 1610612739,
    "DAL": 1610612742, "DEN": 1610612743, "DET": 1610612765,
    "GSW": 1610612744, "HOU": 1610612745, "IND": 1610612754,
    "LAC": 1610612746, "LAL": 1610612747, "MEM": 1610612763,
    "MIA": 1610612748, "MIL": 1610612749, "MIN": 1610612750,
    "NOP": 1610612740, "NYK": 1610612752, "OKC": 1610612760,
    "ORL": 1610612753, "PHI": 1610612755, "PHX": 1610612756,
    "POR": 1610612757, "SAC": 1610612758, "SAS": 1610612759,
    "TOR": 1610612761, "UTA": 1610612762, "WAS": 1610612764,
}

# Map full team names from Supabase games table → NBA abbreviation
NBA_FULL_TO_ABBR = {
    "New York Knicks": "NYK", "San Antonio Spurs": "SAS",
    "Boston Celtics": "BOS", "Miami Heat": "MIA",
    "Los Angeles Lakers": "LAL", "Golden State Warriors": "GSW",
    "Denver Nuggets": "DEN", "Oklahoma City Thunder": "OKC",
    "Minnesota Timberwolves": "MIN", "Cleveland Cavaliers": "CLE",
    "Philadelphia 76ers": "PHI", "Milwaukee Bucks": "MIL",
    "Chicago Bulls": "CHI", "Indiana Pacers": "IND",
    "Atlanta Hawks": "ATL", "Charlotte Hornets": "CHA",
    "Orlando Magic": "ORL", "Washington Wizards": "WAS",
    "Toronto Raptors": "TOR", "Brooklyn Nets": "BKN",
    "Detroit Pistons": "DET", "New Orleans Pelicans": "NOP",
    "Memphis Grizzlies": "MEM", "Dallas Mavericks": "DAL",
    "Houston Rockets": "HOU", "Utah Jazz": "UTA",
    "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC",
    "Los Angeles Clippers": "LAC", "Phoenix Suns": "PHX",
}

NHL_FULL_TO_ABBR = {
    "Carolina Hurricanes": "CAR", "Vegas Golden Knights": "VGK",
    "Boston Bruins": "BOS", "Florida Panthers": "FLA",
    "Colorado Avalanche": "COL", "Dallas Stars": "DAL",
    "Tampa Bay Lightning": "TBL", "New York Rangers": "NYR",
    "Edmonton Oilers": "EDM", "Toronto Maple Leafs": "TOR",
    "Pittsburgh Penguins": "PIT", "New Jersey Devils": "NJD",
    "New York Islanders": "NYI", "Philadelphia Flyers": "PHI",
    "Washington Capitals": "WSH", "Columbus Blue Jackets": "CBJ",
    "Detroit Red Wings": "DET", "Chicago Blackhawks": "CHI",
    "Nashville Predators": "NSH", "St. Louis Blues": "STL",
    "Winnipeg Jets": "WPG", "Minnesota Wild": "MIN",
    "Arizona Coyotes": "ARI", "Anaheim Ducks": "ANA",
    "Los Angeles Kings": "LAK", "San Jose Sharks": "SJS",
    "Seattle Kraken": "SEA", "Calgary Flames": "CGY",
    "Edmonton Oilers": "EDM", "Vancouver Canucks": "VAN",
    "Ottawa Senators": "OTT", "Montreal Canadiens": "MTL",
    "Buffalo Sabres": "BUF",
}
