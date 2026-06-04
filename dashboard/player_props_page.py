"""
Prop Matrix
Popular players with real book lines and blended projections.
"""
import json
import sys
from pathlib import Path
from collections import Counter

import pandas as pd
import streamlit as st
from rapidfuzz import process

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from dashboard.ui_components import render_prop_card

PREFERRED_BOOKS = ["Pinnacle", "Bovada", "DraftKings", "FanDuel", "BetMGM", "Caesars", "bet365"]
BOOK_WEIGHTS = {"Pinnacle": 1.35, "Bovada": 1.2, "DraftKings": 1.1, "FanDuel": 1.1, "BetMGM": 1.0, "Caesars": 1.0, "bet365": 1.0}


def _norm_prop_type(prop_type: str) -> str:
    p = (prop_type or "").strip().lower()
    mapping = {
        "player_points": "points",
        "player_rebounds": "rebounds",
        "player_assists": "assists",
        "player_threes": "threes",
        "player_steals": "steals",
        "player_blocks": "blocks",
        "player_turnovers": "turnovers",
        "batter_hits": "hits",
        "batter_total_bases": "total_bases",
        "pitcher_strikeouts": "pitcher_strikeouts",
    }
    return mapping.get(p, p)


def _prop_value(stat: dict, prop_type: str):
    keys = {
        "points": ["points"],
        "rebounds": ["rebounds"],
        "assists": ["assists"],
        "threes": ["three_pointers_made", "threes"],
        "steals": ["steals"],
        "blocks": ["blocks"],
        "turnovers": ["turnovers"],
        "hits": ["hits"],
        "total_bases": ["total_bases"],
        "pitcher_strikeouts": ["strikeouts", "pitcher_strikeouts"],
    }.get(prop_type, [prop_type])
    for k in keys:
        v = stat.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    return None


def _fmt_odds(v):
    if v is None:
        return None
    try:
        iv = int(v)
        return f"+{iv}" if iv > 0 else str(iv)
    except Exception:
        return str(v)


def _to_obj(v):
    if isinstance(v, dict):
        return v
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return {}
    return {}


@st.cache_data(ttl=180)
def load_players(sport: str):
    query = supabase.table("players").select("id,name,team,external_id,raw_data,sport").order("name").limit(2500)
    if sport != "All":
        query = query.eq("sport", sport)
    return query.execute().data or []


@st.cache_data(ttl=180)
def load_prop_odds():
    return (
        supabase.table("player_prop_odds")
        .select("player_id,game_id,book,prop_type,line,over_price,under_price,created_at")
        .order("created_at", desc=True)
        .limit(10000)
        .execute()
        .data
        or []
    )


@st.cache_data(ttl=180)
def load_player_stats(player_id: str, limit: int = 40):
    return (
        supabase.table("player_game_stats")
        .select("*")
        .eq("player_id", player_id)
        .order("date", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )


def get_headshot(player: dict):
    raw = _to_obj(player.get("raw_data", {}))
    if raw.get("headshot_url"):
        return raw["headshot_url"]
    ext_id = player.get("external_id")
    if ext_id and "nba" in str(player.get("sport", "")).lower():
        return f"https://cdn.nba.com/headshots/nba/latest/1040x760/{ext_id}.png"
    return None


def build_popular_players(players, odds_rows, top_n):
    player_map = {p["id"]: p for p in players if p.get("id")}
    counts = Counter()
    for r in odds_rows:
        pid = r.get("player_id")
        if pid in player_map:
            counts[pid] += 1
    ranked = [player_map[pid] for pid, _ in counts.most_common(top_n)]
    return ranked if ranked else players[:top_n]


def market_consensus_line(rows):
    by_book = {}
    for r in rows:
        book = r.get("book")
        line = r.get("line")
        if book and line is not None and book not in by_book:
            by_book[book] = float(line)
    if not by_book:
        return None, 0
    weighted = sum(v * BOOK_WEIGHTS.get(b, 0.9) for b, v in by_book.items())
    total = sum(BOOK_WEIGHTS.get(b, 0.9) for b in by_book.keys())
    return round(weighted / total, 2), len(by_book)


def projection_for_type(stats, prop_type, rows_for_type):
    values = [_prop_value(s, prop_type) for s in stats]
    values = [v for v in values if v is not None]
    recent = values[:10]
    season = values[:30]
    recent_avg = (sum(recent) / len(recent)) if recent else None
    season_avg = (sum(season) / len(season)) if season else None
    market_line, book_count = market_consensus_line(rows_for_type)

    if recent_avg is not None and season_avg is not None and market_line is not None:
        return round((0.50 * recent_avg) + (0.25 * season_avg) + (0.25 * market_line), 2), f"blend(r+s+m:{book_count}b)"
    if recent_avg is not None and market_line is not None:
        return round((0.65 * recent_avg) + (0.35 * market_line), 2), f"blend(r+m:{book_count}b)"
    if recent_avg is not None and season_avg is not None:
        return round((0.70 * recent_avg) + (0.30 * season_avg), 2), "blend(r+s)"
    if recent_avg is not None:
        return round(recent_avg, 2), "recent"
    if market_line is not None:
        return market_line, f"market:{book_count}b"
    return None, "none"


def hit_rates_for_line(stats, prop_type, line):
    values = [_prop_value(s, prop_type) for s in stats]
    values = [v for v in values if v is not None]
    if not values:
        return None, None
    over = round((sum(1 for v in values if v > line) / len(values)) * 100, 1)
    under = round((sum(1 for v in values if v < line) / len(values)) * 100, 1)
    return over, under


def build_line_matrix(player_rows, selected_books, stats):
    filtered = [r for r in player_rows if not selected_books or r.get("book") in selected_books]
    by_type = {}
    for r in filtered:
        ptype = _norm_prop_type(r.get("prop_type"))
        by_type.setdefault(ptype, []).append(r)

    grouped = {}
    for ptype, rows_for_type in by_type.items():
        proj, proj_src = projection_for_type(stats, ptype, rows_for_type)
        for r in rows_for_type:
            line = r.get("line")
            if line is None:
                continue
            key = (ptype, float(line))
            cur = grouped.get(key)
            if cur is None:
                grouped[key] = {
                    "Prop": ptype.replace("_", " ").title(),
                    "Line": float(line),
                    "Projection": proj,
                    "Projection Source": proj_src,
                    "Best Over": r.get("over_price"),
                    "Over Book": r.get("book"),
                    "Best Under": r.get("under_price"),
                    "Under Book": r.get("book"),
                }
            else:
                ov = r.get("over_price")
                un = r.get("under_price")
                if ov is not None and (cur["Best Over"] is None or ov > cur["Best Over"]):
                    cur["Best Over"] = ov
                    cur["Over Book"] = r.get("book")
                if un is not None and (cur["Best Under"] is None or un > cur["Best Under"]):
                    cur["Best Under"] = un
                    cur["Under Book"] = r.get("book")

    matrix = []
    for (ptype, line), rec in grouped.items():
        proj = rec.get("Projection")
        if proj is None or line <= 0:
            rec["Edge Side"] = "N/A"
            rec["Edge %"] = 0.0
        else:
            over_edge = ((float(proj) - float(line)) / float(line)) * 100
            under_edge = -over_edge
            if over_edge >= under_edge:
                rec["Edge Side"] = "Over"
                rec["Edge %"] = round(over_edge, 2)
            else:
                rec["Edge Side"] = "Under"
                rec["Edge %"] = round(under_edge, 2)
        hit_over, hit_under = hit_rates_for_line(stats, ptype, line)
        rec["Hit Over %"] = hit_over
        rec["Hit Under %"] = hit_under
        rec["Best Over"] = _fmt_odds(rec.get("Best Over"))
        rec["Best Under"] = _fmt_odds(rec.get("Best Under"))
        matrix.append(rec)

    matrix.sort(key=lambda x: -(x.get("Edge %") or 0))
    return matrix


st.title("🎯 Prop Matrix")
st.caption("Popular players first, real lines only, blended projection sources.")

f1, f2, f3 = st.columns([1, 2, 1])
with f1:
    sport_filter = st.selectbox("Sport", ["All", "NBA", "MLB", "NHL", "NFL", "Esports"], index=1)
with f2:
    search_query = st.text_input("Search (optional)", placeholder="Type player name if you want...")
with f3:
    show_players = st.slider("Popular Players", 6, 32, 14, 2)

players = load_players(sport_filter)
odds_rows = load_prop_odds()

if sport_filter != "All":
    players = [p for p in players if str(p.get("sport", "")).upper() == sport_filter]
player_ids = {p.get("id") for p in players}
odds_rows = [r for r in odds_rows if r.get("player_id") in player_ids]

if not odds_rows:
    st.warning("No player prop odds found yet. Run Data Sync -> Fetch NBA/MLB Props.")
    st.stop()

popular_players = build_popular_players(players, odds_rows, show_players)
if search_query and len(search_query) >= 2:
    search_space = [p["name"] for p in players]
    matches = process.extract(search_query, search_space, limit=10, score_cutoff=70)
    if matches:
        popular_players = [next(p for p in players if p["name"] == name) for name, _, _ in matches]

st.markdown("### Popular Players")
tiles = st.columns(4)
for idx, p in enumerate(popular_players):
    with tiles[idx % 4]:
        if st.button(f"{p['name']}\n{p.get('team') or ''}", key=f"popular_player_{p['id']}", width="stretch"):
            st.session_state.selected_prop_player = p
            st.rerun()

selected = st.session_state.get("selected_prop_player")
if not selected or selected.get("id") not in player_ids:
    selected = popular_players[0]
    st.session_state.selected_prop_player = selected

st.markdown("<hr style='border-color: #1E293B;'>", unsafe_allow_html=True)
st.subheader(f"All Lines + Projections for {selected['name']}")

player_rows = [r for r in odds_rows if r.get("player_id") == selected["id"]]
available_books = sorted({r.get("book") for r in player_rows if r.get("book")})
default_books = [b for b in PREFERRED_BOOKS if b in available_books] or available_books[:4]
selected_books = st.multiselect("Books", available_books, default=default_books)

stats = load_player_stats(selected["id"], limit=40)
matrix_rows = build_line_matrix(player_rows, selected_books, stats)
if not matrix_rows:
    st.info("No lines found for selected books.")
    st.stop()

matrix_df = pd.DataFrame(matrix_rows)
st.dataframe(matrix_df, width="stretch", hide_index=True)

st.markdown("### Top Edges")
cards = matrix_df.head(9).to_dict("records")
grid = st.columns(3)
for i, row in enumerate(cards):
    with grid[i % 3]:
        render_prop_card(
            player_name=selected["name"],
            team=selected.get("team", "UNK"),
            opponent="TBD",
            game_time="Today",
            prop_type=row.get("Prop"),
            line=row.get("Line"),
            over_odds=row.get("Best Over"),
            under_odds=row.get("Best Under"),
            model_proj=row.get("Projection") if row.get("Projection") is not None else row.get("Line"),
            edge_pct=row.get("Edge %", 0.0),
            image_url=get_headshot(selected),
        )

