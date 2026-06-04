"""
APEX ANALYTICS - Data Sync
Odds fetching is locked behind admin password.
Player data (free APIs) is open to all.
"""
import sys
from pathlib import Path
import streamlit as st
import subprocess
import os

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from dashboard.auth import require_admin, admin_lock_button
from dashboard.mobile_utils import inject_mobile_css

inject_mobile_css()
admin_lock_button()

st.title("🔄 Data Sync")
st.caption("Fetch live odds, player stats, and manage the database.")


def run_worker(script_name: str, args: list, timeout: int = 300):
    script_path = str(project_root / "workers" / script_name)
    cmd = [sys.executable, script_path] + args
    with st.spinner(f"Running {script_name} {' '.join(args)}…"):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    cwd=str(project_root), timeout=timeout)
            if result.returncode == 0:
                st.success("Done!")
                if result.stdout.strip():
                    with st.expander("View output"):
                        st.code(result.stdout[-3000:])
            else:
                st.error("Worker returned an error:")
                st.code((result.stderr or result.stdout)[-2000:])
        except subprocess.TimeoutExpired:
            st.error(f"Timed out after {timeout}s.")
        except Exception as e:
            st.error(str(e))
    st.cache_data.clear()


# ─────────────────────────────────────────────────────────────
# DB STATUS  (always visible)
# ─────────────────────────────────────────────────────────────
st.subheader("📊 Database Status")
try:
    from datetime import datetime, timezone
    games   = supabase.table("games").select("id,sport").execute().data or []
    players = supabase.table("players").select("id,sport").limit(9999).execute().data or []
    # Use Postgres count trick via head=True for large tables
    try:
        logs_resp = supabase.table("player_game_stats").select("id", count="exact").limit(1).execute()
        log_count = logs_resp.count or 0
    except Exception:
        log_count = len(supabase.table("player_game_stats").select("id").limit(9999).execute().data or [])
    try:
        odds_count_resp = supabase.table("odds_snapshots").select("id", count="exact").limit(1).execute()
        odds_count = odds_count_resp.count or 0
    except Exception:
        odds_count = 0
    logs    = [{"id": i} for i in range(log_count)]   # dummy list for len()
    odds_latest = (supabase.table("odds_snapshots")
                   .select("created_at").order("created_at", desc=True)
                   .limit(1).execute().data or [])

    from collections import Counter
    g_cnt = Counter(g["sport"] for g in games)
    p_cnt = Counter(p.get("sport", "?") for p in players)

    age_str = "—"
    if odds_latest:
        ts  = datetime.fromisoformat(odds_latest[0]["created_at"].replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
        age_str = f"{age:.1f}h ago"
        if age > 12:
            st.warning(f"⏰ Odds are **{age:.0f}h old** — fetch fresh data below.")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Games",      len(games))
    c2.metric("MLB/NBA/NHL/NFL", f"{g_cnt.get('MLB',0)}/{g_cnt.get('NBA',0)}/{g_cnt.get('NHL',0)}/{g_cnt.get('NFL',0)}")
    c3.metric("Players",    len(players))
    c4.metric("Game Logs",  f"{log_count:,}")
    c5.metric("Odds Age",   age_str)
except Exception as e:
    st.error(f"Cannot read database: {e}")

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# PLAYER DATA  (free — no password needed)
# ─────────────────────────────────────────────────────────────
st.subheader("👥 Player Data  —  Free, no API credits")
st.caption("Fetches rosters, headshots, and last 15 game logs from NBA Stats API, MLB StatsAPI, and NHL API.")

pc1, pc2, pc3, pc4 = st.columns(4)
with pc1:
    if st.button("🏀 NBA Players", use_container_width=True):
        run_worker("fetch_live_players.py", ["--sport", "nba"], timeout=300)
with pc2:
    if st.button("⚾ MLB Players", use_container_width=True):
        run_worker("fetch_live_players.py", ["--sport", "mlb"], timeout=300)
with pc3:
    if st.button("🏒 NHL Players", use_container_width=True):
        run_worker("fetch_live_players.py", ["--sport", "nhl"], timeout=180)
with pc4:
    if st.button("🔄 All Players", use_container_width=True, type="primary"):
        run_worker("fetch_live_players.py", ["--sport", "all"], timeout=600)

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# ODDS FETCH  —  PASSWORD GATED
# ─────────────────────────────────────────────────────────────
st.subheader("📡 Live Odds Fetch  —  🔐 Admin Only")
st.caption("Each fetch costs ~1 API credit (500/month free tier). Fetching all sports costs ~3 credits.")

if require_admin("Enter password to unlock odds fetching"):

    oc1, oc2, oc3 = st.columns(3)
    with oc1:
        if st.button("⚾ Fetch MLB Odds", use_container_width=True):
            run_worker("fetch_all_odds.py", ["--sport", "mlb"])
    with oc2:
        if st.button("🏀 Fetch NBA Odds", use_container_width=True):
            run_worker("fetch_all_odds.py", ["--sport", "nba"])
    with oc3:
        if st.button("🏒 Fetch NHL Odds", use_container_width=True):
            run_worker("fetch_all_odds.py", ["--sport", "nhl"])

    if st.button("🔄 Fetch All Sports (3 credits)", use_container_width=True, type="primary"):
        run_worker("fetch_all_odds.py", ["--sport", "all"])

    # API credit check
    st.markdown("---")
    if st.button("Check API Credits Remaining"):
        import requests as req_lib
        odds_key = os.getenv("ODDS_API_KEY", "")
        if not odds_key:
            try:
                odds_key = st.secrets.get("ODDS_API_KEY", "")
            except Exception:
                pass
        if odds_key:
            try:
                r = req_lib.get(
                    f"https://api.the-odds-api.com/v4/sports/?apiKey={odds_key}",
                    timeout=10)
                remaining = r.headers.get("x-requests-remaining", "?")
                used      = r.headers.get("x-requests-used", "?")
                st.info(f"✅ Credits remaining: **{remaining}**  |  Used this month: **{used}**")
            except Exception as e:
                st.error(f"Could not reach Odds API: {e}")
        else:
            st.warning("ODDS_API_KEY not configured.")

    st.markdown("---")

    # Props pipeline (also admin-gated)
    st.subheader("🎯 Props Pipeline")
    st.caption("Fetch book prop odds → build projections → build ranked value snapshots.")
    pp1, pp2, pp3 = st.columns(3)
    with pp1:
        if st.button("Fetch NBA Props", use_container_width=True):
            run_worker("fetch_player_prop_odds.py", ["--sport", "nba"])
    with pp2:
        if st.button("Fetch MLB Props", use_container_width=True):
            run_worker("fetch_player_prop_odds.py", ["--sport", "mlb"])
    with pp3:
        if st.button("Full Props Pipeline", use_container_width=True, type="primary"):
            run_worker("fetch_player_prop_odds.py", ["--sport", "all"])
            run_worker("build_prop_feed_snapshots.py",
                       ["--sport", "NBA", "--hours", "48", "--limit", "1200"])
            run_worker("build_prop_feed_snapshots.py",
                       ["--sport", "MLB", "--hours", "48", "--limit", "1200"])

st.markdown("---")
st.caption("Local URL (same Wi-Fi): shown in the sidebar.")
