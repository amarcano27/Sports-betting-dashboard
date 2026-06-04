"""
APEX ANALYTICS - NFL Model
Devigged market analysis · ATS structural plays · Totals · Line movement
"""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from collections import defaultdict

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from utils.model import devig, american_to_prob, vig_pct, quarter_kelly
from utils.line_movement import get_line_movements, SIGNAL_COLORS, SIGNAL_DESCRIPTIONS
from utils.elo_seeds import BASE_ELO
from dashboard.ui_components import render_game_card
from dashboard.mobile_utils import inject_mobile_css
from dashboard.premium_styles import TOKENS

inject_mobile_css()

# ─────────────────────────────────────────────────────────────
# NFL ELO — 2025 season final standings proxy
# ─────────────────────────────────────────────────────────────
NFL_ELO = {
    # AFC — rough Elo based on 2025 season W/L records
    "Kansas City Chiefs":       1650, "Buffalo Bills":           1620,
    "Baltimore Ravens":         1580, "Cincinnati Bengals":      1520,
    "Houston Texans":           1540, "Los Angeles Chargers":    1500,
    "Pittsburgh Steelers":      1490, "Cleveland Browns":        1430,
    "Indianapolis Colts":       1460, "Jacksonville Jaguars":    1440,
    "Tennessee Titans":         1420, "Denver Broncos":          1480,
    "Las Vegas Raiders":        1400, "New England Patriots":    1370,
    "New York Jets":            1450, "Miami Dolphins":          1470,
    # NFC
    "Detroit Lions":            1600, "Philadelphia Eagles":     1590,
    "San Francisco 49ers":      1570, "Dallas Cowboys":          1530,
    "Green Bay Packers":        1540, "Washington Commanders":   1510,
    "Los Angeles Rams":         1490, "Tampa Bay Buccaneers":    1470,
    "Seattle Seahawks":         1460, "Minnesota Vikings":       1480,
    "New Orleans Saints":       1430, "Atlanta Falcons":         1440,
    "Chicago Bears":            1420, "New York Giants":         1390,
    "Carolina Panthers":        1380, "Arizona Cardinals":       1410,
}

def _elo(team): return NFL_ELO.get(team, BASE_ELO)


# ─────────────────────────────────────────────────────────────
# DATA LOADERS
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def load_nfl_games():
    return (supabase.table("games").select("*")
            .eq("sport","NFL").order("start_time").execute().data or [])

@st.cache_data(ttl=120)
def load_game_odds(game_id: str):
    return (supabase.table("odds_snapshots").select("*")
            .eq("game_id", game_id).execute().data or [])

def best_price(rows, market, label):
    m = [r for r in rows if r.get("market_type")==market and r.get("market_label")==label]
    if not m: return None, None
    b = max(m, key=lambda r: r.get("price") or -9999)
    return int(b["price"]), b.get("book","?")


# ─────────────────────────────────────────────────────────────
# NFL STRUCTURAL RULES
# ─────────────────────────────────────────────────────────────
def check_nfl_structural(away_ml, home_ml, away_team, home_team):
    flags = []
    # Never lay more than -200 straight in NFL (even less margin than MLB/NHL)
    for team, ml in [(away_team, away_ml), (home_team, home_ml)]:
        if ml and ml < -200:
            flags.append({
                "type": "TRAP",
                "msg":  f"{team.split()[-1]} ML at {ml} — heavy chalk in NFL is a trap",
                "suggest": "Use spread -3 or -3.5 at -115 to -125 instead",
            })
    return flags


# ─────────────────────────────────────────────────────────────
# PAGE
# ─────────────────────────────────────────────────────────────
st.title("🏈 NFL Model")
st.caption("2026 season futures · Devigged market probabilities · ATS structural analysis · Line movement")

games = load_nfl_games()
if not games:
    st.warning("No NFL games loaded. Go to **Data Sync** and fetch NFL odds.")
    st.stop()

# ── Week grouping ─────────────────────────────────────────────
by_week: dict[str, list] = defaultdict(list)
for g in games:
    try:
        t    = datetime.fromisoformat(g["start_time"].replace("Z","+00:00"))
        week = t.strftime("Week of %b %d")
    except Exception:
        week = "TBD"
    by_week[week].append(g)

weeks = list(by_week.keys())
sel_week = st.selectbox("Week", weeks, label_visibility="collapsed")
week_games = by_week[sel_week]

tab_games, tab_edges, tab_totals = st.tabs([
    f"🏈 Games ({len(week_games)})",
    "⚡ Top Edges",
    "📊 Totals Board",
])

# ─────────────────────────────────────────────────────────────
# TAB 1 — GAME CARDS
# ─────────────────────────────────────────────────────────────
with tab_games:
    # Pre-fetch line movement
    gids  = [g["id"] for g in week_games]
    moves = get_line_movements(supabase, gids)

    cols = st.columns(2)
    for idx, g in enumerate(week_games):
        away, home = g["away_team"], g["home_team"]
        try:
            t    = datetime.fromisoformat(g["start_time"].replace("Z","+00:00"))
            tstr = t.strftime("%a %b %d · %I:%M %p ET")
        except Exception:
            tstr = "TBD"

        rows = load_game_odds(g["id"])
        away_ml, away_book = best_price(rows, "h2h", away)
        home_ml, home_book = best_price(rows, "h2h", home)
        away_sp, _         = best_price(rows, "spreads", away)
        home_sp, _         = best_price(rows, "spreads", home)
        over_p, _          = best_price(rows, "totals", "Over")
        under_p, _         = best_price(rows, "totals", "Under")

        if not away_ml or not home_ml:
            continue

        dv_a, dv_h = devig(away_ml, home_ml)

        # Elo-adjusted model prob
        from utils.model import ELO_DEFAULT, HOME_FIELD_ELO, ELO_SCALE, SHRINK_MIN, SHRINK_MAX
        import math
        elo_diff = (_elo(home) + HOME_FIELD_ELO) - _elo(away)
        raw_home = 1.0 / (1.0 + 10.0 ** (-elo_diff / ELO_SCALE))
        model_h  = max(SHRINK_MIN, min(SHRINK_MAX, raw_home))
        model_a  = 1.0 - model_h

        away_edge = round((model_a - dv_a) * 100, 1)
        home_edge = round((model_h - dv_h) * 100, 1)

        if away_edge >= home_edge:
            best_e, vt, vo, mp, dp = away_edge, away, away_ml, model_a, dv_a
        else:
            best_e, vt, vo, mp, dp = home_edge, home, home_ml, model_h, dv_h

        # Structural check
        flags = check_nfl_structural(away_ml, home_ml, away, home)
        if flags:
            rec = "TRAP"
        elif best_e >= 5:
            rec = "BEST VALUE"
        elif best_e >= 2:
            rec = "PLAY"
        elif best_e >= 0:
            rec = "LEAN"
        else:
            rec = "SKIP"

        # Line movement
        gm_moves = moves.get(g["id"], {})
        steam    = None
        for side, mv in [(away, gm_moves.get(away,{})), (home, gm_moves.get(home,{}))]:
            sig = mv.get("move",{}).get("signal","FLAT")
            if sig in ("STEAM","MOVE"):
                steam = (side, mv)

        with cols[idx % 2]:
            render_game_card(
                sport="NFL", away_team=away, home_team=home,
                time_str=tstr, away_ml=away_ml, home_ml=home_ml,
                edge_pct=best_e, recommendation=rec,
                model_prob=mp, market_prob=dp,
                value_target=vt, value_odds=vo,
            )

            # Spread + total line
            fmt = lambda v: (f"+{v}" if v and v > 0 else str(v)) if v else "—"
            sp_rows = [r for r in rows if r.get("market_type")=="spreads"]
            away_sp_line = next((r.get("line") for r in sp_rows
                                 if r.get("market_label")==away), None)
            over_rows = [r for r in rows if r.get("market_type")=="totals"
                         and r.get("market_label")=="Over"]
            total_line = max(over_rows, key=lambda r: r.get("price") or -9999).get("line") if over_rows else None

            st.markdown(f"""
<div style="background:{TOKENS['bg_panel_2']};border-radius:6px;padding:9px 14px;
            margin-top:-12px;margin-bottom:8px;border:1px solid {TOKENS['border']};
            display:flex;gap:20px;flex-wrap:wrap;align-items:center">
  {"<div style='font-size:10px;color:" + TOKENS['text_muted'] + "'>Spread: <b style=color:" + TOKENS['text_primary'] + ">" + away.split()[-1] + " " + str(away_sp_line) + "</b></div>" if away_sp_line else ""}
  {"<div style='font-size:10px;color:" + TOKENS['text_muted'] + "'>Total: <b style=color:" + TOKENS['text_primary'] + ">O/U " + str(total_line) + "</b></div>" if total_line else ""}
  <div style="font-size:10px;color:{TOKENS['text_muted']}">
    Elo: {away.split()[-1]} {_elo(away)} / {home.split()[-1]} {_elo(home)}
  </div>
  <div style="font-size:10px;color:{TOKENS['text_dim']}">Vig {vig_pct(away_ml,home_ml):.1f}%</div>
</div>""", unsafe_allow_html=True)

            # Structural trap warnings
            for flag in flags:
                sc = TOKENS["red"]
                st.markdown(f"""
<div style="background:{sc}18;border-left:3px solid {sc};padding:7px 12px;
            border-radius:4px;margin-bottom:8px;font-size:12px">
  <span style="color:{sc};font-weight:700">🚫 {flag['msg']}</span><br>
  <span style="color:{TOKENS['text_muted']}">💡 {flag['suggest']}</span>
</div>""", unsafe_allow_html=True)

            # Steam alert
            if steam:
                s_name, smv = steam
                sc2 = SIGNAL_COLORS.get(smv.get("move",{}).get("signal","FLAT"), TOKENS["text_muted"])
                op  = smv.get("open")
                cu  = smv.get("current")
                o_s = (f"+{op}" if op and op>0 else str(op)) if op else "—"
                c_s = (f"+{cu}" if cu and cu>0 else str(cu)) if cu else "—"
                st.markdown(f"""
<div style="background:{sc2}18;border-left:3px solid {sc2};padding:7px 12px;
            border-radius:4px;margin-bottom:8px;font-size:12px;
            color:{sc2};font-weight:700">
  ⚡ STEAM · {s_name.split()[-1]}
  <span style="font-family:'JetBrains Mono',monospace"> {o_s} → {c_s}</span>
</div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# TAB 2 — TOP EDGES
# ─────────────────────────────────────────────────────────────
with tab_edges:
    st.subheader("⚡ Top Edge Plays This Week")
    edge_rows = []
    for g in week_games:
        away, home = g["away_team"], g["home_team"]
        rows = load_game_odds(g["id"])
        away_ml, _ = best_price(rows, "h2h", away)
        home_ml, _ = best_price(rows, "h2h", home)
        if not away_ml or not home_ml: continue

        dv_a, dv_h = devig(away_ml, home_ml)
        elo_diff = (_elo(home) + HOME_FIELD_ELO) - _elo(away)
        raw_h = 1.0/(1.0+10.0**(-elo_diff/ELO_SCALE))
        model_h = max(SHRINK_MIN, min(SHRINK_MAX, raw_h))
        model_a = 1.0 - model_h

        for team, ml, model_p, dv_p in [
            (away, away_ml, model_a, dv_a),
            (home, home_ml, model_h, dv_h),
        ]:
            edge = round((model_p - dv_p)*100, 1)
            if edge < 1.0: continue
            try:
                t    = datetime.fromisoformat(g["start_time"].replace("Z","+00:00"))
                tstr = t.strftime("%a %b %d")
            except Exception:
                tstr = "?"
            kelly = quarter_kelly(ml, model_p)
            edge_rows.append({
                "Team":      team,
                "ML":        f"+{ml}" if ml>0 else str(ml),
                "Model %":   f"{model_p*100:.1f}%",
                "Market %":  f"{dv_p*100:.1f}%",
                "Edge":      f"{edge:+.1f}%",
                "Kelly":     f"{kelly*100:.1f}%",
                "Matchup":   f"{away.split()[-1]} @ {home.split()[-1]}",
                "Date":      tstr,
                "Rating":    "BEST VALUE" if edge>=8 else "STRONG" if edge>=5 else "PLAY",
            })

    if edge_rows:
        edge_rows.sort(key=lambda x: float(x["Edge"].rstrip("%")), reverse=True)
        st.dataframe(pd.DataFrame(edge_rows), use_container_width=True, hide_index=True,
            column_config={
                "Team":     st.column_config.TextColumn(width=180),
                "ML":       st.column_config.TextColumn(width=70),
                "Model %":  st.column_config.TextColumn(width=80),
                "Market %": st.column_config.TextColumn(width=80),
                "Edge":     st.column_config.TextColumn(width=70),
                "Kelly":    st.column_config.TextColumn(width=70),
                "Matchup":  st.column_config.TextColumn(width=160),
                "Date":     st.column_config.TextColumn(width=90),
                "Rating":   st.column_config.TextColumn(width=95),
            })
    else:
        st.info("No edges ≥1% found in this week's slate.")


# ─────────────────────────────────────────────────────────────
# TAB 3 — TOTALS BOARD
# ─────────────────────────────────────────────────────────────
with tab_totals:
    st.subheader("📊 Totals Board")
    st.caption("Over/Under lines and pricing for every game this week.")
    tot_rows = []
    for g in week_games:
        away, home = g["away_team"], g["home_team"]
        rows = load_game_odds(g["id"])
        over_p,  _ = best_price(rows, "totals", "Over")
        under_p, _ = best_price(rows, "totals", "Under")
        over_list  = [r for r in rows if r.get("market_type")=="totals"
                      and r.get("market_label")=="Over"]
        total_line = (max(over_list, key=lambda r: r.get("price") or -9999).get("line")
                      if over_list else None)
        if not total_line: continue
        try:
            t    = datetime.fromisoformat(g["start_time"].replace("Z","+00:00"))
            tstr = t.strftime("%a %b %d")
        except Exception:
            tstr = "?"
        tot_rows.append({
            "Game":    f"{away.split()[-1]} @ {home.split()[-1]}",
            "Date":    tstr,
            "Line":    total_line,
            "Over":    f"+{over_p}"  if over_p  and over_p  > 0 else str(over_p)  if over_p  else "—",
            "Under":   f"+{under_p}" if under_p and under_p > 0 else str(under_p) if under_p else "—",
            "Juice":   f"{vig_pct(over_p, under_p):.1f}%" if over_p and under_p else "—",
        })
    if tot_rows:
        tot_rows.sort(key=lambda x: x["Line"] or 0, reverse=True)
        st.dataframe(pd.DataFrame(tot_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No totals data available for this week.")
