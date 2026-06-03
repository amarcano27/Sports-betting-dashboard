"""
APEX ANALYTICS - MLB Model
Elo + FIP probabilistic model.
"""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
from datetime import datetime
import requests

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from utils.model import build_game_model, devig, american_to_prob
from dashboard.ui_components import render_game_card

# ─────────────────────────────────────────────────────────────
# DYNAMIC PITCHER FETCHING
# ─────────────────────────────────────────────────────────────
TEAM_ABBR = {
    "Detroit Tigers": "DET", "Tampa Bay Rays": "TB",
    "San Diego Padres": "SD", "Philadelphia Phillies": "PHI",
    "Miami Marlins": "MIA", "Washington Nationals": "WSH",
    "Baltimore Orioles": "BAL", "Boston Red Sox": "BOS",
    "Cleveland Guardians": "CLE", "New York Yankees": "NYY",
    "Kansas City Royals": "KC", "Cincinnati Reds": "CIN",
    "Toronto Blue Jays": "TOR", "Atlanta Braves": "ATL",
    "Chicago White Sox": "CHW", "Minnesota Twins": "MIN",
    "San Francisco Giants": "SF", "Milwaukee Brewers": "MIL",
    "Texas Rangers": "TEX", "St. Louis Cardinals": "STL",
    "Athletics": "OAK", "Chicago Cubs": "CHC",
    "Pittsburgh Pirates": "PIT", "Houston Astros": "HOU",
    "Colorado Rockies": "COL", "Los Angeles Angels": "LAA",
    "Los Angeles Dodgers": "LAD", "Arizona Diamondbacks": "ARI",
    "New York Mets": "NYM", "Seattle Mariners": "SEA",
}

MLB_TEAM_IDS = {
    "ARI": 109, "ATL": 144, "BAL": 110, "BOS": 111, "CHC": 112,
    "CHW": 145, "CIN": 113, "CLE": 114, "COL": 115, "DET": 116,
    "HOU": 117, "KC":  118, "LAA": 108, "LAD": 119, "MIA": 146,
    "MIL": 158, "MIN": 142, "NYM": 121, "NYY": 147, "OAK": 133,
    "PHI": 143, "PIT": 134, "SD":  135, "SEA": 136, "SF":  137,
    "STL": 138, "TB":  139, "TEX": 140, "TOR": 141, "WSH": 120,
}

@st.cache_data(ttl=3600)
def get_probable_pitchers(date_str: str) -> dict:
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_str}&hydrate=probablePitcher"
    pitchers = {}
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if not data.get("dates"): return pitchers
        for game in data["dates"][0].get("games", []):
            for side in ["away", "home"]:
                team_id = game["teams"][side]["team"]["id"]
                prob = game["teams"][side].get("probablePitcher")
                if prob:
                    pitchers[team_id] = {"id": prob["id"], "name": prob["fullName"]}
    except: pass
    return pitchers

@st.cache_data(ttl=3600)
def get_pitcher_stats(player_id: int, season: str = "2024") -> dict:
    url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=season&group=pitching&season={season}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if not data.get("stats"): return None
        stat = data["stats"][0]["splits"][0]["stat"]
        
        hr = stat.get("homeRuns", 0)
        bb = stat.get("baseOnBalls", 0)
        hbp = stat.get("hitBatsmen", 0)
        k = stat.get("strikeOuts", 0)
        ip_str = str(stat.get("inningsPitched", "0"))
        
        if "." in ip_str:
            full, part = ip_str.split(".")
            ip = int(full) + (int(part) / 3.0)
        else:
            ip = float(ip_str)
            
        fip = ((13 * hr + 3 * (bb + hbp) - 2 * k) / ip) + 3.15 if ip > 0 else 4.20
            
        return {
            "fip": round(fip, 2),
            "era": float(stat.get("era", 4.20)),
            "xera": float(stat.get("era", 4.20)),
            "k9": float(stat.get("strikeoutsPer9Inn", 8.0))
        }
    except: return None

def find_pitcher(team_name: str) -> tuple[str | None, dict | None]:
    abbr = TEAM_ABBR.get(team_name)
    if not abbr: return None, None
    team_id = MLB_TEAM_IDS.get(abbr)
    if not team_id: return None, None
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    pitchers = get_probable_pitchers(today_str)
    if not pitchers: pitchers = get_probable_pitchers("2024-06-03")
        
    p_info = pitchers.get(team_id)
    if not p_info: return None, None
        
    stats = get_pitcher_stats(p_info["id"])
    if not stats: stats = {"fip": 4.20, "era": 4.20, "xera": 4.20, "k9": 8.0}
    stats["team"] = abbr
    return p_info["name"], stats

# ─────────────────────────────────────────────────────────────
# DATA LOADERS
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def load_mlb_games():
    return supabase.table("games").select("*").eq("sport","MLB").order("start_time").execute().data or []

@st.cache_data(ttl=120)
def load_game_odds(game_id: str):
    return supabase.table("odds_snapshots").select("*").eq("game_id", game_id).execute().data or []

def best_price(rows, market, label):
    m = [r for r in rows if r.get("market_type") == market and r.get("market_label") == label]
    if not m: return None, None
    b = max(m, key=lambda r: r.get("price") or -9999)
    return int(b["price"]), b.get("book","?")

# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
st.title("⚾ MLB Model")
st.caption("Elo + FIP Probabilistic Engine")

games = load_mlb_games()
if not games:
    st.warning("No MLB games found in database.")
    st.stop()

# Layout in a grid
cols = st.columns(2)

for idx, g in enumerate(games):
    away, home = g["away_team"], g["home_team"]
    try:
        t = datetime.fromisoformat(g["start_time"].replace("Z","+00:00"))
        time_str = t.strftime("%I:%M %p ET")
    except:
        time_str = "TBD"

    rows = load_game_odds(g["id"])
    away_ml, _ = best_price(rows, "h2h", away)
    home_ml, _ = best_price(rows, "h2h", home)

    if not away_ml or not home_ml:
        continue

    away_pn, away_pd = find_pitcher(away)
    home_pn, home_pd = find_pitcher(home)

    dv_a, dv_h = devig(away_ml, home_ml)

    if away_pd and home_pd:
        gm = build_game_model(away, home, away_pd["fip"], home_pd["fip"], away_ml, home_ml)
        best_e = max(gm.away_edge, gm.home_edge)
        rec = gm.away_rec if gm.away_edge >= gm.home_edge else gm.home_rec
        model_p = gm.model_away_prob if gm.away_edge >= gm.home_edge else gm.model_home_prob
        dv_p = dv_a if gm.away_edge >= gm.home_edge else dv_h
    else:
        if dv_a > dv_h:
            best_e = (dv_a - american_to_prob(away_ml)) * 100
            model_p = dv_a
            dv_p = dv_a
        else:
            best_e = (dv_h - american_to_prob(home_ml)) * 100
            model_p = dv_h
            dv_p = dv_h
        rec = "PLAY" if best_e >= 2 else "LEAN"

    with cols[idx % 2]:
        render_game_card(
            sport="MLB",
            away_team=away,
            home_team=home,
            time_str=time_str,
            away_ml=away_ml,
            home_ml=home_ml,
            edge_pct=best_e,
            recommendation=rec,
            model_prob=model_p,
            market_prob=dv_p
        )
