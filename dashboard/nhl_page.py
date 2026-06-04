"""
APEX ANALYTICS - NHL Model
Puck line structural plays + player scoring props + devigged probabilities.
"""
import sys, json
from pathlib import Path
import streamlit as st
import pandas as pd
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from services.player_service import (
    nhl_get_roster, nhl_get_player_gamelog,
    compute_prop_line, hit_rate, matchup_history,
    NHL_FULL_TO_ABBR,
)
from utils.model import devig, american_to_prob, vig_pct
from dashboard.premium_styles import TOKENS, color
from dashboard.ui_components import render_game_card
from dashboard.mobile_utils import inject_mobile_css

inject_mobile_css()

# ─────────────────────────────────────────────────────────────
# DATA LOADERS
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def load_nhl_games():
    return supabase.table("games").select("*").eq("sport","NHL").order("start_time").execute().data or []

@st.cache_data(ttl=120)
def load_game_odds(game_id: str):
    return supabase.table("odds_snapshots").select("*").eq("game_id", game_id).execute().data or []

@st.cache_data(ttl=300)
def load_nhl_players(team_abbr: str):
    return supabase.table("players").select("*").eq("sport","NHL").eq("team", team_abbr).execute().data or []

@st.cache_data(ttl=300)
def load_player_logs(player_id: str, limit: int = 15):
    return (
        supabase.table("player_game_stats")
        .select("*").eq("player_id", player_id)
        .order("date", desc=True).limit(limit).execute().data or []
    )

def best_price(rows, market, label):
    m = [r for r in rows if r.get("market_type")==market and r.get("market_label")==label]
    if not m: return None, None
    b = max(m, key=lambda r: r.get("price") or -9999)
    return int(b["price"]), b.get("book","?")

def safe_avg(values, n=None):
    v = [float(x) for x in (values[:n] if n else values) if x is not None]
    return round(sum(v)/len(v), 2) if v else 0.0


# ─────────────────────────────────────────────────────────────
# STRUCTURAL PLAY CHECKER
# ─────────────────────────────────────────────────────────────
def check_puck_line_value(ml: int, team: str) -> dict:
    if ml is None: return {"flag": False}
    if ml < 0 and abs(ml) >= 200:
        return {"flag": True, "type": "TRAP",
                "msg":     f"{team} ML at {ml} — NEVER lay −200+ straight",
                "suggest": f"Use {team} puck line −1.5 (typically +130–+165)"}
    if ml < 0 and abs(ml) >= 150:
        return {"flag": True, "type": "CAUTION",
                "msg":     f"{team} ML at {ml} — heavy juice, consider puck line",
                "suggest": f"Puck line −1.5 at plus-money if team has won 3+ by 2+ goals"}
    return {"flag": False}


# ─────────────────────────────────────────────────────────────
# PLAYER SCORING PROPS TABLE
# ─────────────────────────────────────────────────────────────
def render_nhl_players(game: dict):
    away, home = game["away_team"], game["home_team"]
    away_abbr  = NHL_FULL_TO_ABBR.get(away, "")
    home_abbr  = NHL_FULL_TO_ABBR.get(home, "")

    all_rows = []
    for team_abbr, opp_abbr in [(away_abbr, home_abbr), (home_abbr, away_abbr)]:
        if not team_abbr:
            continue
        players = load_nhl_players(team_abbr)
        if not players:
            continue
        for p in players[:18]:
            logs = load_player_logs(p["id"], limit=10)
            if not logs: continue
            # In our DB: goals→points, assists→rebounds, total_pts→assists
            goals   = [g.get("points", 0) for g in logs]
            assists = [g.get("rebounds", 0) for g in logs]
            pts     = [g.get("assists", 0) for g in logs]
            avg_pts = safe_avg(pts)
            if avg_pts < 0.15: continue
            line    = compute_prop_line(pts)
            hr      = hit_rate(pts, line)
            mh      = matchup_history(logs, opp_abbr, "assists")
            all_rows.append({
                "Player":     p.get("name","?"),
                "Team":       team_abbr,
                "Pos":        p.get("position",""),
                "Pts/G":      avg_pts,
                "Goals/G":    safe_avg(goals),
                "Ast/G":      safe_avg(assists),
                "O/U Line":   f"O{line} pts",
                "Over %":     f"{hr['over']:.0f}%",
                f"vs {opp_abbr}": mh.get("avg","—"),
                "Streak":     f"{hr['streak']} {'O' if hr['streak_dir']=='O' else 'U'}" if hr["streak"]>=2 else "—",
            })

    if not all_rows:
        st.info("No NHL player data in DB yet.")
        if st.button("🔄 Fetch NHL Players (free)", use_container_width=True):
            import subprocess
            r = subprocess.run(
                [sys.executable, "workers/fetch_live_players.py", "--sport", "nhl"],
                capture_output=True, text=True, cwd=str(project_root), timeout=180
            )
            st.cache_data.clear()
            st.success("Done! Refresh the page.")
        return

    all_rows.sort(key=lambda x: x["Pts/G"], reverse=True)
    st.dataframe(pd.DataFrame(all_rows), use_container_width=True, hide_index=True,
        column_config={
            "Player":  st.column_config.TextColumn(width=160),
            "Team":    st.column_config.TextColumn(width=55),
            "Pos":     st.column_config.TextColumn(width=45),
            "Pts/G":   st.column_config.NumberColumn(width=70, format="%.2f"),
            "Goals/G": st.column_config.NumberColumn(width=70, format="%.2f"),
            "Ast/G":   st.column_config.NumberColumn(width=65, format="%.2f"),
            "Over %":  st.column_config.TextColumn(width=70),
        })


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
st.title("🏒 NHL Model")
st.caption("Puck line structural plays · Devigged probabilities · Player scoring props")

games = load_nhl_games()
if not games:
    st.warning("No NHL games loaded. Go to **Data Sync → Fetch NHL**.")
    st.stop()

tab_games, tab_players, tab_guide = st.tabs(["🏒 Games", "🎯 Player Props", "📖 Structural Guide"])

with tab_games:
    cols = st.columns(2)
    for idx, g in enumerate(games):
        away, home = g["away_team"], g["home_team"]
        try:
            t    = datetime.fromisoformat(g["start_time"].replace("Z","+00:00"))
            tstr = t.strftime("%I:%M %p ET")
        except Exception:
            tstr = "TBD"

        rows     = load_game_odds(g["id"])
        away_ml, _= best_price(rows, "h2h", away)
        home_ml, _= best_price(rows, "h2h", home)
        away_pl, _= best_price(rows, "spreads", away)
        home_pl, _= best_price(rows, "spreads", home)
        over_p,  _= best_price(rows, "totals", "Over")
        under_p, _= best_price(rows, "totals", "Under")
        over_rows = [r for r in rows if r.get("market_type")=="totals" and r.get("market_label")=="Over"]
        total_line= max(over_rows, key=lambda r: r.get("price") or -9999).get("line") if over_rows else None

        if not away_ml or not home_ml:
            continue

        dv_a, dv_h = devig(away_ml, home_ml)
        away_check  = check_puck_line_value(away_ml, away)
        home_check  = check_puck_line_value(home_ml, home)

        if dv_a > dv_h:
            edge = (dv_a - american_to_prob(away_ml)) * 100
            rec  = "TRAP" if away_check.get("type")=="TRAP" else ("VALUE" if edge>=1.5 else "LEAN")
            vt, vo = away, away_ml
            mp, dp = dv_a, dv_a
        else:
            edge = (dv_h - american_to_prob(home_ml)) * 100
            rec  = "TRAP" if home_check.get("type")=="TRAP" else ("VALUE" if edge>=1.5 else "LEAN")
            vt, vo = home, home_ml
            mp, dp = dv_h, dv_h

        with cols[idx % 2]:
            render_game_card(
                sport="NHL", away_team=away, home_team=home,
                time_str=tstr, away_ml=away_ml, home_ml=home_ml,
                edge_pct=edge, recommendation=rec,
                model_prob=mp, market_prob=dp,
                value_target=vt, value_odds=vo,
            )

            # Puck lines + total below game card
            ml_fmt = lambda v: (f"+{v}" if v > 0 else str(v)) if v else "—"
            v_clr  = lambda v: TOKENS["green"] if v and v > 0 else TOKENS["text_primary"]
            st.markdown(f"""
<div style="background:{TOKENS['bg_panel_2']};border-radius:6px;padding:10px 16px;
            display:flex;gap:24px;align-items:center;flex-wrap:wrap;margin-top:-12px;
            margin-bottom:8px;border:1px solid {TOKENS['border']}">
  <div style="font-size:10px;color:{TOKENS['text_muted']};font-weight:700;
              text-transform:uppercase">Puck −1.5</div>
  <div>
    <span style="font-size:10px;color:{TOKENS['text_muted']}">{away.split()[-1]} </span>
    <span style="font-family:'JetBrains Mono',monospace;font-weight:700;
                 color:{v_clr(away_pl)}">{ml_fmt(away_pl)}</span>
  </div>
  <div>
    <span style="font-size:10px;color:{TOKENS['text_muted']}">{home.split()[-1]} </span>
    <span style="font-family:'JetBrains Mono',monospace;font-weight:700;
                 color:{v_clr(home_pl)}">{ml_fmt(home_pl)}</span>
  </div>
  {"<div style='font-size:10px;color:" + TOKENS['text_muted'] + "'>O/U " + str(total_line) + "</div>" if total_line else ""}
  <div style="font-size:10px;color:{TOKENS['text_dim']}">
    Vig: {vig_pct(away_ml, home_ml):.1f}%
  </div>
</div>""", unsafe_allow_html=True)

            # Structural warnings
            for chk in [away_check, home_check]:
                if chk.get("flag"):
                    bg  = TOKENS["red_bg"] if chk["type"]=="TRAP" else TOKENS["amber_bg"]
                    brd = TOKENS["red"]    if chk["type"]=="TRAP" else TOKENS["amber"]
                    st.markdown(f"""
<div style="background:{bg};border-left:3px solid {brd};padding:8px 14px;
            border-radius:4px;margin-bottom:8px">
  <span style="color:{brd};font-size:12px;font-weight:700">
    {'🚫' if chk['type']=='TRAP' else '⚠️'} {chk['msg']}
  </span><br>
  <span style="color:{TOKENS['text_secondary']};font-size:11px">💡 {chk['suggest']}</span>
</div>""", unsafe_allow_html=True)

with tab_players:
    if len(games) > 1:
        opts = {f"{g['away_team']} @ {g['home_team']}": g for g in games}
        sel  = st.selectbox("Game", list(opts.keys()), label_visibility="collapsed")
        render_nhl_players(opts[sel])
    else:
        render_nhl_players(games[0])

with tab_guide:
    st.markdown(f"""
<div style="background:{TOKENS['bg_panel']};border:1px solid {TOKENS['border_strong']};
            border-radius:10px;padding:22px;line-height:1.9">
<div style="font-size:16px;font-weight:800;color:{TOKENS['text_primary']};margin-bottom:16px">
  🏒 NHL Structural Play Rules
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
<div>

**−200+ ML = TRAP (always)**
Never lay −200 or worse straight on NHL.
Convert to puck line −1.5 at plus-money.
e.g. COL −215 → COL puck line +140 ✅

**Series Pattern**
Team winning 3+ straight by 2+ goals?
→ Take their puck line −1.5.
Works especially well in playoff runs.

</div>
<div>

**Plus-money underdog value**
Dog at +130 or better = evaluate carefully.
Devig the market first to find true win %.
If model % > devigged % = edge.

**Anytime goal scorer**
Pair ATG scorer (+130–+160) with O5.5 total
for correlated same-game parlay.
Only take ATG when player has 0.4+ G/game.

</div>
</div>
</div>""", unsafe_allow_html=True)
