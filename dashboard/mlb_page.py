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
from utils.model import (
    build_game_model, devig, american_to_prob, k_prop_model,
    vig_pct, quarter_kelly,
)
from utils.line_movement import get_line_movements, SIGNAL_COLORS, SIGNAL_DESCRIPTIONS
from dashboard.ui_components import render_game_card
from dashboard.mobile_utils import inject_mobile_css

inject_mobile_css()

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
st.caption("Elo + FIP · Line Movement · K Props · F5 Model · Real standings Elo")

games = load_mlb_games()
if not games:
    st.warning("No MLB games found. Go to **Data Sync** and fetch MLB odds.")
    st.stop()

# Pre-fetch line movement for all games at once (single DB query)
game_ids = [g["id"] for g in games]
line_moves = get_line_movements(supabase, game_ids)

tab_full, tab_f5, tab_kprops = st.tabs([
    "⚾ Full Game ML",
    "5️⃣ First 5 Innings (F5)",
    "🎯 K Prop Board",
])

with tab_full:
    cols = st.columns(2)
    for idx, g in enumerate(games):
        away, home = g["away_team"], g["home_team"]
        try:
            t = datetime.fromisoformat(g["start_time"].replace("Z", "+00:00"))
            time_str = t.strftime("%I:%M %p ET")
        except Exception:
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
            gm = build_game_model(away, home, away_pd["fip"], home_pd["fip"],
                                  away_ml, home_ml,
                                  away_pitcher_name=away_pn or away,
                                  home_pitcher_name=home_pn or home)
            best_e     = max(gm.away_edge, gm.home_edge)
            rec        = gm.away_rec if gm.away_edge >= gm.home_edge else gm.home_rec
            model_p    = gm.model_away_prob if gm.away_edge >= gm.home_edge else gm.model_home_prob
            dv_p       = dv_a if gm.away_edge >= gm.home_edge else dv_h
            value_team = away if gm.away_edge >= gm.home_edge else home
            value_odds = away_ml if gm.away_edge >= gm.home_edge else home_ml
        else:
            if dv_a > dv_h:
                best_e, model_p, dv_p = (dv_a - american_to_prob(away_ml)) * 100, dv_a, dv_a
                value_team, value_odds = away, away_ml
            else:
                best_e, model_p, dv_p = (dv_h - american_to_prob(home_ml)) * 100, dv_h, dv_h
                value_team, value_odds = home, home_ml
            rec = "PLAY" if best_e >= 2 else "LEAN"

        # Line movement for this game
        gm_moves = line_moves.get(g["id"], {})
        away_move = gm_moves.get(away, {})
        home_move = gm_moves.get(home, {})
        steam_team = None
        for side_name, mv in [(away, away_move), (home, home_move)]:
            if mv.get("move", {}).get("signal") in ("STEAM", "MOVE"):
                steam_team = (side_name, mv["move"])

        with cols[idx % 2]:
            render_game_card(
                sport="MLB", away_team=away, home_team=home,
                time_str=time_str, away_ml=away_ml, home_ml=home_ml,
                edge_pct=best_e, recommendation=rec,
                model_prob=model_p, market_prob=dv_p,
                value_target=value_team, value_odds=value_odds,
            )

            # Line movement banner
            if steam_team:
                s_name, s_move = steam_team
                sc = SIGNAL_COLORS.get(s_move["signal"], "#64748B")
                open_p  = away_move.get("open") if s_name == away else home_move.get("open")
                curr_p  = away_move.get("current") if s_name == away else home_move.get("current")
                o_str   = (f"+{open_p}" if open_p and open_p > 0 else str(open_p)) if open_p else "—"
                c_str   = (f"+{curr_p}" if curr_p and curr_p > 0 else str(curr_p)) if curr_p else "—"
                st.markdown(f"""
<div style="background:{sc}18;border-left:3px solid {sc};
            padding:7px 12px;border-radius:4px;margin-top:-12px;margin-bottom:8px;
            font-size:12px;color:{sc};font-weight:700">
  {'⚡ STEAM' if s_move['signal']=='STEAM' else '📈 LINE MOVE'} · {s_name.split()[-1]}
  <span style="font-family:'JetBrains Mono',monospace"> {o_str} → {c_str}</span>
  <span style="font-weight:400;color:#94A3B8"> · {s_move.get('label','')} · {SIGNAL_DESCRIPTIONS.get(s_move['signal'],'')[:55]}</span>
</div>""", unsafe_allow_html=True)

            # Pitcher detail expander
            if away_pd or home_pd:
                with st.expander(f"🔍 Pitcher Detail — {away.split()[-1]} vs {home.split()[-1]}"):
                    pc1, pc2 = st.columns(2)
                    for col_obj, team, pname, pstats in [
                        (pc1, away, away_pn, away_pd),
                        (pc2, home, home_pn, home_pd),
                    ]:
                        with col_obj:
                            if pstats:
                                fip = pstats.get("fip", 4.20)
                                era = pstats.get("era", fip)
                                k9  = pstats.get("k9", 8.0)
                                tier_label = ("TIER 1 — ELITE" if fip < 2.5
                                              else "TIER 2 — STRONG" if fip < 3.25
                                              else "TIER 3 — SOLID" if fip < 4.0
                                              else "TIER 4 — BELOW AVG" if fip < 5.0
                                              else "AVOID")
                                tier_clr = ("#10B981" if "TIER 1" in tier_label
                                            else "#1A7F37" if "TIER 2" in tier_label
                                            else "#F59E0B" if "TIER 3" in tier_label
                                            else "#EF4444")
                                st.markdown(f"""
**{pname or team}** — {team.split()[-1]}
<div style="display:inline-block;background:{tier_clr}22;color:{tier_clr};
            padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;
            margin:4px 0 8px">{tier_label}</div>

| FIP | ERA | K/9 |
|---|---|---|
| **{fip:.2f}** | {era:.2f} | {k9:.1f} |
""", unsafe_allow_html=True)
                            else:
                                st.caption(f"{team.split()[-1]}: pitcher not found in MLB API")


with tab_f5:
    st.subheader("5️⃣ First 5 Innings Model")
    st.caption("""
**F5 bets isolate starter quality** — no bullpen variance, no late-game noise.
Edge formula: FIP-adjusted Elo model prob vs F5 market implied prob.
Rule: only bet F5 when starter is Tier 1 or Tier 2 (FIP < 4.0).
""")

    f5_rows = []
    for g in games:
        away, home = g["away_team"], g["home_team"]
        rows = load_game_odds(g["id"])

        # F5 market uses "alternate_spreads" or "h2h_h1" keys — we use h2h as proxy
        away_ml, _ = best_price(rows, "h2h", away)
        home_ml, _ = best_price(rows, "h2h", home)
        if not away_ml or not home_ml:
            continue

        away_pn, away_pd = find_pitcher(away)
        home_pn, home_pd = find_pitcher(home)
        if not away_pd or not home_pd:
            continue

        # F5 model: same Elo+FIP but weight pitcher 70% / team Elo 30%
        # (starter is more deterministic over 5 innings)
        away_fip = away_pd["fip"]
        home_fip = home_pd["fip"]

        # Only show Tier 1/2 matchups (FIP < 4.0 for at least one starter)
        if away_fip >= 4.0 and home_fip >= 4.0:
            continue

        gm = build_game_model(away, home, away_fip, home_fip, away_ml, home_ml,
                              away_pitcher_name=away_pn or away,
                              home_pitcher_name=home_pn or home)

        # F5 adjustment: compress team Elo influence, boost pitcher
        # Re-run with pitcher adjustment amplified 1.5x
        try:
            from utils.model import PitcherProfile, GameModel, HOME_FIELD_ELO, ELO_SCALE, SHRINK_MIN, SHRINK_MAX
            import math
            ap = PitcherProfile(name=away_pn or away, team=away,
                                fip=away_fip, k9=away_pd.get("k9"))
            hp = PitcherProfile(name=home_pn or home, team=home,
                                fip=home_fip, k9=home_pd.get("k9"))
            # Amplify pitcher Elo adjustment by 1.5x for F5
            a_adj = ap.elo_adjustment * 1.5
            h_adj = hp.elo_adjustment * 1.5
            diff  = (gm.home_elo + h_adj + HOME_FIELD_ELO * 0.5) - (gm.away_elo + a_adj)
            raw   = 1.0 / (1.0 + 10.0 ** (-diff / ELO_SCALE))
            f5_home_prob = max(SHRINK_MIN, min(SHRINK_MAX, raw))
            f5_away_prob = 1.0 - f5_home_prob
        except Exception:
            f5_home_prob = gm.model_home_prob
            f5_away_prob = gm.model_away_prob

        from utils.model import devig as _devig, american_to_prob as _atp
        dv_a, dv_h = _devig(away_ml, home_ml)
        f5_away_edge = round((f5_away_prob - dv_a) * 100, 1)
        f5_home_edge = round((f5_home_prob - dv_h) * 100, 1)

        best_side = away if f5_away_edge >= f5_home_edge else home
        best_edge = f5_away_edge if f5_away_edge >= f5_home_edge else f5_home_edge
        best_odds = away_ml if f5_away_edge >= f5_home_edge else home_ml
        best_prob = f5_away_prob if f5_away_edge >= f5_home_edge else f5_home_prob
        best_pn   = away_pn if f5_away_edge >= f5_home_edge else home_pn
        best_fip  = away_fip if f5_away_edge >= f5_home_edge else home_fip

        tier = ("TIER 1" if best_fip < 2.5 else "TIER 2" if best_fip < 3.25
                else "TIER 3" if best_fip < 4.0 else "SKIP")

        if tier == "SKIP":
            continue

        f5_rows.append({
            "Game":       f"{away.split()[-1]} @ {home.split()[-1]}",
            "Time":       g.get("start_time","")[:10],
            "F5 Play":    f"{best_side.split()[-1]} F5",
            "Starter":    best_pn or "?",
            "Tier":       tier,
            "FIP":        f"{best_fip:.2f}",
            "Odds":       f"+{best_odds}" if best_odds > 0 else str(best_odds),
            "F5 Prob%":   f"{best_prob*100:.1f}%",
            "Edge":       f"{best_edge:+.1f}%",
            "Kelly":      f"{quarter_kelly(best_odds, best_prob)*100:.1f}%",
            "Rating":     "STRONG" if best_edge >= 5 else "PLAY" if best_edge >= 2 else "LEAN",
        })

    if f5_rows:
        f5_rows.sort(key=lambda x: float(x["Edge"].rstrip("%")), reverse=True)
        df_f5 = pd.DataFrame(f5_rows)
        st.dataframe(df_f5, use_container_width=True, hide_index=True,
            column_config={
                "Game":     st.column_config.TextColumn(width=140),
                "F5 Play":  st.column_config.TextColumn(width=110),
                "Starter":  st.column_config.TextColumn(width=160),
                "Tier":     st.column_config.TextColumn(width=90),
                "FIP":      st.column_config.TextColumn(width=60),
                "Odds":     st.column_config.TextColumn(width=70),
                "F5 Prob%": st.column_config.TextColumn(width=80),
                "Edge":     st.column_config.TextColumn(width=70),
                "Kelly":    st.column_config.TextColumn(width=70),
                "Rating":   st.column_config.TextColumn(width=80),
            })
    else:
        st.info("No Tier 1/2 F5 matchups found in today's slate.")


with tab_kprops:
    st.subheader("🎯 K Prop Board")
    st.caption("Poisson probability model for strikeout props. Edge = model prob − implied prob.")

    k_rows = []
    for g in games:
        away, home = g["away_team"], g["home_team"]
        for team, is_home in [(away, False), (home, True)]:
            pn, pstats = find_pitcher(team)
            if not pstats or not pstats.get("k9"):
                continue
            k9   = pstats["k9"]
            exp  = round(k9 * 6 / 9, 1)
            line = max(0.5, round(exp * 2 - 1) / 2)   # ~0.5 below expected pace
            kr   = k_prop_model(k9=k9, innings_expected=6.0,
                                prop_line=line, odds=-115)
            k_rows.append({
                "Pitcher":    pn or team,
                "Team":       team.split()[-1],
                "vs":         home.split()[-1] if not is_home else away.split()[-1],
                "K/9":        k9,
                "Exp 6IP":    exp,
                "Line":       f"O{line}",
                "Model O%":   f"{kr['over_prob']:.0f}%",
                "Implied":    f"{kr['implied_pct']:.0f}%",
                "Edge":       f"{kr['edge']:+.1f}%",
                "Kelly":      f"{kr['kelly_pct']:.1f}%",
                "Signal":     kr["priority"],
            })

    if k_rows:
        k_rows.sort(key=lambda x: float(x["Edge"].rstrip("%")), reverse=True)
        st.dataframe(pd.DataFrame(k_rows), use_container_width=True, hide_index=True,
            column_config={
                "Pitcher":  st.column_config.TextColumn(width=170),
                "Team":     st.column_config.TextColumn(width=70),
                "vs":       st.column_config.TextColumn(width=70),
                "K/9":      st.column_config.NumberColumn(width=60, format="%.1f"),
                "Exp 6IP":  st.column_config.NumberColumn(width=70, format="%.1f"),
                "Model O%": st.column_config.TextColumn(width=80),
                "Edge":     st.column_config.TextColumn(width=70),
                "Signal":   st.column_config.TextColumn(width=100),
            })
    else:
        st.info("No pitcher K data available. Fetch today's probable pitchers via Data Sync.")
