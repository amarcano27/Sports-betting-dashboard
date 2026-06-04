"""
APEX ANALYTICS - Injury Feed
Free ESPN hidden API — no key required.
Shows today's injury/status report for MLB, NBA, NHL.
"""
import sys
from pathlib import Path
import streamlit as st
import requests
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dashboard.premium_styles import TOKENS
from dashboard.mobile_utils import inject_mobile_css

inject_mobile_css()

ESPN_ENDPOINTS = {
    "MLB": "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/injuries",
    "NBA": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries",
    "NHL": "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/injuries",
    "NFL": "https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries",
}

STATUS_COLOR = {
    "Out":           TOKENS["red"],
    "Questionable":  TOKENS["amber"],
    "Doubtful":      TOKENS["red"],
    "Day-To-Day":    TOKENS["amber"],
    "IR":            TOKENS["red"],
    "Active":        TOKENS["green"],
    "Probable":      TOKENS["green"],
}

@st.cache_data(ttl=1800)   # 30-minute cache
def fetch_injuries(sport: str) -> list[dict]:
    url = ESPN_ENDPOINTS.get(sport)
    if not url:
        return []
    try:
        r = requests.get(url, timeout=12,
                         headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        data = r.json()
        injuries = []
        for team_entry in data.get("injuries", []):
            team_name = team_entry.get("team", {}).get("displayName", "?")
            team_abbr = team_entry.get("team", {}).get("abbreviation", "")
            for inj in team_entry.get("injuries", []):
                athlete = inj.get("athlete", {})
                status  = inj.get("status", "Unknown")
                desc    = inj.get("longComment") or inj.get("shortComment") or "No details"
                injuries.append({
                    "team":     team_name,
                    "abbr":     team_abbr,
                    "player":   athlete.get("displayName", "?"),
                    "position": athlete.get("position", {}).get("abbreviation", ""),
                    "status":   status,
                    "details":  desc,
                    "headshot": athlete.get("headshot", {}).get("href", ""),
                })
        return injuries
    except Exception as e:
        return []


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
st.title("🏥 Injury Report")
st.caption("ESPN injury feed · Updates every 30 min · Free, no API key")

sport = st.selectbox("Sport", ["MLB","NBA","NHL","NFL"], label_visibility="collapsed")

injuries = fetch_injuries(sport)

if not injuries:
    st.info(f"No injury data for {sport} right now, or ESPN API is temporarily unavailable.")
    st.stop()

# Filter controls
c1, c2 = st.columns(2)
status_filter = c1.multiselect("Status filter",
    options=["Out","Questionable","Doubtful","Day-To-Day","IR","Probable","Active"],
    default=["Out","Questionable","Doubtful","Day-To-Day","IR"])
search = c2.text_input("Search player / team", placeholder="e.g. Springer, Yankees")

filtered = [i for i in injuries
            if (not status_filter or i["status"] in status_filter)
            and (not search or search.lower() in i["player"].lower()
                 or search.lower() in i["team"].lower())]

st.caption(f"**{len(filtered)}** players shown of {len(injuries)} total")

# Group by team
from collections import defaultdict
by_team = defaultdict(list)
for inj in filtered:
    by_team[inj["team"]].append(inj)

for team_name, players in sorted(by_team.items()):
    with st.expander(f"**{team_name}** — {len(players)} player(s)"):
        for p in players:
            sc = STATUS_COLOR.get(p["status"], TOKENS["text_muted"])
            cols = st.columns([1,4])
            with cols[0]:
                if p.get("headshot"):
                    st.image(p["headshot"], width=56)
                else:
                    st.markdown(f"""
<div style="width:52px;height:52px;background:{TOKENS['bg_panel_2']};border-radius:50%;
            display:flex;align-items:center;justify-content:center;
            font-weight:800;color:{TOKENS['text_secondary']};font-size:18px">
  {p['player'][0]}
</div>""", unsafe_allow_html=True)
            with cols[1]:
                st.markdown(f"""
<div style="padding:4px 0">
  <div style="display:flex;gap:12px;align-items:center">
    <span style="font-weight:800;color:{TOKENS['text_primary']};font-size:15px">{p['player']}</span>
    <span style="font-size:11px;color:{TOKENS['text_muted']}">{p['position']}</span>
    <span style="font-size:11px;font-weight:700;color:{sc};background:{sc}22;
                 padding:2px 8px;border-radius:4px">{p['status']}</span>
  </div>
  <div style="font-size:12px;color:{TOKENS['text_muted']};margin-top:4px">{p['details'][:120]}</div>
</div>""", unsafe_allow_html=True)
