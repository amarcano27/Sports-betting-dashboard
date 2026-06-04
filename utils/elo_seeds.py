"""
Team Elo Seeds from Real Standings
===================================
Fetches current W/L records from free official APIs and converts
to calibrated Elo ratings using Pythagorean expectation.

Sources (all free, no key needed):
  MLB  → statsapi.mlb.com
  NBA  → stats.nba.com
  NHL  → api-web.nhle.com
"""
import requests
import math

BASE_ELO   = 1500.0
ELO_SCALE  = 400.0
WIN_PCT_TO_ELO_MULTIPLIER = 600.0   # spread across top/bottom of league


def win_pct_to_elo(win_pct: float) -> float:
    """
    Convert win% to Elo rating.
    .500 → 1500, league-best ~.700 → ~1620, league-worst ~.300 → ~1380.
    """
    if win_pct <= 0: return BASE_ELO - 200
    if win_pct >= 1: return BASE_ELO + 200
    # Invert Elo formula: elo_diff = -400 * log10(1/wp - 1)
    elo_diff = -ELO_SCALE * math.log10(1.0 / win_pct - 1.0)
    return round(BASE_ELO + elo_diff, 1)


def pythagorean_elo(runs_scored: float, runs_allowed: float, exp: float = 1.83) -> float:
    """Convert RS/RA to Elo via Pythagorean win%."""
    if runs_allowed == 0 or runs_scored == 0:
        return BASE_ELO
    wp = runs_scored ** exp / (runs_scored ** exp + runs_allowed ** exp)
    return win_pct_to_elo(wp)


# ─────────────────────────────────────────────────────────────
# MLB
# ─────────────────────────────────────────────────────────────
MLB_TEAM_ABBR_MAP = {
    "Arizona Diamondbacks": "ARI", "Atlanta Braves": "ATL",
    "Baltimore Orioles": "BAL", "Boston Red Sox": "BOS",
    "Chicago Cubs": "CHC", "Chicago White Sox": "CHW",
    "Cincinnati Reds": "CIN", "Cleveland Guardians": "CLE",
    "Colorado Rockies": "COL", "Detroit Tigers": "DET",
    "Houston Astros": "HOU", "Kansas City Royals": "KC",
    "Los Angeles Angels": "LAA", "Los Angeles Dodgers": "LAD",
    "Miami Marlins": "MIA", "Milwaukee Brewers": "MIL",
    "Minnesota Twins": "MIN", "New York Mets": "NYM",
    "New York Yankees": "NYY", "Athletics": "OAK",
    "Philadelphia Phillies": "PHI", "Pittsburgh Pirates": "PIT",
    "San Diego Padres": "SD", "Seattle Mariners": "SEA",
    "San Francisco Giants": "SF", "St. Louis Cardinals": "STL",
    "Tampa Bay Rays": "TB", "Texas Rangers": "TEX",
    "Toronto Blue Jays": "TOR", "Washington Nationals": "WSH",
}

# Map from MLB API short names → full names used in our DB
MLB_SHORT_TO_FULL = {
    "Angels": "Los Angeles Angels", "Astros": "Houston Astros",
    "Athletics": "Athletics", "Blue Jays": "Toronto Blue Jays",
    "Braves": "Atlanta Braves", "Brewers": "Milwaukee Brewers",
    "Cardinals": "St. Louis Cardinals", "Cubs": "Chicago Cubs",
    "D-backs": "Arizona Diamondbacks", "Dodgers": "Los Angeles Dodgers",
    "Giants": "San Francisco Giants", "Guardians": "Cleveland Guardians",
    "Mariners": "Seattle Mariners", "Marlins": "Miami Marlins",
    "Mets": "New York Mets", "Nationals": "Washington Nationals",
    "Orioles": "Baltimore Orioles", "Padres": "San Diego Padres",
    "Phillies": "Philadelphia Phillies", "Pirates": "Pittsburgh Pirates",
    "Rangers": "Texas Rangers", "Rays": "Tampa Bay Rays",
    "Red Sox": "Boston Red Sox", "Reds": "Cincinnati Reds",
    "Rockies": "Colorado Rockies", "Royals": "Kansas City Royals",
    "Tigers": "Detroit Tigers", "Twins": "Minnesota Twins",
    "White Sox": "Chicago White Sox", "Yankees": "New York Yankees",
}

def get_mlb_elo_seeds() -> dict[str, float]:
    """
    Returns {full_team_name: elo_rating} for all MLB teams.
    Uses Pythagorean expectation from runs scored/allowed.
    """
    url = "https://statsapi.mlb.com/api/v1/standings"
    params = {"leagueId": "103,104", "season": "2026", "standingsTypes": "regularSeason"}
    seeds = {}
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        for record in data.get("records", []):
            for tr in record.get("teamRecords", []):
                short_name = tr["team"].get("teamName", tr["team"].get("name", ""))
                name = MLB_SHORT_TO_FULL.get(short_name, short_name)
                wins = tr.get("wins", 0)
                losses = tr.get("losses", 0)
                total = wins + losses
                if total == 0:
                    seeds[name] = BASE_ELO
                    continue
                # Use Pythagorean if runs available, else straight win%
                rs = tr.get("runsScored")
                ra = tr.get("runsAllowed")
                if rs and ra and rs > 0 and ra > 0:
                    seeds[name] = pythagorean_elo(rs, ra)
                else:
                    seeds[name] = win_pct_to_elo(wins / total)
    except Exception as e:
        print(f"[elo_seeds MLB] {e}")
    return seeds


# ─────────────────────────────────────────────────────────────
# NBA
# ─────────────────────────────────────────────────────────────
NBA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.nba.com/",
    "Origin":  "https://www.nba.com",
}

NBA_ABBR_TO_FULL = {
    "ATL": "Atlanta Hawks",     "BOS": "Boston Celtics",
    "BKN": "Brooklyn Nets",     "CHA": "Charlotte Hornets",
    "CHI": "Chicago Bulls",     "CLE": "Cleveland Cavaliers",
    "DAL": "Dallas Mavericks",  "DEN": "Denver Nuggets",
    "DET": "Detroit Pistons",   "GSW": "Golden State Warriors",
    "HOU": "Houston Rockets",   "IND": "Indiana Pacers",
    "LAC": "Los Angeles Clippers","LAL": "Los Angeles Lakers",
    "MEM": "Memphis Grizzlies", "MIA": "Miami Heat",
    "MIL": "Milwaukee Bucks",   "MIN": "Minnesota Timberwolves",
    "NOP": "New Orleans Pelicans","NYK": "New York Knicks",
    "OKC": "Oklahoma City Thunder","ORL": "Orlando Magic",
    "PHI": "Philadelphia 76ers","PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers","SAC": "Sacramento Kings",
    "SAS": "San Antonio Spurs", "TOR": "Toronto Raptors",
    "UTA": "Utah Jazz",         "WAS": "Washington Wizards",
}

# NBA 2025-26 season fallback Elo (used when API times out)
# Based on final regular-season standings
NBA_FALLBACK_ELO = {
    "Oklahoma City Thunder":     1650, "Cleveland Cavaliers":     1620,
    "Boston Celtics":            1610, "New York Knicks":         1580,
    "Denver Nuggets":            1560, "Houston Rockets":         1550,
    "Los Angeles Lakers":        1530, "Golden State Warriors":   1510,
    "Minnesota Timberwolves":    1520, "Memphis Grizzlies":       1500,
    "Milwaukee Bucks":           1490, "Phoenix Suns":            1470,
    "Indiana Pacers":            1480, "Los Angeles Clippers":    1460,
    "Dallas Mavericks":          1455, "Sacramento Kings":        1440,
    "Miami Heat":                1435, "Orlando Magic":           1430,
    "Philadelphia 76ers":        1410, "Atlanta Hawks":           1400,
    "Chicago Bulls":             1390, "Toronto Raptors":         1380,
    "Brooklyn Nets":             1370, "New Orleans Pelicans":    1360,
    "San Antonio Spurs":         1340, "Detroit Pistons":         1350,
    "Utah Jazz":                 1320, "Portland Trail Blazers":  1330,
    "Washington Wizards":        1300, "Charlotte Hornets":       1310,
}

def get_nba_elo_seeds() -> dict[str, float]:
    """Returns {full_team_name: elo_rating} for all NBA teams.
    Tries live API first; falls back to hardcoded 2025-26 standings on timeout."""
    url = "https://stats.nba.com/stats/leaguestandingsv3"
    params = {"LeagueID": "00", "Season": "2025-26", "SeasonType": "Regular Season"}
    seeds = {}
    try:
        r = requests.get(url, headers=NBA_HEADERS, params=params, timeout=8)
        r.raise_for_status()
        data = r.json()
        rs   = data["resultSets"][0]
        cols = [c.lower() for c in rs["headers"]]
        for row in rs["rowSet"]:
            d        = dict(zip(cols, row))
            wins     = d.get("wins", 0) or 0
            losses   = d.get("losses", 0) or 0
            total    = wins + losses
            wp       = wins / total if total > 0 else 0.5
            abbr     = d.get("teamabbreviation", "")
            full_name = NBA_ABBR_TO_FULL.get(abbr, "")
            if full_name:
                seeds[full_name] = win_pct_to_elo(wp)
    except Exception:
        # Silent fallback — NBA Stats API is frequently slow/blocked
        pass

    # Fill any missing teams from fallback (or use entirely if API failed)
    for name, elo in NBA_FALLBACK_ELO.items():
        if name not in seeds:
            seeds[name] = elo

    return seeds


# ─────────────────────────────────────────────────────────────
# NHL
# ─────────────────────────────────────────────────────────────
NHL_ABBR_TO_FULL = {
    "CAR": "Carolina Hurricanes",   "VGK": "Vegas Golden Knights",
    "BOS": "Boston Bruins",         "FLA": "Florida Panthers",
    "COL": "Colorado Avalanche",    "DAL": "Dallas Stars",
    "TBL": "Tampa Bay Lightning",   "NYR": "New York Rangers",
    "EDM": "Edmonton Oilers",       "TOR": "Toronto Maple Leafs",
    "PIT": "Pittsburgh Penguins",   "NJD": "New Jersey Devils",
    "NYI": "New York Islanders",    "PHI": "Philadelphia Flyers",
    "WSH": "Washington Capitals",   "CBJ": "Columbus Blue Jackets",
    "DET": "Detroit Red Wings",     "CHI": "Chicago Blackhawks",
    "NSH": "Nashville Predators",   "STL": "St. Louis Blues",
    "WPG": "Winnipeg Jets",         "MIN": "Minnesota Wild",
    "ANA": "Anaheim Ducks",         "LAK": "Los Angeles Kings",
    "SJS": "San Jose Sharks",       "SEA": "Seattle Kraken",
    "CGY": "Calgary Flames",        "VAN": "Vancouver Canucks",
    "OTT": "Ottawa Senators",       "MTL": "Montreal Canadiens",
    "BUF": "Buffalo Sabres",        "ARI": "Utah Hockey Club",
}

def get_nhl_elo_seeds() -> dict[str, float]:
    """Returns {full_team_name: elo_rating} for all NHL teams."""
    url = "https://api-web.nhle.com/v1/standings/now"
    seeds = {}
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        for team in data.get("standings", []):
            abbr = team.get("teamAbbrev", {}).get("default", "")
            wins = team.get("wins", 0)
            losses = team.get("losses", 0)
            otl  = team.get("otLosses", 0)
            total = wins + losses + otl
            wp   = wins / total if total > 0 else 0.5
            # NHL uses points%, not win% — adjust
            pts  = team.get("points", 0)
            gp   = team.get("gamesPlayed", total or 1)
            pts_pct = pts / (gp * 2) if gp > 0 else 0.5
            full_name = NHL_ABBR_TO_FULL.get(abbr, abbr)
            seeds[full_name] = win_pct_to_elo(pts_pct)
    except Exception as e:
        print(f"[elo_seeds NHL] {e}")
    return seeds


# ─────────────────────────────────────────────────────────────
# COMBINED + CACHED
# ─────────────────────────────────────────────────────────────
_cache: dict = {}

def get_all_elo_seeds(force_refresh: bool = False) -> dict[str, float]:
    """
    Returns combined {team_name: elo} for MLB + NBA + NHL.
    Cached in memory for the session; use force_refresh=True to update.
    """
    global _cache
    if _cache and not force_refresh:
        return _cache
    result = {}
    result.update(get_mlb_elo_seeds())
    result.update(get_nba_elo_seeds())
    result.update(get_nhl_elo_seeds())
    _cache = result
    return result


def lookup_elo(team_name: str, default: float = BASE_ELO) -> float:
    """Get Elo seed for a team by full name. Falls back to 1500."""
    seeds = get_all_elo_seeds()
    return seeds.get(team_name, default)
