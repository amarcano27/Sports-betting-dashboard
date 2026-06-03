"""
HOME — Command Center
All sports at a glance: today's games, top plays by edge, plus-money feed,
quick-access to fetch latest data.
"""
import sys, json
from pathlib import Path
import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from collections import Counter

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase, DB_MODE
from utils.model import (
    build_game_model, devig, american_to_prob,
    REC_COLORS, MIN_EDGE_PCT,
)
from dashboard.mlb_page import find_pitcher
from dashboard.premium_styles import color


@st.cache_data(ttl=60)
def load_all_games():
    return supabase.table("games").select("*").order("start_time").execute().data or []

@st.cache_data(ttl=60)
def load_odds_for_game(game_id: str):
    return supabase.table("odds_snapshots").select("*").eq("game_id", game_id).execute().data or []

@st.cache_data(ttl=120)
def load_player_count():
    r = supabase.table("players").select("id").limit(9999).execute().data or []
    return len(r)

@st.cache_data(ttl=120)
def load_game_log_count():
    r = supabase.table("player_game_stats").select("id").limit(99999).execute().data or []
    return len(r)


def fmt_time(iso_str: str) -> str:
    try:
        t = datetime.fromisoformat(iso_str.replace("Z","+00:00"))
        return t.strftime("%I:%M %p")
    except Exception:
        return "TBD"


def best_ml(odds_rows, team):
    m = [r for r in odds_rows if r.get("market_type")=="h2h" and r.get("market_label")==team]
    if not m: return None
    return int(max(m, key=lambda r: r.get("price") or -9999).get("price", 0))


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
st.title("📊 Command Center")
st.caption(f"Live · {DB_MODE.upper()} backend · {datetime.now().strftime('%b %d %Y %I:%M %p')}")

games = load_all_games()
counts = Counter(g["sport"] for g in games)
player_count = load_player_count()
log_count    = load_game_log_count()
total_odds   = len(supabase.table("odds_snapshots").select("id").limit(99999).execute().data or [])

# ── Metrics strip ─────────────────────────────────────────────
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Total Games",    len(games))
m2.metric("⚾ MLB",          counts.get("MLB", 0))
m3.metric("🏀 NBA",          counts.get("NBA", 0))
m4.metric("🏒 NHL",          counts.get("NHL", 0))
m5.metric("Players in DB",  player_count)
m6.metric("Game Logs",      f"{log_count:,}")

st.markdown("---")

# ── Top edge plays across all sports ─────────────────────────
st.subheader("🎯 Top Plays Right Now")
st.caption("Edge = Elo+FIP model prob − devigged market prob (MLB). Devig-only for other sports.")

top_plays = []
for g in games:
    sport = g.get("sport", "?")
    rows  = load_odds_for_game(g["id"])
    away, home = g["away_team"], g["home_team"]
    a_ml = best_ml(rows, away)
    h_ml = best_ml(rows, home)
    if not a_ml or not h_ml:
        continue

    dv_a, dv_h = devig(a_ml, h_ml)

    if sport == "MLB":
        apn, apd = find_pitcher(away)
        hpn, hpd = find_pitcher(home)
        if apd and hpd:
            gm = build_game_model(away, home, apd["fip"], hpd["fip"], a_ml, h_ml)
            best_e = max(gm.away_edge, gm.home_edge)
            best_t = away if gm.away_edge >= gm.home_edge else home
            best_m = a_ml if gm.away_edge >= gm.home_edge else h_ml
            best_l = gm.away_rec if gm.away_edge >= gm.home_edge else gm.home_rec
            model_p = gm.model_away_prob if gm.away_edge >= gm.home_edge else gm.model_home_prob
            dv_p    = dv_a if gm.away_edge >= gm.home_edge else dv_h
        else:
            # fallback to devig only
            if dv_a > dv_h:
                best_e, best_t, best_m = (dv_a - american_to_prob(a_ml)) * 100, away, a_ml
            else:
                best_e, best_t, best_m = (dv_h - american_to_prob(h_ml)) * 100, home, h_ml
            best_l = "PLAY" if best_e >= 2 else "LEAN"
            model_p = dv_a
            dv_p    = dv_a
    else:
        # Non-MLB: use devig only
        if dv_a > american_to_prob(a_ml):
            best_e, best_t, best_m = (dv_a - american_to_prob(a_ml)) * 100, away, a_ml
            dv_p = dv_a
        else:
            best_e, best_t, best_m = (dv_h - american_to_prob(h_ml)) * 100, home, h_ml
            dv_p = dv_h
        best_l = "PLAY" if best_e >= 2 else "LEAN"
        model_p = dv_p

    if best_e >= 1.0:
        try:
            t = datetime.fromisoformat(g["start_time"].replace("Z","+00:00"))
            time_str = t.strftime("%I:%M %p ET")
        except Exception:
            time_str = "TBD"

        top_plays.append({
            "sport":    sport,
            "matchup":  f"{away.split()[-1]} @ {home.split()[-1]}",
            "team":     best_t,
            "ml":       best_m,
            "ml_str":   f"+{best_m}" if best_m > 0 else str(best_m),
            "edge":     best_e,
            "label":    best_l,
            "time":     time_str,
            "model_p":  model_p,
            "dv_p":     dv_p,
        })

top_plays.sort(key=lambda x: -x["edge"])

SPORT_ICON = {"MLB":"⚾","NBA":"🏀","NHL":"🏒","NFL":"🏈","PGA":"⛳"}

if top_plays:
    # Top 4 as hero cards
    hero = top_plays[:4]
    cols = st.columns(len(hero))
    for ci, p in enumerate(hero):
        with cols[ci]:
            rc    = REC_COLORS.get(p["label"], color("text_primary"))
            mlc   = color("green") if p["ml"] > 0 else color("text_primary")
            sport_icon = SPORT_ICON.get(p["sport"],"🏆")
            st.markdown(f"""
<div style="background: #121212; border: 1px solid {rc}; border-radius: 16px; padding: 16px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5); transition: transform 0.2s;">
  <div style="font-size: 11px; color: #737373; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;">{sport_icon} {p['sport']}</div>
  <div style="font-size: 13px; color: #a3a3a3; margin: 6px 0; font-weight: 600;">{p['matchup']}</div>
  <div style="font-size: 15px; font-weight: 800; color: #ffffff; margin-bottom: 4px;">
    {p['team'].split()[-1]}
  </div>
  <div style="font-family: 'JetBrains Mono', monospace; font-size: 32px; font-weight: 800; color: {mlc};">
    {p['ml_str']}
  </div>
  <div style="margin-top: 8px; display: inline-block; background: {rc}22; color: {rc}; border: 1px solid {rc}44; padding: 4px 12px; border-radius: 6px; font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px;">{p['label']}</div>
  <div style="font-family: 'JetBrains Mono', monospace; font-size: 14px; color: #10b981; font-weight: 700; margin-top: 8px;">Edge +{p['edge']:.1f}%</div>
  <div style="font-size: 11px; color: #525252; margin-top: 6px; font-weight: 600;">{p['time']}</div>
</div>
""", unsafe_allow_html=True)

    # Rest as compact table
    if len(top_plays) > 4:
        st.markdown("##### All Plays")
        tbl = []
        for p in top_plays[4:]:
            tbl.append({
                "Sport":   p["sport"],
                "Matchup": p["matchup"],
                "Play":    f"{p['team'].split()[-1]} {p['ml_str']}",
                "Edge":    f"+{p['edge']:.1f}%",
                "Label":   p["label"],
                "Time":    p["time"],
            })
        st.dataframe(pd.DataFrame(tbl), width="stretch", hide_index=True,
            column_config={
                "Sport":   st.column_config.TextColumn(width=70),
                "Matchup": st.column_config.TextColumn(width=160),
                "Play":    st.column_config.TextColumn(width=130),
                "Edge":    st.column_config.TextColumn(width=80),
                "Label":   st.column_config.TextColumn(width=100),
                "Time":    st.column_config.TextColumn(width=100),
            })
else:
    st.info("No plays with edge ≥1% found. Fetch fresh odds data below.")

st.markdown("---")

# ── Today's full schedule ─────────────────────────────────────
st.subheader("📋 Today's Schedule")
if games:
    sched_rows = []
    for g in sorted(games, key=lambda x: x.get("start_time","")):
        rows  = load_odds_for_game(g["id"])
        a_ml  = best_ml(rows, g["away_team"])
        h_ml  = best_ml(rows, g["home_team"])
        a_str = (f"+{a_ml}" if a_ml > 0 else str(a_ml)) if a_ml else "—"
        h_str = (f"+{h_ml}" if h_ml > 0 else str(h_ml)) if h_ml else "—"
        sched_rows.append({
            "Sport":         g["sport"],
            "Time":          fmt_time(g.get("start_time","")),
            "Away":          g["away_team"],
            "Away ML":       a_str,
            "Home":          g["home_team"],
            "Home ML":       h_str,
        })
    df = pd.DataFrame(sched_rows)
    st.dataframe(df, width="stretch", hide_index=True,
        column_config={
            "Sport":    st.column_config.TextColumn(width=70),
            "Time":     st.column_config.TextColumn(width=100),
            "Away":     st.column_config.TextColumn(width=200),
            "Away ML":  st.column_config.TextColumn(width=90),
            "Home":     st.column_config.TextColumn(width=200),
            "Home ML":  st.column_config.TextColumn(width=90),
        })
else:
    st.warning("No games loaded. Use quick-fetch below.")

st.markdown("---")

# ── Quick data fetch ──────────────────────────────────────────
st.subheader("🔄 Quick Data Refresh")
st.caption(f"API budget: ~{500 - total_odds // 55} credits remaining (est). Fetching all sports costs 3 credits.")
import os
has_key = bool(os.getenv("ODDS_API_KEY","").strip()) and os.getenv("ODDS_API_KEY","") != "PASTE_YOUR_KEY_HERE"

fc1, fc2, fc3, fc4 = st.columns(4)
with fc1:
    if st.button("⚾ Fetch MLB", disabled=not has_key, width="stretch"):
        import subprocess
        with st.spinner("Fetching MLB odds..."):
            r = subprocess.run([sys.executable,"workers/fetch_all_odds.py","--sport","mlb"],
                               capture_output=True, text=True, cwd=str(project_root))
            st.toast("MLB updated!" if r.returncode == 0 else f"Error: {r.stderr[-200:]}")
            st.cache_data.clear()
with fc2:
    if st.button("🏀 Fetch NBA", disabled=not has_key, width="stretch"):
        import subprocess
        with st.spinner("Fetching NBA odds..."):
            r = subprocess.run([sys.executable,"workers/fetch_all_odds.py","--sport","nba"],
                               capture_output=True, text=True, cwd=str(project_root))
            st.toast("NBA updated!" if r.returncode == 0 else f"Error: {r.stderr[-200:]}")
            st.cache_data.clear()
with fc3:
    if st.button("🏒 Fetch NHL", disabled=not has_key, width="stretch"):
        import subprocess
        with st.spinner("Fetching NHL odds..."):
            r = subprocess.run([sys.executable,"workers/fetch_all_odds.py","--sport","nhl"],
                               capture_output=True, text=True, cwd=str(project_root))
            st.toast("NHL updated!" if r.returncode == 0 else f"Error: {r.stderr[-200:]}")
            st.cache_data.clear()
with fc4:
    if st.button("👥 Fetch Players", width="stretch"):
        import subprocess
        with st.spinner("Fetching player stats (free, no credits)..."):
            r = subprocess.run([sys.executable,"workers/fetch_live_players.py","--sport","all"],
                               capture_output=True, text=True, cwd=str(project_root), timeout=300)
            st.toast("Players updated!" if r.returncode == 0 else "Error fetching players")
            st.cache_data.clear()

if not has_key:
    st.caption("⚠️ Add ODDS_API_KEY to .env to enable live odds fetching. Player data fetch works without a key.")
