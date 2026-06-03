"""
MLB Analysis — Elo + FIP probabilistic model.

Model engine: utils/model.py
  - Team Elo ratings (K=6, HFA=55pts) — Birdland/538 methodology
  - FIP-based pitcher adjustment (50 Elo per 1.0 FIP from 4.20 avg)
  - No-vig devigging of market odds (MPTO method)
  - Edge = Model probability − devigged market probability
  - Quarter Kelly bet sizing
  - Poisson K prop probability model
  - Backtested accuracy: 57.33% (Birdland, 3 seasons)
"""
import sys, math, json
from pathlib import Path
import streamlit as st
import pandas as pd
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from utils.model import (
    build_game_model, k_prop_model, devig,
    american_to_prob, prob_to_american, quarter_kelly,
    vig_pct, REC_COLORS, REC_CARD_CLASS,
    LEAGUE_AVG_FIP, MIN_EDGE_PCT,
    PitcherProfile, pythagorean_pct,
)
from dashboard.premium_styles import tier_badge, color


import requests
from datetime import datetime

# ─────────────────────────────────────────────────────────────
# DYNAMIC PITCHER FETCHING (Replaces hardcoded PITCHER_DB)
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
    """Fetch probable pitchers for a given date from MLB API."""
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_str}&hydrate=probablePitcher"
    pitchers = {}
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if not data.get("dates"):
            return pitchers
        
        for game in data["dates"][0].get("games", []):
            for side in ["away", "home"]:
                team_id = game["teams"][side]["team"]["id"]
                prob = game["teams"][side].get("probablePitcher")
                if prob:
                    pitchers[team_id] = {
                        "id": prob["id"],
                        "name": prob["fullName"]
                    }
    except Exception as e:
        print(f"Error fetching probable pitchers: {e}")
    return pitchers

@st.cache_data(ttl=3600)
def get_pitcher_stats(player_id: int, season: str = "2024") -> dict:
    """Fetch pitcher season stats and calculate FIP."""
    url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=season&group=pitching&season={season}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if not data.get("stats"):
            return None
        
        stat = data["stats"][0]["splits"][0]["stat"]
        
        # Calculate FIP
        # FIP = ((13*HR + 3*(BB+HBP) - 2*K) / IP) + constant (usually ~3.15)
        hr = stat.get("homeRuns", 0)
        bb = stat.get("baseOnBalls", 0)
        hbp = stat.get("hitBatsmen", 0)
        k = stat.get("strikeOuts", 0)
        ip_str = str(stat.get("inningsPitched", "0"))
        
        # Convert IP string (e.g. "75.2" = 75 and 2/3 innings) to decimal
        if "." in ip_str:
            full, part = ip_str.split(".")
            ip = int(full) + (int(part) / 3.0)
        else:
            ip = float(ip_str)
            
        if ip > 0:
            fip = ((13 * hr + 3 * (bb + hbp) - 2 * k) / ip) + 3.15
        else:
            fip = 4.20 # League average fallback
            
        return {
            "fip": round(fip, 2),
            "era": float(stat.get("era", 4.20)),
            "xera": float(stat.get("era", 4.20)), # xERA not in basic API, fallback to ERA
            "k9": float(stat.get("strikeoutsPer9Inn", 8.0))
        }
    except Exception as e:
        print(f"Error fetching stats for {player_id}: {e}")
        return None

def find_pitcher(team_name: str) -> tuple[str | None, dict | None]:
    """Dynamically find the probable pitcher and their stats for a team today."""
    abbr = TEAM_ABBR.get(team_name)
    if not abbr:
        return None, None
        
    team_id = MLB_TEAM_IDS.get(abbr)
    if not team_id:
        return None, None
        
    # Use today's date (or a fixed date for testing if needed)
    # Using 2024-06-03 as a fallback since the DB might have games from then
    # In a real app, this would be datetime.now().strftime('%Y-%m-%d')
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    # For the sake of the demo data which is from 2024, let's try 2024 if today fails
    pitchers = get_probable_pitchers(today_str)
    if not pitchers:
        pitchers = get_probable_pitchers("2024-06-03")
        
    pitcher_info = pitchers.get(team_id)
    if not pitcher_info:
        return None, None
        
    stats = get_pitcher_stats(pitcher_info["id"])
    if not stats:
        # Fallback to league average if stats fail
        stats = {"fip": 4.20, "era": 4.20, "xera": 4.20, "k9": 8.0}
        
    stats["team"] = abbr
    return pitcher_info["name"], stats


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

def all_book_prices(rows, market, label):
    m = [r for r in rows if r.get("market_type") == market and r.get("market_label") == label]
    return sorted(m, key=lambda r: r.get("price") or -9999, reverse=True)


# ─────────────────────────────────────────────────────────────
# GAME CARD
# ─────────────────────────────────────────────────────────────
def render_game_card(game: dict, odds_rows: list, idx: int):
    away, home = game["away_team"], game["home_team"]

    try:
        t = datetime.fromisoformat(game["start_time"].replace("Z","+00:00"))
        time_str = t.strftime("%I:%M %p ET")
    except Exception:
        time_str = "TBD"

    away_pn, away_pd = find_pitcher(away)
    home_pn, home_pd = find_pitcher(home)

    away_ml, away_book = best_price(odds_rows, "h2h", away)
    home_ml, home_book = best_price(odds_rows, "h2h", home)
    over_p,  _        = best_price(odds_rows, "totals", "Over")
    under_p, _        = best_price(odds_rows, "totals", "Under")
    total_rows        = [r for r in odds_rows if r.get("market_type")=="totals" and r.get("market_label")=="Over"]
    total_line        = max(total_rows, key=lambda r: r.get("price") or -9999).get("line") if total_rows else None

    # ── RUN MODEL ────────────────────────────────────────────
    if away_pd and home_pd:
        gm = build_game_model(
            away_team=away, home_team=home,
            away_fip=away_pd["fip"], home_fip=home_pd["fip"],
            away_odds=away_ml, home_odds=home_ml,
            away_pitcher_name=away_pn, home_pitcher_name=home_pn,
            away_k9=away_pd.get("k9"), home_k9=home_pd.get("k9"),
            away_xera=away_pd.get("xera"), home_xera=home_pd.get("xera"),
        )
        has_model = True
    else:
        gm = None
        has_model = False

    # ── DETERMINE CARD STYLE ─────────────────────────────────
    if has_model:
        best_edge = gm.best_edge
        best_play = gm.best_play
        if gm.home_edge >= gm.away_edge:
            rec_label = gm.home_rec
            rec_ml    = home_ml
            rec_team  = home
            rec_edge  = gm.home_edge
            rec_kelly = gm.home_kelly
            rec_model_prob = gm.model_home_prob
            rec_devig_prob = gm.devig_home_prob
        else:
            rec_label = gm.away_rec
            rec_ml    = away_ml
            rec_team  = away
            rec_edge  = gm.away_edge
            rec_kelly = gm.away_kelly
            rec_model_prob = gm.model_away_prob
            rec_devig_prob = gm.devig_away_prob
    else:
        rec_label = "INCOMPLETE"
        rec_ml    = None
        rec_team  = "—"
        rec_edge  = 0.0
        rec_kelly = 0.0
        rec_model_prob = 0.5
        rec_devig_prob = 0.5
        best_play = "—"
        best_edge = 0.0

    card_class = REC_CARD_CLASS.get(rec_label, "play-card")
    rec_color  = REC_COLORS.get(rec_label, color("text_primary"))

    ml_str = (f"+{rec_ml}" if rec_ml and rec_ml > 0 else str(rec_ml)) if rec_ml else "—"

    # ── BUILD REASONING STRING ───────────────────────────────
    if has_model:
        ap = gm.away_pitcher
        hp = gm.home_pitcher
        vig = vig_pct(away_ml, home_ml) if away_ml and home_ml else None
        vig_str = f" · Market vig: {vig:.1f}%" if vig else ""
        if rec_label in ("BEST VALUE", "STRONG", "PLAY"):
            reason = (
                f"{away_pn} (FIP {ap.best_fip:.2f}, {ap.tier.split(' — ')[0]}) vs "
                f"{home_pn} (FIP {hp.best_fip:.2f}, {hp.tier.split(' — ')[0]}). "
                f"Model: {rec_team.split()[-1]} {rec_model_prob*100:.1f}% vs devigged market {rec_devig_prob*100:.1f}%. "
                f"Edge: +{rec_edge:.1f}%{vig_str}"
            )
        elif rec_label == "LEAN":
            reason = (
                f"Marginal edge ({rec_edge:+.1f}%). "
                f"Model {rec_team.split()[-1]} {rec_model_prob*100:.1f}% vs market {rec_devig_prob*100:.1f}%.{vig_str}"
            )
        elif rec_label == "PARLAY ONLY":
            reason = f"{rec_ml} is too heavy to lay straight — use as parlay/SGP leg only."
        elif rec_label == "SKIP":
            reason = (
                f"Negative edge ({rec_edge:+.1f}%). "
                f"Market price implies more than our model supports. Pass on both sides."
            )
        else:
            reason = "Both starters AVOID tier or insufficient data."
    else:
        reason = "One or both starters not found. Pitcher stats could not be fetched from MLB API."

    # ── CARD HEADER ───────────────────────────────────────────
    st.markdown(f"""
<div class="{card_class}">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;
              border-bottom:1px solid {color('border')};padding-bottom:12px;margin-bottom:14px">
    <div>
      <div style="font-size:11px;color:{color('text_muted')};font-weight:700;
                  text-transform:uppercase;letter-spacing:0.07em">
        GAME {idx} · {time_str}
      </div>
      <div style="font-size:20px;font-weight:700;color:{color('text_primary')};margin-top:4px">
        {away} @ {home}
      </div>
    </div>
    <div style="text-align:right">
      <div style="display:inline-block;background:{rec_color};color:#0d1117;
                  padding:4px 12px;border-radius:4px;font-size:12px;font-weight:800;
                  text-transform:uppercase;letter-spacing:0.05em">{rec_label}</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:20px;
                  font-weight:700;color:{rec_color};margin-top:6px">{ml_str}</div>
      <div style="font-size:11px;color:{color('text_muted')}">
        {rec_team.split()[-1]} · Edge {'+' if rec_edge >= 0 else ''}{rec_edge:.1f}%
      </div>
    </div>
  </div>
  <div style="background:{color('bg_panel_2')};padding:10px 14px;border-radius:6px;
              border-left:3px solid {color('blue')};margin-bottom:16px">
    <span style="color:{color('text_secondary')};font-size:13px">{reason}</span>
  </div>
""", unsafe_allow_html=True)

    # ── PITCHER COLUMNS ───────────────────────────────────────
    pc1, pc2 = st.columns(2)
    for col_side, team, pn, pd_raw, ml, book, model_p, devig_p, side_edge, side_kelly, side_rec in [
        (pc1, away, away_pn, away_pd, away_ml, away_book,
         gm.model_away_prob if has_model else None,
         gm.devig_away_prob if has_model else None,
         gm.away_edge if has_model else None,
         gm.away_kelly if has_model else None,
         gm.away_rec if has_model else "—"),
        (pc2, home, home_pn, home_pd, home_ml, home_book,
         gm.model_home_prob if has_model else None,
         gm.devig_home_prob if has_model else None,
         gm.home_edge if has_model else None,
         gm.home_kelly if has_model else None,
         gm.home_rec if has_model else "—"),
    ]:
        with col_side:
            if pd_raw:
                p = PitcherProfile(
                    name=pn or team, team=TEAM_ABBR.get(team,""),
                    fip=pd_raw["fip"], xera=pd_raw.get("xera"),
                    era=pd_raw.get("era"), k9=pd_raw.get("k9")
                )
                fip_adj = p.elo_adjustment
                adj_color = color("green") if fip_adj >= 0 else color("red")
                ml_display = (f"+{ml}" if ml > 0 else str(ml)) if ml else "—"
                ml_clr = color("green") if ml and ml > 0 else color("red") if ml else color("text_muted")
                imp_pct = american_to_prob(ml)*100 if ml else 0

                edge_clr = color("green") if side_edge and side_edge >= 2 else color("amber") if side_edge and side_edge >= 0 else color("red")
                edge_str = f"{side_edge:+.1f}%" if side_edge is not None else "—"
                model_str = f"{model_p*100:.1f}%" if model_p is not None else "—"
                devig_str = f"{devig_p*100:.1f}%" if devig_p is not None else "—"
                kelly_str = f"{side_kelly*100:.1f}%" if side_kelly else "0%"
                rec_clr   = REC_COLORS.get(side_rec, color("text_muted"))

                # xERA > FIP = regression risk
                xera_warn = ""
                if pd_raw.get("xera") and (pd_raw["xera"] - pd_raw["fip"]) > 0.7:
                    xera_warn = f"⚠️ xERA {pd_raw['xera']:.2f} > FIP — regression risk"

                st.markdown(f"""
<div style="background:{color('bg_panel_2')};border-radius:8px;padding:16px">
  <div style="font-size:10px;color:{color('text_muted')};font-weight:700;
              text-transform:uppercase;letter-spacing:0.06em">{team}</div>
  <div style="font-size:15px;font-weight:700;color:{color('text_primary')};margin:5px 0 8px">
    {pn}
  </div>
  <div style="margin-bottom:10px">{tier_badge(p.tier)}</div>
  {"<div style='font-size:11px;color:" + color('amber') + ";margin-bottom:8px'>" + xera_warn + "</div>" if xera_warn else ""}
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;
              padding:10px 0;border-top:1px solid {color('border')}">
    <div>
      <div style="font-size:9px;color:{color('text_muted')};text-transform:uppercase;
                  letter-spacing:0.05em">FIP</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:20px;
                  font-weight:700;color:{color('text_primary')}">{pd_raw['fip']:.2f}</div>
    </div>
    <div>
      <div style="font-size:9px;color:{color('text_muted')};text-transform:uppercase;
                  letter-spacing:0.05em">ERA</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:20px;
                  font-weight:700;color:{color('text_primary')}">{pd_raw.get('era',0):.2f}</div>
    </div>
    <div>
      <div style="font-size:9px;color:{color('text_muted')};text-transform:uppercase;
                  letter-spacing:0.05em">K/9</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:20px;
                  font-weight:700;color:{color('text_primary')}">{pd_raw.get('k9','—')}</div>
    </div>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;
              padding:10px 0;border-top:1px solid {color('border')}">
    <div>
      <div style="font-size:9px;color:{color('text_muted')};text-transform:uppercase">FIP Elo Adj</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:15px;
                  font-weight:700;color:{adj_color}">{'+' if fip_adj >= 0 else ''}{fip_adj:.0f} pts</div>
    </div>
    <div>
      <div style="font-size:9px;color:{color('text_muted')};text-transform:uppercase">ML / Implied</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:15px;
                  font-weight:700;color:{ml_clr}">{ml_display}</div>
      <div style="font-size:10px;color:{color('text_muted')}">{imp_pct:.0f}% implied</div>
    </div>
  </div>
  <div style="background:{color('bg_panel')};border-radius:6px;padding:10px;
              margin-top:8px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px">
    <div>
      <div style="font-size:9px;color:{color('text_muted')};text-transform:uppercase">Model Prob</div>
      <div style="font-family:'JetBrains Mono',monospace;font-weight:700;
                  color:{color('text_primary')}">{model_str}</div>
    </div>
    <div>
      <div style="font-size:9px;color:{color('text_muted')};text-transform:uppercase">Devig Mkt</div>
      <div style="font-family:'JetBrains Mono',monospace;font-weight:700;
                  color:{color('text_muted')}">{devig_str}</div>
    </div>
    <div>
      <div style="font-size:9px;color:{color('text_muted')};text-transform:uppercase">Edge</div>
      <div style="font-family:'JetBrains Mono',monospace;font-weight:700;
                  color:{edge_clr}">{edge_str}</div>
    </div>
  </div>
  <div style="margin-top:8px;display:flex;justify-content:space-between;align-items:center">
    <div style="display:inline-block;background:{rec_clr};color:#0d1117;
                padding:3px 8px;border-radius:4px;font-size:10px;font-weight:700">{side_rec}</div>
    <div style="font-size:11px;color:{color('text_muted')}">
      Kelly: <span style="color:{color('amber')};font-weight:700">{kelly_str}</span> bankroll
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
<div style="background:{color('bg_panel_2')};border-radius:8px;padding:16px;
            border:1px dashed {color('border')};opacity:0.65">
  <div style="font-size:10px;color:{color('text_muted')};font-weight:700;
              text-transform:uppercase">{team}</div>
  <div style="color:{color('text_muted')};font-style:italic;margin-top:8px">
    Starter not in pitcher database
  </div>
  <div style="font-size:11px;color:{color('text_dim')};margin-top:6px">
    Stats fetched dynamically from MLB API.
  </div>
</div>
""", unsafe_allow_html=True)

    # ── INLINE K PROP ESTIMATES ───────────────────────────────
    if away_pd or home_pd:
        kp1, kp2 = st.columns(2)
        for kci, (team, pn, pd_raw) in enumerate([(away, away_pn, away_pd), (home, home_pn, home_pd)]):
            with [kp1, kp2][kci]:
                if pd_raw and pd_raw.get("k9"):
                    k9  = pd_raw["k9"]
                    # Typical book line = 0.5 below expected pace, rounded to .5 increments
                    exp_6ip = k9 * 6 / 9
                    line    = max(0.5, round(exp_6ip - 0.5) + 0.5 if (exp_6ip - 0.5) % 1 != 0.5 else exp_6ip - 0.5)
                    kr      = k_prop_model(k9=k9, innings_expected=6.0, prop_line=line, odds=-110)
                    bg      = color("green_bg") if kr["priority"] in ("BEST VALUE","STRONG") else color("bg_panel_2")
                    brd     = color("green") if kr["priority"] in ("BEST VALUE","STRONG") else color("border")
                    pr_clr  = color("green") if kr["priority"] in ("BEST VALUE","STRONG") else color("amber") if kr["priority"] in ("PLAY","LEAN") else color("red")
                    st.markdown(f"""
<div style="background:{bg};border:1px solid {brd};border-radius:6px;padding:12px;margin-top:10px">
  <div style="font-size:9px;color:{color('text_muted')};font-weight:700;
              text-transform:uppercase;letter-spacing:0.05em">K Prop Est · {pn or team}</div>
  <div style="display:flex;justify-content:space-between;align-items:center;margin-top:6px">
    <div>
      <div style="font-size:14px;font-weight:700;color:{color('text_primary')}">
        O{line} Ks
      </div>
      <div style="font-size:11px;color:{color('text_muted')}">
        Expected: {kr['expected_ks']}/6 IP (K/9={k9})
      </div>
    </div>
    <div style="text-align:right">
      <div style="font-size:11px;font-weight:700;color:{pr_clr}">{kr['priority']}</div>
      <div style="font-size:11px;color:{color('text_muted')}">Edge {kr['edge']:+.1f}%</div>
    </div>
  </div>
  <div style="font-size:11px;color:{color('text_secondary')};margin-top:6px">
    Poisson model: {kr['over_prob']}% over · {kr['signal'][:55]}
  </div>
</div>
""", unsafe_allow_html=True)

    # ── TOTALS ────────────────────────────────────────────────
    if total_line and over_p and under_p:
        ov_c = color("green") if over_p  > 0 else color("text_primary")
        un_c = color("green") if under_p > 0 else color("text_primary")
        st.markdown(f"""
<div style="background:{color('bg_panel_2')};border-radius:6px;padding:10px 14px;
            margin-top:12px;display:flex;gap:28px;align-items:center;flex-wrap:wrap">
  <div style="font-size:11px;color:{color('text_muted')};font-weight:700;
              text-transform:uppercase">Total O/U {total_line}</div>
  <div>
    <span style="color:{color('text_muted')};font-size:11px">OVER </span>
    <span style="font-family:'JetBrains Mono',monospace;font-weight:700;color:{ov_c}">
      {'+' if over_p > 0 else ''}{over_p}
    </span>
  </div>
  <div>
    <span style="color:{color('text_muted')};font-size:11px">UNDER </span>
    <span style="font-family:'JetBrains Mono',monospace;font-weight:700;color:{un_c}">
      {'+' if under_p > 0 else ''}{under_p}
    </span>
  </div>
  {f'<div style="font-size:10px;color:{color(chr(116)+chr(101)+chr(120)+chr(116)+"_muted")}">Vig: {vig_pct(away_ml, home_ml):.1f}%</div>' if away_ml and home_ml else ''}
</div>
""", unsafe_allow_html=True)

    # ── LINE SHOP ─────────────────────────────────────────────
    with st.expander("📊 Full Line Shop — all books + devig"):
        c1, c2 = st.columns(2)
        for ci, (side_team, side_model, side_devig) in enumerate([
            (away, gm.model_away_prob if has_model else None, gm.devig_away_prob if has_model else None),
            (home, gm.model_home_prob if has_model else None, gm.devig_home_prob if has_model else None),
        ]):
            with [c1, c2][ci]:
                rows = all_book_prices(odds_rows, "h2h", side_team)
                if rows:
                    st.caption(f"**{side_team}**")
                    df_data = []
                    for r in rows[:10]:
                        p = r.get("price")
                        if p:
                            df_data.append({
                                "Book":    r.get("book","?").upper(),
                                "ML":      f"+{int(p)}" if p > 0 else f"{int(p)}",
                                "Implied": f"{american_to_prob(int(p))*100:.1f}%",
                            })
                    if df_data:
                        st.dataframe(pd.DataFrame(df_data), hide_index=True,
                                     width="stretch", height=min(200, 40*len(df_data)+38))
        if has_model and away_ml and home_ml:
            st.caption(f"**Devigged market:** {away.split()[-1]} {gm.devig_away_prob*100:.1f}% / {home.split()[-1]} {gm.devig_home_prob*100:.1f}%")
            st.caption(f"Market vig: {vig_pct(away_ml, home_ml):.2f}%")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("")


# ─────────────────────────────────────────────────────────────
# MODEL EXPLAINER
# ─────────────────────────────────────────────────────────────
def show_model_explainer():
    st.subheader("🧠 How the Model Works")
    st.markdown(f"""
<div style="background:{color('bg_panel')};border:1px solid {color('border')};
            border-radius:10px;padding:20px;line-height:1.8">

<div style="font-size:15px;font-weight:700;color:{color('text_primary')};margin-bottom:16px">
  Elo + FIP Probabilistic Model — 57.33% backtested accuracy (Birdland Metrics, 3 seasons)
</div>

<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
<div>

**Step 1 — Team Elo Rating**
Each team carries an Elo strength rating (avg = 1500).
Updates after every game (K=6) with margin-of-victory scaling.
Home field = +55 Elo points.

**Step 2 — Pitcher FIP Adjustment**
FIP (Fielding Independent Pitching) is more predictive than ERA.
Formula: `(4.20 − pitcher_FIP) × 50 Elo points`
Ace at FIP 2.10 → +105 Elo. Liability at FIP 6.10 → −95 Elo.

**Step 3 — Win Probability**
`P(home win) = 1 / (1 + 10^(−ΔElo/400))`
Shrinkage cap: never predict below 16% or above 84%.

</div>
<div>

**Step 4 — No-Vig Devigging**
Strip the sportsbook's juice from both sides.
MPTO method: normalize implied probs back to 100%.
Result = "true" market probability without the vig.

**Step 5 — Edge Calculation**
`Edge = Model Probability − Devigged Market Probability`
Positive edge = our model sees more probability than the market prices.

**Step 6 — Quarter Kelly Sizing**
`f* = (b×p − q) / b × 0.25`
Professional standard: 25% of full Kelly accounts for model uncertainty.

</div>
</div>

<div style="margin-top:16px;padding-top:14px;border-top:1px solid {color('border')};
            font-size:12px;color:{color('text_muted')}">
Edge thresholds: <b style="color:{color('green')}">BEST VALUE ≥8%</b> ·
<b style="color:{color('green')}">STRONG ≥5%</b> ·
<b style="color:{color('green')}">PLAY ≥2%</b> ·
<b style="color:{color('amber')}">LEAN ≥0%</b> ·
<b style="color:{color('red')}">SKIP &lt;0%</b>
· Minimum 2 credits/day to run. Use FIP not ERA when updating pitcher DB.
</div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# PITCHER ANALYZER
# ─────────────────────────────────────────────────────────────
def pitcher_analyzer():
    st.subheader("⚾ Pitcher + K Prop Analyzer")
    st.caption("Uses FIP (not ERA) as primary input — more predictive of future performance.")

    with st.form("pa"):
        c1, c2, c3, c4 = st.columns(4)
        name      = c1.text_input("Name", placeholder="e.g. Misiorowski")
        fip       = c2.number_input("FIP",  0.0, 15.0, 3.50, 0.01, help="Primary input")
        opp_fip   = c3.number_input("Opp FIP", 0.0, 15.0, 4.20, 0.01)
        k9        = c4.number_input("K/9",  0.0, 20.0, 8.5, 0.1)

        c5, c6, c7 = st.columns(3)
        k_line    = c5.number_input("K Prop Line", 0.5, 20.0, 5.5, 0.5)
        k_odds    = c6.number_input("K Prop Odds", -1000, 2000, -110, 5)
        ml_odds   = c7.number_input("Team ML Odds", -1000, 2000, -140, 5)

        opp_k_pct = st.slider("Opponent K% (0.22 = league avg)", 0.15, 0.35, 0.22, 0.01)
        submitted = st.form_submit_button("Analyze", width="stretch", type="primary")

    if not submitted:
        return

    p = PitcherProfile(name=name or "SP", team="—", fip=fip, k9=k9)
    opp_p = PitcherProfile(name="Opponent SP", team="—", fip=opp_fip)

    from utils.model import ELO_DEFAULT, devig, quarter_kelly, american_to_prob
    # Model this as a neutral-site game
    home_adj = p.elo_adjustment + ELO_DEFAULT
    away_adj = opp_p.elo_adjustment + ELO_DEFAULT
    raw_prob = 1.0 / (1.0 + 10.0 ** (-((home_adj - away_adj)) / 400))
    model_prob = max(0.16, min(0.84, raw_prob))

    ml_implied = american_to_prob(ml_odds)
    ml_edge = (model_prob - ml_implied) * 100
    ml_kelly = quarter_kelly(ml_odds, model_prob) * 100

    kr = k_prop_model(k9=k9, innings_expected=6.0, prop_line=k_line,
                      odds=k_odds, opponent_k_pct=opp_k_pct)

    st.markdown("---")
    mc1, mc2 = st.columns(2)
    with mc1:
        st.markdown(f"### {name or 'Pitcher'}")
        st.markdown(tier_badge(p.tier), unsafe_allow_html=True)
        st.markdown(f"""
<div style="margin-top:12px;font-size:13px;color:{color('text_secondary')}">
  FIP Elo adjustment: <b style="color:{'#3FB950' if p.elo_adjustment >= 0 else '#F85149'}">
  {'+' if p.elo_adjustment >= 0 else ''}{p.elo_adjustment:.0f} Elo pts</b>
  vs opponent ({'+' if opp_p.elo_adjustment >= 0 else ''}{opp_p.elo_adjustment:.0f} pts)
</div>
""", unsafe_allow_html=True)

        st.markdown(f"**ML at {'+'if ml_odds>0 else ''}{ml_odds}**")
        m1, m2, m3 = st.columns(3)
        m1.metric("Model Prob",  f"{model_prob*100:.1f}%")
        m2.metric("Implied",     f"{ml_implied*100:.1f}%")
        m3.metric("Edge",        f"{ml_edge:+.1f}%", delta="+EV" if ml_edge > 0 else "−EV")
        if ml_edge >= 5:
            st.success(f"✅ Strong play — {ml_edge:+.1f}% edge")
        elif ml_edge >= 2:
            st.info(f"⚡ Play — {ml_edge:+.1f}% edge")
        elif ml_edge >= 0:
            st.warning(f"🔄 Lean — {ml_edge:+.1f}% edge")
        else:
            st.error(f"🚫 Skip — {ml_edge:+.1f}% edge")
        st.caption(f"Quarter Kelly stake: {ml_kelly:.1f}% of bankroll")

    with mc2:
        st.markdown("**K Prop (Poisson Model)**")
        pr_clr = color("green") if kr["priority"] in ("BEST VALUE","STRONG") else color("amber") if kr["priority"] in ("PLAY","LEAN") else color("red")
        st.markdown(f"""
<div style="background:{color('bg_panel_2')};border-left:4px solid {pr_clr};
            padding:12px;border-radius:6px;margin-bottom:12px">
  <div style="font-weight:700;color:{pr_clr};font-size:14px">{kr['priority']}</div>
  <div style="color:{color('text_secondary')};font-size:13px;margin-top:4px">{kr['signal']}</div>
</div>
""", unsafe_allow_html=True)
        k1, k2, k3 = st.columns(3)
        k1.metric("Expected Ks",  str(kr['expected_ks']))
        k2.metric("Poisson Over%", f"{kr['over_prob']}%")
        k3.metric("Edge",          f"{kr['edge']:+.1f}%")
        st.caption(f"Quarter Kelly: {kr['kelly_pct']:.1f}% bankroll · opp_K%={opp_k_pct:.0%}")


# ─────────────────────────────────────────────────────────────
# EDGE CALCULATOR
# ─────────────────────────────────────────────────────────────
def edge_calculator():
    st.subheader("📊 Edge Calculator & No-Vig Tool")

    t1, t2 = st.tabs(["Single Bet Edge", "No-Vig Two-Way Market"])
    with t1:
        c1, c2, c3 = st.columns(3)
        play   = c1.text_input("Play", "Davis Martin ML")
        odds_v = c2.number_input("Odds", -2000, 5000, -145, 5)
        real   = c3.number_input("Model Prob %", 1.0, 99.0, 62.0, 0.5)

        from utils.model import american_to_prob as atp
        imp = atp(odds_v) * 100
        e   = real - imp
        stake = st.slider("Stake ($)", 10, 500, 100, 10)
        if odds_v >= 0:
            profit = odds_v / 100 * stake
        else:
            profit = 100 / abs(odds_v) * stake
        ev_d = round((real/100) * profit - (1 - real/100) * stake, 2)
        kf   = quarter_kelly(odds_v, real/100) * 100

        st.markdown(f"""
<div style="background:{color('bg_panel')};border-radius:8px;padding:16px;margin:12px 0;
            border-left:4px solid {color('green') if e>=2 else color('amber') if e>=0 else color('red')}">
  <div style="font-family:'JetBrains Mono',monospace;font-size:24px;font-weight:700;
              color:{color('green') if e>=2 else color('amber') if e>=0 else color('red')}">
    {real:.1f}% − {imp:.1f}% = {e:+.1f}% edge
  </div>
  <div style="font-size:13px;color:{color('text_muted')};margin-top:4px">
    {"✅ +EV — take it" if e>=2 else "⚡ Marginal edge" if e>=0 else "🚫 Negative EV — pass"}
    {"  Negative odds are fine when your model justifies it." if odds_v<0 and e>0 else ""}
  </div>
</div>
""", unsafe_allow_html=True)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Edge",      f"{e:+.1f}%")
        m2.metric("EV/$"+str(stake), f"${ev_d:+.2f}")
        m3.metric("Kelly",     f"{kf:.1f}%")
        m4.metric("Fair Odds", f"{'+' if prob_to_american(real/100)>0 else ''}{prob_to_american(real/100)}")

    with t2:
        st.caption("Enter both sides of a market to remove the vig and get true probabilities.")
        d1, d2 = st.columns(2)
        side_a = d1.text_input("Side A", "Away Team")
        a_odds = d1.number_input("Side A Odds", -2000, 2000, 133, 5, key="dv_a")
        side_b = d2.text_input("Side B", "Home Team")
        b_odds = d2.number_input("Side B Odds", -2000, 2000, -155, 5, key="dv_b")

        da, db = devig(a_odds, b_odds)
        v = vig_pct(a_odds, b_odds)
        st.markdown(f"""
<div style="background:{color('bg_panel')};border-radius:8px;padding:16px;margin-top:12px">
  <div style="font-size:13px;color:{color('text_muted')};margin-bottom:10px;font-weight:600">
    DEVIGGED PROBABILITIES (market vig = {v:.2f}%)
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
    <div>
      <div style="font-size:12px;color:{color('text_muted')}">{side_a}</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:700;
                  color:{color('text_primary')}">{da*100:.1f}%</div>
      <div style="font-size:11px;color:{color('text_muted')}">
        Fair odds: {'+' if prob_to_american(da)>0 else ''}{prob_to_american(da)}
      </div>
    </div>
    <div>
      <div style="font-size:12px;color:{color('text_muted')}">{side_b}</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:700;
                  color:{color('text_primary')}">{db*100:.1f}%</div>
      <div style="font-size:11px;color:{color('text_muted')}">
        Fair odds: {'+' if prob_to_american(db)>0 else ''}{prob_to_american(db)}
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# PARLAY BUILDER
# ─────────────────────────────────────────────────────────────
def parlay_builder():
    st.subheader("🎯 Parlay Builder")
    st.caption("Parlay odds + win probability + EV. Per-leg Kelly + edge breakdown included.")

    from utils.model import parlay_odds as po, american_to_decimal as atd, decimal_to_american as dta

    if "parlay_legs" not in st.session_state:
        st.session_state.parlay_legs = [
            {"play":"Davis Martin ML",  "odds":-120, "model_pct":62.0},
            {"play":"Soroka O6.5 Ks",   "odds": 120, "model_pct":65.0},
        ]

    for i, leg in enumerate(st.session_state.parlay_legs):
        c1, c2, c3, c4 = st.columns([4,2,2,1])
        leg["play"]      = c1.text_input(f"Leg {i+1}", value=leg["play"], key=f"pl_{i}",
                                          label_visibility="collapsed", placeholder=f"Leg {i+1}")
        leg["odds"]      = c2.number_input("Odds",    value=leg["odds"],      key=f"po_{i}",
                                            min_value=-2000, max_value=5000, step=5,
                                            label_visibility="collapsed")
        leg["model_pct"] = c3.number_input("Model%", value=leg["model_pct"], key=f"pm_{i}",
                                            min_value=1.0, max_value=99.0, step=1.0,
                                            label_visibility="collapsed")
        if c4.button("✕", key=f"prm_{i}") and len(st.session_state.parlay_legs) > 1:
            st.session_state.parlay_legs.pop(i)
            st.rerun()

    if st.button("➕ Add Leg"):
        st.session_state.parlay_legs.append({"play":"", "odds":-130, "model_pct":58.0})
        st.rerun()

    legs = st.session_state.parlay_legs
    if len(legs) < 2:
        return

    combined_dec  = 1.0
    combined_prob = 1.0
    for l in legs:
        combined_dec  *= atd(l["odds"])
        combined_prob *= l["model_pct"] / 100

    combined_american = dta(combined_dec)
    stake  = st.slider("Stake ($)", 5, 500, 25, 5)
    profit = (combined_dec - 1) * stake
    ev_d   = round(combined_prob * profit - (1-combined_prob) * stake, 2)

    m1, m2, m3, m4 = st.columns(4)
    pfx = "+" if combined_american > 0 else ""
    m1.metric("Parlay Odds", f"{pfx}{combined_american}")
    m2.metric("Win Prob",    f"{combined_prob*100:.1f}%")
    m3.metric("Payout",      f"${profit:.0f}")
    m4.metric("EV",          f"${ev_d:+.2f}", delta="+EV" if ev_d > 0 else "−EV")

    with st.expander("📊 Per-leg breakdown"):
        rows = []
        for l in legs:
            imp = american_to_prob(l["odds"])*100
            e   = l["model_pct"] - imp
            kf  = quarter_kelly(l["odds"], l["model_pct"]/100)*100
            rows.append({
                "Play":       l["play"] or "(unnamed)",
                "Odds":       f"+{l['odds']}" if l["odds"] > 0 else str(l["odds"]),
                "Model %":    f"{l['model_pct']:.1f}%",
                "Implied %":  f"{imp:.1f}%",
                "Edge":       f"{e:+.1f}%",
                "Kelly":      f"{kf:.1f}%",
                "Status":     "✅" if e >= 2 else "⚡" if e >= 0 else "⚠️ Drag",
            })
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
st.title("⚾ MLB Analysis")
st.caption("Elo + FIP model · No-vig devigging · Poisson K props · Quarter Kelly sizing · 57% backtested accuracy")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 Today's Slate",
    "🧠 Model Explained",
    "⚾ Pitcher Analyzer",
    "📊 Edge / No-Vig",
    "🎯 Parlay Builder",
])

with tab1:
    games = load_mlb_games()
    if not games:
        st.warning("No MLB games in DB. Go to **Data Manager → Fetch MLB**.")
    else:
        # Top plays summary strip
        top_plays = []
        for g in games:
            rows = load_game_odds(g["id"])
            apn, apd = find_pitcher(g["away_team"])
            hpn, hpd = find_pitcher(g["home_team"])
            a_ml, _ = best_price(rows, "h2h", g["away_team"])
            h_ml, _ = best_price(rows, "h2h", g["home_team"])
            if apd and hpd and a_ml and h_ml:
                gm = build_game_model(
                    g["away_team"], g["home_team"],
                    apd["fip"], hpd["fip"],
                    a_ml, h_ml, away_pitcher_name=apn, home_pitcher_name=hpn
                )
                be = max(gm.away_edge, gm.home_edge)
                if be >= MIN_EDGE_PCT:
                    best_team  = g["away_team"] if gm.away_edge >= gm.home_edge else g["home_team"]
                    best_ml    = a_ml if gm.away_edge >= gm.home_edge else h_ml
                    best_label = gm.away_rec if gm.away_edge >= gm.home_edge else gm.home_rec
                    top_plays.append((be, best_team, best_ml, best_label,
                                      g["away_team"].split()[-1]+"@"+g["home_team"].split()[-1]))

        top_plays.sort(key=lambda x: -x[0])
        if top_plays:
            st.markdown("#### ⚡ Top Plays Today")
            cols = st.columns(min(4, len(top_plays)))
            for ci, (be, bt, bml, bl, matchup) in enumerate(top_plays[:4]):
                with cols[ci]:
                    ml_str = f"+{bml}" if bml > 0 else str(bml)
                    rc = REC_COLORS.get(bl, color("text_primary"))
                    st.markdown(f"""
<div style="background:{color('bg_panel')};border:1px solid {rc};border-radius:8px;
            padding:14px;text-align:center">
  <div style="font-size:9px;color:{color('text_muted')};font-weight:700;
              text-transform:uppercase">{matchup}</div>
  <div style="font-size:11px;font-weight:700;color:{rc};margin:4px 0">{bl}</div>
  <div style="font-family:'JetBrains Mono',monospace;font-size:20px;font-weight:700;
              color:{color('green') if bml and bml>0 else color('text_primary')}">{ml_str}</div>
  <div style="font-family:'JetBrains Mono',monospace;font-size:13px;
              color:{color('green')};font-weight:600">Edge +{be:.1f}%</div>
  <div style="font-size:10px;color:{color('text_muted')};margin-top:2px">{bt.split()[-1]}</div>
</div>
""", unsafe_allow_html=True)
            st.markdown("---")

        st.caption(f"{len(games)} games loaded · Model uses FIP (not ERA) as primary pitcher input")
        for i, g in enumerate(sorted(games, key=lambda x: x.get("start_time","")), 1):
            render_game_card(g, load_game_odds(g["id"]), i)

with tab2:
    show_model_explainer()
with tab3:
    pitcher_analyzer()
with tab4:
    edge_calculator()
with tab5:
    parlay_builder()
