"""
APEX ANALYTICS - NBA Model
Game analysis + full player prop cards with headshots, last 10 games,
matchup history vs tonight's opponent, hit rates, sparklines.
"""
import sys, json
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from services.player_service import (
    nba_headshot_url, compute_prop_line, hit_rate, matchup_history,
    NBA_FULL_TO_ABBR,
)
from utils.model import devig, american_to_prob, quarter_kelly
from dashboard.premium_styles import TOKENS, color
from dashboard.ui_components import render_game_card, render_prop_card
from dashboard.mobile_utils import inject_mobile_css

inject_mobile_css()

# ─────────────────────────────────────────────────────────────
# DATA LOADERS
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def load_nba_games():
    return supabase.table("games").select("*").eq("sport","NBA").order("start_time").execute().data or []

@st.cache_data(ttl=120)
def load_game_odds(game_id: str):
    return supabase.table("odds_snapshots").select("*").eq("game_id", game_id).execute().data or []

@st.cache_data(ttl=300)
def load_nba_players(team_abbrs: tuple):
    result = []
    for abbr in team_abbrs:
        rows = supabase.table("players").select("*").eq("sport","NBA").eq("team", abbr).execute().data or []
        result.extend(rows)
    return result

@st.cache_data(ttl=300)
def load_player_logs(player_id: str, limit: int = 15):
    return (
        supabase.table("player_game_stats")
        .select("*").eq("player_id", player_id)
        .order("date", desc=True).limit(limit).execute().data or []
    )

def best_price(rows, market, label):
    m = [r for r in rows if r.get("market_type") == market and r.get("market_label") == label]
    if not m: return None, None
    b = max(m, key=lambda r: r.get("price") or -9999)
    return int(b["price"]), b.get("book", "?")

def safe_avg(values, n=None):
    v = [float(x) for x in (values[:n] if n else values) if x is not None]
    return round(sum(v) / len(v), 1) if v else 0.0

def get_headshot(player: dict) -> str:
    raw = player.get("raw_data", {})
    if isinstance(raw, str):
        try: raw = json.loads(raw)
        except: raw = {}
    return raw.get("headshot_url", nba_headshot_url(player.get("external_id", "")))

# ─────────────────────────────────────────────────────────────
# SPARKLINE
# ─────────────────────────────────────────────────────────────
def sparkline(values: list, line: float, key: str):
    v = list(reversed(values[:10]))
    if not v:
        return
    colors = [TOKENS["green"] if x > line else TOKENS["red"] for x in v]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=list(range(len(v))), y=v, marker_color=colors))
    fig.add_hline(y=line, line_dash="dot", line_color=TOKENS["amber"], line_width=1.5)
    fig.update_layout(
        height=90, margin=dict(l=0, r=0, t=4, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, range=[0, max(v) * 1.3 if v else 1]),
    )
    st.plotly_chart(fig, use_container_width=True, key=key)

# ─────────────────────────────────────────────────────────────
# PLAYER PROP CARD
# ─────────────────────────────────────────────────────────────
def render_player_card(player: dict, game: dict, opponent_abbr: str):
    name     = player.get("name", "Unknown")
    position = player.get("position", "")
    team     = player.get("team", "")
    pid      = player.get("id")
    headshot = get_headshot(player)

    logs = load_player_logs(pid)
    if not logs:
        return

    pts_vals = [g.get("points", 0) for g in logs]
    reb_vals = [g.get("rebounds", 0) for g in logs]
    ast_vals = [g.get("assists", 0) for g in logs]
    fg3_vals = [g.get("three_pointers_made", 0) for g in logs]
    stl_vals = [g.get("steals", 0) for g in logs]
    blk_vals = [g.get("blocks", 0) for g in logs]

    avg_pts = safe_avg(pts_vals, 10)
    if avg_pts < 4:
        return  # skip bench/inactive players

    pts_line = compute_prop_line(pts_vals)
    reb_line = compute_prop_line(reb_vals)
    ast_line = compute_prop_line(ast_vals)
    fg3_line = compute_prop_line(fg3_vals)
    pra_vals = [p + r + a for p, r, a in zip(pts_vals, reb_vals, ast_vals)]
    pra_line = compute_prop_line(pra_vals)

    pts_hr = hit_rate(pts_vals[:10], pts_line)
    reb_hr = hit_rate(reb_vals[:10], reb_line)
    ast_hr = hit_rate(ast_vals[:10], ast_line)
    pra_hr = hit_rate(pra_vals[:10], pra_line)

    mh_pts = matchup_history(logs, opponent_abbr, "points")
    mh_reb = matchup_history(logs, opponent_abbr, "rebounds")
    mh_ast = matchup_history(logs, opponent_abbr, "assists")

    l5_pts = safe_avg(pts_vals, 5)
    l5_reb = safe_avg(reb_vals, 5)
    l5_ast = safe_avg(ast_vals, 5)

    streak = pts_hr.get("streak", 0)
    streak_dir = pts_hr.get("streak_dir", "")
    streak_txt = ""
    streak_color = TOKENS["text_muted"]
    if streak >= 3:
        if streak_dir == "O":
            streak_txt = f"🔥 {streak}-game Over streak"
            streak_color = TOKENS["green"]
        elif streak_dir == "U":
            streak_txt = f"❄️ {streak}-game Under streak"
            streak_color = TOKENS["cyan"]

    over_pct = pts_hr.get("over", 0)
    hr_color = TOKENS["green"] if over_pct >= 60 else TOKENS["red"] if over_pct < 40 else TOKENS["amber"]

    st.markdown(f"""
<div style="background:{TOKENS['bg_panel']};border:1px solid {TOKENS['border_strong']};
            border-radius:12px;overflow:hidden;margin-bottom:18px">
  <div style="display:flex;gap:0;background:{TOKENS['bg_panel_2']};
              border-bottom:1px solid {TOKENS['border']}">
    <div style="padding:16px 20px;min-width:80px;text-align:center;
                border-right:1px solid {TOKENS['border']}">
      <img src="{headshot}" style="width:72px;height:72px;border-radius:50%;
           object-fit:cover;border:2px solid {TOKENS['border_strong']}"
           onerror="this.style.display='none'"/>
      <div style="font-size:10px;color:{TOKENS['text_muted']};margin-top:6px;
                  font-weight:700;text-transform:uppercase">{position} · {team}</div>
    </div>
    <div style="padding:16px 20px;flex:1">
      <div style="font-size:19px;font-weight:800;color:{TOKENS['text_primary']};
                  letter-spacing:-0.02em">{name}</div>
      <div style="font-size:12px;color:{TOKENS['text_muted']};margin-top:2px">
        vs {opponent_abbr} · {game.get('start_time','')[:10]}
        {"&nbsp; &nbsp;<span style='color:" + streak_color + ";font-weight:700'>" + streak_txt + "</span>" if streak_txt else ""}
      </div>
      <div style="display:flex;gap:20px;margin-top:12px;flex-wrap:wrap">
""", unsafe_allow_html=True)

    for lbl, val, line, hr, l5 in [
        ("PTS", avg_pts, pts_line, pts_hr, l5_pts),
        ("REB", safe_avg(reb_vals), reb_line, reb_hr, l5_reb),
        ("AST", safe_avg(ast_vals), ast_line, ast_hr, l5_ast),
        ("3PM", safe_avg(fg3_vals), fg3_line, None, None),
        ("STL", safe_avg(stl_vals), None, None, None),
        ("BLK", safe_avg(blk_vals), None, None, None),
    ]:
        op = hr.get("over", 0) if hr else 0
        hrc = TOKENS["green"] if op >= 60 else TOKENS["red"] if op < 40 else TOKENS["amber"]
        trend = ""
        if l5 is not None and val > 0:
            diff = l5 - val
            trend = f"<div style='font-size:9px;color:{TOKENS['green'] if diff>0 else TOKENS['red']}'>" \
                    f"{'↑' if diff>=0 else '↓'}{abs(diff):.1f} L5</div>"
        st.markdown(f"""
<div style="background:{TOKENS['bg_main']};border-radius:8px;padding:8px 12px;
            text-align:center;min-width:60px">
  <div style="font-size:9px;color:{TOKENS['text_muted']};font-weight:700;
              text-transform:uppercase">{lbl}</div>
  <div style="font-family:'JetBrains Mono',monospace;font-size:17px;font-weight:800;
              color:{TOKENS['text_primary']};margin-top:2px">{val}</div>
  {"<div style='font-size:9px;color:" + hrc + ";font-weight:700'>O" + str(line) + " | " + f"{op:.0f}%" + "</div>" if line else ""}
  {trend}
</div>""", unsafe_allow_html=True)

    st.markdown("</div></div></div>", unsafe_allow_html=True)

    # ── Tabs ─────────────────────────────────────────────────
    t1, t2, t3 = st.tabs(["📋 Last 10", "🎯 Props", f"⚔️ vs {opponent_abbr}"])

    with t1:
        rows = []
        for g in logs[:10]:
            p, r, a = g.get("points",0), g.get("rebounds",0), g.get("assists",0)
            rows.append({
                "Date": g.get("date","")[:10],
                "Opp":  g.get("opponent","?"),
                "H/A":  "🏠" if g.get("home") else "✈️",
                "PTS":  p, "REB": r, "AST": a,
                "3PM":  g.get("three_pointers_made",0),
                "PRA":  p+r+a,
                "Min":  g.get("minutes_played",0),
            })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True,
                height=min(380, 38*len(rows)+38))
            sparkline(pts_vals, pts_line, f"sp_{pid}_pts")

    with t2:
        pc = st.columns(3)
        for ci, (lbl, vals, line, hr_d) in enumerate([
            ("POINTS",    pts_vals, pts_line, pts_hr),
            ("REBOUNDS",  reb_vals, reb_line, reb_hr),
            ("ASSISTS",   ast_vals, ast_line, ast_hr),
            ("PRA",       pra_vals, pra_line, pra_hr),
            ("3-POINTERS",fg3_vals, fg3_line, None),
        ]):
            if not vals: continue
            op  = hr_d.get("over",0) if hr_d else 0
            avg = safe_avg(vals)
            rc  = TOKENS["green"] if op>=60 else TOKENS["amber"] if op>=50 else TOKENS["red"]
            pri = "STRONG" if op>=65 else "PLAY" if op>=55 else "LEAN" if op>=50 else "SKIP"
            with pc[ci % 3]:
                st.markdown(f"""
<div style="background:{TOKENS['bg_panel_2']};border-radius:8px;padding:12px;
            margin-bottom:10px;border-left:3px solid {rc}">
  <div style="font-size:9px;color:{TOKENS['text_muted']};font-weight:700;
              text-transform:uppercase;letter-spacing:.05em">{lbl}</div>
  <div style="display:flex;justify-content:space-between;align-items:center;margin-top:6px">
    <div style="font-family:'JetBrains Mono',monospace;font-size:20px;
                font-weight:800;color:{TOKENS['text_primary']}">O{line}</div>
    <div style="font-size:11px;font-weight:800;color:{rc}">{pri}</div>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px">
    <div>
      <div style="font-size:9px;color:{TOKENS['text_muted']}">OVER RATE</div>
      <div style="font-family:'JetBrains Mono',monospace;font-weight:800;
                  color:{rc}">{op:.0f}%</div>
    </div>
    <div>
      <div style="font-size:9px;color:{TOKENS['text_muted']}">AVG</div>
      <div style="font-family:'JetBrains Mono',monospace;font-weight:800;
                  color:{TOKENS['text_primary']}">{avg}</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    with t3:
        if mh_pts["n"] > 0:
            st.caption(f"**{name} vs {opponent_abbr}** — {mh_pts['n']} games on record")
            mh_rows = []
            for g in mh_pts["games"]:
                p, r, a = g.get("points",0), g.get("rebounds",0), g.get("assists",0)
                mh_rows.append({"Date":g.get("date","")[:10],
                    "PTS":p,"REB":r,"AST":a,"PRA":p+r+a,"3PM":g.get("three_pointers_made",0)})
            st.dataframe(pd.DataFrame(mh_rows), use_container_width=True, hide_index=True)
            avg_vs = mh_pts.get("avg", avg_pts)
            delta  = round(avg_vs - avg_pts, 1)
            dc     = TOKENS["green"] if delta > 0 else TOKENS["red"]
            st.markdown(f"""
<div style="background:{TOKENS['bg_panel_2']};border-radius:6px;padding:10px 14px;margin-top:6px">
  <b>vs {opponent_abbr} avg:</b>
  <span style="font-family:'JetBrains Mono',monospace;color:{TOKENS['text_primary']};
               font-weight:700"> {avg_vs} PTS</span>
  <span style="color:{dc};font-size:12px;margin-left:8px">
    {'+' if delta>=0 else ''}{delta} vs season
  </span>
  {"  ·  " + str(mh_reb.get('avg','—')) + " REB  ·  " + str(mh_ast.get('avg','—')) + " AST" if mh_reb.get('n',0)>0 else ""}
</div>""", unsafe_allow_html=True)
        else:
            st.info(f"No history vs {opponent_abbr} in database yet.")

    st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
st.title("🏀 NBA Model")
st.caption("Game analysis · Player props · Headshots · Matchup history · Hit rates")

games = load_nba_games()
if not games:
    st.warning("No NBA games in database. Go to **Data Sync** and fetch NBA.")
    st.stop()

# Game selector
if len(games) > 1:
    opts = {f"{g['away_team']} @ {g['home_team']}": g for g in games}
    sel  = st.selectbox("Select game", list(opts.keys()), label_visibility="collapsed")
    game = opts[sel]
else:
    game = games[0]

away_full = game["away_team"]
home_full = game["home_team"]
away_abbr = NBA_FULL_TO_ABBR.get(away_full, "")
home_abbr = NBA_FULL_TO_ABBR.get(home_full, "")

# ── Game card ────────────────────────────────────────────────
odds_rows = load_game_odds(game["id"])

def _bml(team):
    m = [r for r in odds_rows if r.get("market_type")=="h2h" and r.get("market_label")==team]
    if not m: return None
    return int(max(m, key=lambda r: r.get("price") or -9999).get("price", 0))

away_ml = _bml(away_full)
home_ml = _bml(home_full)

try:
    t   = datetime.fromisoformat(game["start_time"].replace("Z","+00:00"))
    tstr = t.strftime("%I:%M %p ET")
except Exception:
    tstr = "TBD"

if away_ml and home_ml:
    dv_a, dv_h = devig(away_ml, home_ml)
    if dv_a > dv_h:
        edge = (dv_a - american_to_prob(away_ml)) * 100
        rec  = "VALUE" if edge >= 1.5 else "LEAN"
        vt, vo = away_full, away_ml
    else:
        edge = (dv_h - american_to_prob(home_ml)) * 100
        rec  = "VALUE" if edge >= 1.5 else "LEAN"
        vt, vo = home_full, home_ml

    render_game_card(
        sport="NBA", away_team=away_full, home_team=home_full,
        time_str=tstr, away_ml=away_ml, home_ml=home_ml,
        edge_pct=edge, recommendation=rec,
        model_prob=dv_a if dv_a > dv_h else dv_h,
        market_prob=dv_a if dv_a > dv_h else dv_h,
        value_target=vt, value_odds=vo,
    )

# ── Player tabs ──────────────────────────────────────────────
players = load_nba_players(tuple(a for a in [away_abbr, home_abbr] if a))

tab_away, tab_home, tab_top = st.tabs([
    f"✈️ {away_full.split()[-1]} ({away_abbr})",
    f"🏠 {home_full.split()[-1]} ({home_abbr})",
    "⭐ Top Props",
])

def _sort_pts(p):
    logs = load_player_logs(p["id"], limit=5)
    return safe_avg([g.get("points",0) for g in logs])

away_pl = sorted([p for p in players if p.get("team")==away_abbr], key=_sort_pts, reverse=True)
home_pl = sorted([p for p in players if p.get("team")==home_abbr], key=_sort_pts, reverse=True)

with tab_away:
    if not away_pl:
        st.info(f"No {away_abbr} player data. Go to **Data Sync → Fetch NBA Players**.")
    for p in away_pl[:12]:
        render_player_card(p, game, home_abbr)

with tab_home:
    if not home_pl:
        st.info(f"No {home_abbr} player data. Go to **Data Sync → Fetch NBA Players**.")
    for p in home_pl[:12]:
        render_player_card(p, game, away_abbr)

with tab_top:
    st.subheader("⭐ Best Props Today — sorted by over hit rate")
    rows = []
    for p in players:
        logs = load_player_logs(p["id"], limit=10)
        if not logs: continue
        pts  = [g.get("points",0) for g in logs]
        avg  = safe_avg(pts)
        if avg < 6: continue
        line = compute_prop_line(pts)
        hr   = hit_rate(pts, line)
        opp  = home_abbr if p.get("team")==away_abbr else away_abbr
        mh   = matchup_history(logs, opp, "points")
        rows.append({
            "Player":   p.get("name","?"),
            "Team":     p.get("team",""),
            "Pos":      p.get("position",""),
            "Prop":     f"O{line} PTS",
            "Over %":   f"{hr['over']:.0f}%",
            "Avg":      avg,
            "L5 Avg":   safe_avg(pts,5),
            f"vs {opp}": mh.get("avg","—"),
            "Streak":   f"{hr['streak']} {'O' if hr['streak_dir']=='O' else 'U'}" if hr["streak"]>=2 else "—",
        })
    rows.sort(key=lambda x: float(x["Over %"].rstrip("%")), reverse=True)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("Fetch player data first via Data Sync.")
