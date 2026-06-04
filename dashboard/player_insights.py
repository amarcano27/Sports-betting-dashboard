"""
Player Insights
Focused, beginner-friendly player page with clear value signals.
"""
import sys
from pathlib import Path
from datetime import datetime
import json
import streamlit as st
import pandas as pd

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase


def _fmt_time(ts: str) -> str:
    try:
        t = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return t.strftime("%b %d %I:%M %p")
    except Exception:
        return "TBD"


@st.cache_data(ttl=120)
def load_players():
    return (
        supabase.table("players")
        .select("id,name,team,position,sport,external_id,raw_data")
        .order("name")
        .limit(1000)
        .execute()
        .data
        or []
    )


@st.cache_data(ttl=120)
def load_recent_stats(player_id: str):
    return (
        supabase.table("player_game_stats")
        .select("*")
        .eq("player_id", player_id)
        .order("date", desc=True)
        .limit(20)
        .execute()
        .data
        or []
    )


@st.cache_data(ttl=120)
def load_props(player_id: str):
    try:
        return (
            supabase.table("player_prop_odds")
            .select("*")
            .eq("player_id", player_id)
            .order("created_at", desc=True)
            .limit(100)
            .execute()
            .data
            or []
        )
    except Exception:
        return []


def _headshot(player: dict) -> str | None:
    raw = player.get("raw_data", {})
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = {}
    url = raw.get("headshot_url")
    if url:
        return url
    ext_id = player.get("external_id")
    if ext_id and str(player.get("sport", "")).upper() == "NBA":
        return f"https://cdn.nba.com/headshots/nba/latest/1040x760/{ext_id}.png"
    return None


st.title("🔎 Player Insights")
st.caption("Select a player to see recent form + best available props.")

players = load_players()
if not players:
    st.warning("No players found in database.")
    st.stop()

default_idx = 0
if "selected_player_id" in st.session_state:
    for i, p in enumerate(players):
        if p["id"] == st.session_state["selected_player_id"]:
            default_idx = i
            break

player_idx = st.selectbox(
    "Player",
    range(len(players)),
    format_func=lambda i: f"{players[i]['name']} ({players[i].get('team','N/A')})",
    index=default_idx,
)
player = players[player_idx]
st.session_state["selected_player_id"] = player["id"]
st.session_state["selected_player_name"] = player["name"]
st.session_state["selected_player_team"] = player.get("team")

top1, top2 = st.columns([1, 3])
with top1:
    hs = _headshot(player)
    if hs:
        st.image(hs, width=120)
with top2:
    st.markdown(f"### {player['name']}")
    st.caption(f"{player.get('sport','N/A')} · {player.get('team','N/A')} · {player.get('position','N/A')}")

stats = load_recent_stats(player["id"])
props = load_props(player["id"])

st.markdown("#### Recent Game Log")
if stats:
    cols = ["date", "opponent", "minutes_played", "points", "rebounds", "assists", "three_pointers_made", "steals", "blocks", "turnovers"]
    cols = [c for c in cols if c in stats[0]]
    df = pd.DataFrame(stats)[cols]
    st.dataframe(df, width="stretch", hide_index=True)
else:
    st.info("No recent game stats found.")

st.markdown("#### Best Available Props")
if not props:
    st.info("No player props available yet for this player.")
else:
    grouped = {}
    for p in props:
        key = (p.get("prop_type"), p.get("line"))
        if key not in grouped:
            grouped[key] = dict(p)
        else:
            if p.get("over_price") and (not grouped[key].get("over_price") or p["over_price"] > grouped[key]["over_price"]):
                grouped[key]["over_price"] = p["over_price"]
                grouped[key]["book"] = p.get("book")
            if p.get("under_price") and (not grouped[key].get("under_price") or p["under_price"] > grouped[key]["under_price"]):
                grouped[key]["under_price"] = p["under_price"]
                grouped[key]["book"] = p.get("book")

    rows = []
    for (ptype, line), g in grouped.items():
        rows.append(
            {
                "Prop": str(ptype).replace("_", " ").title(),
                "Line": line,
                "Best Over": f"+{int(g['over_price'])}" if isinstance(g.get("over_price"), int) and g["over_price"] > 0 else g.get("over_price"),
                "Best Under": f"+{int(g['under_price'])}" if isinstance(g.get("under_price"), int) and g["under_price"] > 0 else g.get("under_price"),
                "Book": g.get("book"),
                "Updated": _fmt_time(g.get("created_at", "")),
            }
        )
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
