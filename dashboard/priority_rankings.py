"""
APEX ANALYTICS - Top Edges
"""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
from datetime import datetime
from collections import Counter

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from utils.model import devig, american_to_prob
from dashboard.mlb_page import find_pitcher, build_game_model
from dashboard.ui_components import render_game_card

@st.cache_data(ttl=60)
def load_all_games():
    return supabase.table("games").select("*").order("start_time").execute().data or []

@st.cache_data(ttl=60)
def load_odds_for_game(game_id: str):
    return supabase.table("odds_snapshots").select("*").eq("game_id", game_id).execute().data or []


@st.cache_data(ttl=120)
def load_players():
    return supabase.table("players").select("id,name,team,sport").limit(2000).execute().data or []


@st.cache_data(ttl=120)
def load_player_props():
    return (
        supabase.table("player_prop_odds")
        .select("player_id,game_id,book,prop_type,line,over_price,under_price,created_at")
        .order("created_at", desc=True)
        .limit(10000)
        .execute()
        .data
        or []
    )


@st.cache_data(ttl=120)
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


def _norm_prop_type(p: str) -> str:
    p = (p or "").strip().lower()
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


def _fmt_odds(v):
    if v is None:
        return None
    try:
        iv = int(v)
        return f"+{iv}" if iv > 0 else str(iv)
    except Exception:
        return str(v)


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


def market_consensus_line(rows):
    book_weights = {"Pinnacle": 1.35, "Bovada": 1.2, "DraftKings": 1.1, "FanDuel": 1.1, "BetMGM": 1.0, "Caesars": 1.0, "bet365": 1.0}
    by_book = {}
    for r in rows:
        book = r.get("book")
        line = r.get("line")
        if book and line is not None and book not in by_book:
            by_book[book] = float(line)
    if not by_book:
        return None, 0
    weighted = sum(v * book_weights.get(b, 0.9) for b, v in by_book.items())
    total = sum(book_weights.get(b, 0.9) for b in by_book.keys())
    return weighted / total, len(by_book)


def blended_projection(stats, prop_type, rows_for_type):
    values = [_prop_value(s, prop_type) for s in stats]
    values = [v for v in values if v is not None]
    recent = values[:10]
    season = values[:30]
    recent_avg = (sum(recent) / len(recent)) if recent else None
    season_avg = (sum(season) / len(season)) if season else None
    market_line, books = market_consensus_line(rows_for_type)
    if recent_avg is not None and season_avg is not None and market_line is not None:
        return (0.50 * recent_avg) + (0.25 * season_avg) + (0.25 * market_line), f"blend(r+s+m:{books}b)", books
    if recent_avg is not None and market_line is not None:
        return (0.65 * recent_avg) + (0.35 * market_line), f"blend(r+m:{books}b)", books
    if recent_avg is not None and season_avg is not None:
        return (0.70 * recent_avg) + (0.30 * season_avg), "blend(r+s)", books
    if recent_avg is not None:
        return recent_avg, "recent", books
    if market_line is not None:
        return market_line, f"market:{books}b", books
    return None, "none", books


def hit_rates(stats, prop_type, line):
    values = [_prop_value(s, prop_type) for s in stats]
    values = [v for v in values if v is not None]
    if not values:
        return None, None
    over = round((sum(1 for v in values if v > line) / len(values)) * 100, 1)
    under = round((sum(1 for v in values if v < line) / len(values)) * 100, 1)
    return over, under


def build_player_prop_edges(players, prop_rows, selected_books, min_edge, limit=120):
    players_by_id = {p["id"]: p for p in players if p.get("id")}
    grouped = {}
    by_player_type = {}
    for r in prop_rows:
        pid = r.get("player_id")
        if pid not in players_by_id:
            continue
        if selected_books and r.get("book") not in selected_books:
            continue
        line = r.get("line")
        if line is None:
            continue
        ptype = _norm_prop_type(r.get("prop_type"))
        by_player_type.setdefault((pid, ptype), []).append(r)
        key = (pid, ptype, float(line))
        if key not in grouped:
            grouped[key] = {
                "player_id": pid,
                "prop_type": ptype,
                "line": float(line),
                "best_over": r.get("over_price"),
                "best_under": r.get("under_price"),
                "best_over_book": r.get("book"),
                "best_under_book": r.get("book"),
            }
        else:
            cur = grouped[key]
            ov = r.get("over_price")
            un = r.get("under_price")
            if ov is not None and (cur["best_over"] is None or ov > cur["best_over"]):
                cur["best_over"] = ov
                cur["best_over_book"] = r.get("book")
            if un is not None and (cur["best_under"] is None or un > cur["best_under"]):
                cur["best_under"] = un
                cur["best_under_book"] = r.get("book")

    edges = []
    stats_cache = {}
    proj_cache = {}
    for rec in grouped.values():
        pid = rec["player_id"]
        ptype = rec["prop_type"]
        stats = stats_cache.get(pid)
        if stats is None:
            stats = load_player_stats(pid, limit=40)
            stats_cache[pid] = stats
        proj_key = (pid, ptype)
        if proj_key not in proj_cache:
            proj_cache[proj_key] = blended_projection(stats, ptype, by_player_type.get(proj_key, []))
        proj, proj_src, market_books = proj_cache[proj_key]
        if proj is None or rec["line"] <= 0:
            continue
        over_edge = ((proj - rec["line"]) / rec["line"]) * 100
        under_edge = -over_edge
        side = "Over" if over_edge >= under_edge else "Under"
        edge = over_edge if side == "Over" else under_edge
        if edge < min_edge:
            continue
        hit_over, hit_under = hit_rates(stats, ptype, rec["line"])
        edges.append(
            {
                "Player": players_by_id[pid].get("name"),
                "Team": players_by_id[pid].get("team"),
                "Sport": players_by_id[pid].get("sport"),
                "Prop": ptype.replace("_", " ").title(),
                "Line": rec["line"],
                "Projection": round(proj, 2),
                "Proj Source": proj_src,
                "Mkt Books": market_books,
                "Side": side,
                "Edge %": round(edge, 2),
                "Hit Over %": hit_over,
                "Hit Under %": hit_under,
                "Best Over": _fmt_odds(rec["best_over"]),
                "Over Book": rec["best_over_book"],
                "Best Under": _fmt_odds(rec["best_under"]),
                "Under Book": rec["best_under_book"],
            }
        )
    edges.sort(key=lambda x: -(x.get("Edge %") or 0))
    return edges[:limit]

def best_ml(rows, team):
    m = [r for r in rows if r.get("market_type")=="h2h" and r.get("market_label")==team]
    if not m: return None
    return int(max(m, key=lambda r: r.get("price") or -9999).get("price", 0))

st.title("⚡ Top Edges")
st.caption("All sports sorted by raw mathematical edge.")
sort_mode = st.selectbox("Sort", ["Highest Edge", "Start Time", "Sport"], index=0)

games = load_all_games()
plays = []

for g in games:
    sport = g.get("sport", "?")
    rows  = load_odds_for_game(g["id"])
    away, home = g["away_team"], g["home_team"]
    a_ml = best_ml(rows, away)
    h_ml = best_ml(rows, home)
    if not a_ml or not h_ml: continue

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
            if dv_a > dv_h:
                best_e, best_t, best_m = (dv_a - american_to_prob(a_ml)) * 100, away, a_ml
            else:
                best_e, best_t, best_m = (dv_h - american_to_prob(h_ml)) * 100, home, h_ml
            best_l = "PLAY" if best_e >= 2 else "LEAN"
            model_p = dv_a
            dv_p    = dv_a
    else:
        if dv_a > american_to_prob(a_ml):
            best_e, best_t, best_m = (dv_a - american_to_prob(a_ml)) * 100, away, a_ml
            dv_p = dv_a
        else:
            best_e, best_t, best_m = (dv_h - american_to_prob(h_ml)) * 100, home, h_ml
            dv_p = dv_h
        best_l = "PLAY" if best_e >= 2 else "LEAN"
        model_p = dv_p

    try:
        t = datetime.fromisoformat(g["start_time"].replace("Z","+00:00"))
        time_str = t.strftime("%I:%M %p ET")
    except:
        time_str = "TBD"

    plays.append({
        "sport": sport, "away": away, "home": home, "time": time_str,
        "a_ml": a_ml, "h_ml": h_ml, "edge": best_e, "label": best_l,
        "model_p": model_p, "dv_p": dv_p, "value_team": best_t, "value_odds": best_m,
        "start_time": g.get("start_time", ""),
    })

if sort_mode == "Start Time":
    plays.sort(key=lambda x: x.get("start_time") or "")
elif sort_mode == "Sport":
    plays.sort(key=lambda x: (x.get("sport") or "", -(x.get("edge") or 0)))
else:
    plays.sort(key=lambda x: -(x.get("edge") or 0))

if not plays:
    st.info("No plays found.")
    st.stop()

cols = st.columns(2)
for idx, p in enumerate(plays):
    with cols[idx % 2]:
        render_game_card(
            sport=p["sport"], away_team=p["away"], home_team=p["home"],
            time_str=p["time"], away_ml=p["a_ml"], home_ml=p["h_ml"],
            edge_pct=p["edge"], recommendation=p["label"],
            model_prob=p["model_p"], market_prob=p["dv_p"],
            value_target=p.get("value_team"), value_odds=p.get("value_odds")
        )

st.markdown("<hr style='border-color: #1E293B;'>", unsafe_allow_html=True)
st.subheader("🧠 Player Prop Edges (Popular + Alt Lines)")
st.caption("Real-book lines with projection source + confidence, plus alt-line hit rates.")

players = load_players()
prop_rows = load_player_props()

available_books = sorted({r.get("book") for r in prop_rows if r.get("book")})
preferred = [b for b in ["Pinnacle", "Bovada", "DraftKings", "FanDuel", "BetMGM", "Caesars", "bet365"] if b in available_books]
b1, b2 = st.columns([3, 1])
with b1:
    selected_books = st.multiselect("Books", available_books, default=preferred or available_books[:4])
with b2:
    min_edge = st.slider("Min Edge %", min_value=0.0, max_value=25.0, value=2.0, step=0.5)

prop_edges = build_player_prop_edges(players, prop_rows, selected_books=selected_books, min_edge=min_edge, limit=250)

if not prop_edges:
    st.info("No player-prop edges found yet. Run projection + value snapshot workers in Data Manager.")
    st.stop()

popular_counts = Counter(e["Player"] for e in prop_edges if e.get("Player"))
popular_players = [name for name, _ in popular_counts.most_common(20)]
selected_popular = st.selectbox("Popular player", popular_players, index=0)

filtered = [e for e in prop_edges if e.get("Player") == selected_popular]
top_for_player = sorted(filtered, key=lambda x: -(x.get("Edge %") or 0))

if top_for_player:
    st.dataframe(pd.DataFrame(top_for_player[:30]), width="stretch", hide_index=True)

    prop_types = sorted({f["Prop"] for f in top_for_player})
    selected_prop = st.selectbox("View alt lines for prop", prop_types, index=0)
    alt_lines = [f for f in top_for_player if f["Prop"] == selected_prop]
    alt_lines = sorted(alt_lines, key=lambda x: x.get("Line") or 0)
    st.markdown("**Alt-line hit rates and edges**")
    st.dataframe(pd.DataFrame(alt_lines), width="stretch", hide_index=True)
