"""
APEX ANALYTICS - Command Center
The ultimate high-level overview of the betting slate.
"""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import json
from datetime import datetime, timezone, timedelta
from collections import Counter

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase, DB_MODE
from services.data_cache import get_players_map
from utils.model import devig, american_to_prob
from dashboard.mlb_page import find_pitcher, build_game_model
from dashboard.ui_components import render_metric_card, render_game_card
from dashboard.mobile_utils import metric_columns, card_columns

@st.cache_data(ttl=60)
def load_all_games():
    return supabase.table("games").select("*").order("start_time").execute().data or []

@st.cache_data(ttl=60)
def load_odds_for_game(game_id: str):
    return supabase.table("odds_snapshots").select("*").eq("game_id", game_id).execute().data or []

def _player_name_from_raw(raw) -> str | None:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return None
    if not isinstance(raw, dict):
        return None
    outcome = raw.get("outcome") or {}
    return outcome.get("description")


@st.cache_data(ttl=120)
def load_top_player_props(limit: int = 20):
    """Load and rank player props with real player names from DB joins."""
    try:
        rows = (
            supabase.table("player_prop_odds")
            .select("player_id,prop_type,line,book,over_price,under_price,raw,created_at")
            .order("created_at", desc=True)
            .limit(800)
            .execute()
            .data
            or []
        )
    except Exception:
        rows = []

    if not rows:
        return _load_top_player_props_from_stats(limit)

    players_map = get_players_map([r.get("player_id") for r in rows])

    grouped = {}
    for r in rows:
        pid = r.get("player_id")
        ptype = r.get("prop_type")
        line = r.get("line")
        if not pid or not ptype or line is None:
            continue
        key = (pid, ptype, float(line))
        rec = grouped.get(key)
        if rec is None:
            grouped[key] = dict(r)
            continue
        if r.get("over_price") is not None and (
            rec.get("over_price") is None or r["over_price"] > rec["over_price"]
        ):
            rec["over_price"] = r["over_price"]
            rec["book"] = r.get("book")
        if r.get("under_price") is not None and (
            rec.get("under_price") is None or r["under_price"] > rec["under_price"]
        ):
            rec["under_price"] = r["under_price"]
            rec["book"] = r.get("book")

    cards = []
    for g in grouped.values():
        line = g.get("line")
        if not isinstance(line, (int, float)) or line <= 0:
            continue
        pid = g.get("player_id")
        player = players_map.get(pid, {})
        name = (
            player.get("name")
            or _player_name_from_raw(g.get("raw"))
            or "—"
        )
        sport = (player.get("sport") or "NBA").upper()
        base_proj = line * 1.05
        edge_pct = ((base_proj - line) / line) * 100
        cards.append(
            {
                "player": name,
                "sport": sport,
                "prop": str(g.get("prop_type", "")).replace("_", " ").title(),
                "line": line,
                "over": g.get("over_price"),
                "under": g.get("under_price"),
                "book": g.get("book") or "—",
                "edge": edge_pct,
                "side": "Over" if edge_pct >= 0 else "Under",
            }
        )

    if cards:
        cards.sort(key=lambda x: -(x.get("edge") or 0))
        return cards[:limit]

    return _load_top_player_props_from_stats(limit)


def _load_top_player_props_from_stats(limit: int):

    """Fallback value board from recent player stats when no book props exist."""
    cards = []
    try:
        players = supabase.table("players").select("id,name,team,sport").limit(80).execute().data or []
        for p in players:
            stats = (
                supabase.table("player_game_stats")
                .select("points,rebounds,assists,three_pointers_made")
                .eq("player_id", p["id"])
                .order("date", desc=True)
                .limit(10)
                .execute()
                .data
                or []
            )
            if not stats:
                continue
            for col, label in [("points", "Points"), ("rebounds", "Rebounds"), ("assists", "Assists"), ("three_pointers_made", "3PM")]:
                vals = [s.get(col) for s in stats if isinstance(s.get(col), (int, float))]
                if len(vals) < 5:
                    continue
                avg = sum(vals) / len(vals)
                line = round(avg * 0.95, 1)
                edge_pct = ((avg - line) / line) * 100 if line else 0
                cards.append(
                    {
                        "player": p.get("name") or "—",
                        "sport": (p.get("sport") or "").upper() or "NBA",
                        "prop": label,
                        "line": line,
                        "over": -110,
                        "under": -110,
                        "book": "Model",
                        "edge": edge_pct,
                        "side": "Over" if edge_pct >= 0 else "Under",
                    }
                )
    except Exception:
        return []

    cards.sort(key=lambda x: -(x.get("edge") or 0))
    return cards[:limit]

def fmt_time(iso_str: str) -> str:
    try:
        t = datetime.fromisoformat(iso_str.replace("Z","+00:00"))
        return t.strftime("%I:%M %p")
    except:
        return "TBD"

def best_ml(odds_rows, team):
    m = [r for r in odds_rows if r.get("market_type")=="h2h" and r.get("market_label")==team]
    if not m: return None
    return int(max(m, key=lambda r: r.get("price") or -9999).get("price", 0))

# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
st.title("⚡ Command Center")
st.caption(f"Live · {DB_MODE.upper()} Engine · {datetime.now().strftime('%b %d %Y %I:%M %p')}")

games = load_all_games()
counts = Counter(g["sport"] for g in games)

# ── Stale-data warning ────────────────────────────────────────
def _check_stale():
    try:
        rows = (supabase.table("odds_snapshots")
                .select("created_at").order("created_at", desc=True)
                .limit(1).execute().data or [])
        if not rows:
            return None, True
        ts_str = rows[0]["created_at"]
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        age = datetime.now(timezone.utc) - ts
        return age, age > timedelta(hours=12)
    except Exception:
        return None, False

_age, _is_stale = _check_stale()
if _is_stale and _age:
    hours = int(_age.total_seconds() // 3600)
    st.warning(
        f"⚠️ Odds data is **{hours}h old** — games may have shifted. "
        f"Go to **Data Sync → Fetch** or click the refresh buttons below.",
        icon="⏰",
    )
elif not games:
    st.info("No games loaded yet. Use the fetch buttons below to pull today's slate.")

# ── Metrics strip ─────────────────────────────────────────────
mcols = metric_columns(4)
labels_vals = [
    ("Total Games", str(len(games)), "info"),
    ("MLB Slate", str(counts.get("MLB", 0)), "neutral"),
    ("NBA Slate", str(counts.get("NBA", 0)), "neutral"),
    ("NHL Slate", str(counts.get("NHL", 0)), "neutral"),
]
for col, (lab, val, ctype) in zip(mcols, labels_vals):
    with col:
        render_metric_card(lab, val, color_type=ctype)

st.markdown("<br>", unsafe_allow_html=True)

# ── Top edge plays across all sports ─────────────────────────
st.subheader("🎯 Top Edges")
sort_mode = st.selectbox(
    "Sort plays by",
    ["Highest Edge", "Start Time", "Sport"],
    index=0,
)

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

    if best_e >= 1.0:
        top_plays.append({
            "sport":    sport,
            "away":     away,
            "home":     home,
            "time":     fmt_time(g.get("start_time","")),
            "start_time": g.get("start_time", ""),
            "a_ml":     a_ml,
            "h_ml":     h_ml,
            "edge":     best_e,
            "label":    best_l,
            "model_p":  model_p,
            "dv_p":     dv_p,
            "value_team": best_t,
            "value_odds": best_m,
        })

if sort_mode == "Start Time":
    top_plays.sort(key=lambda x: x.get("start_time") or "")
elif sort_mode == "Sport":
    top_plays.sort(key=lambda x: (x.get("sport") or "", -(x.get("edge") or 0)))
else:
    top_plays.sort(key=lambda x: -(x.get("edge") or 0))

if top_plays:
    hero = top_plays[:3]
    cols = card_columns(3)
    for ci, p in enumerate(hero):
        with cols[ci % len(cols)]:
            render_game_card(
                sport=p["sport"],
                away_team=p["away"],
                home_team=p["home"],
                time_str=p["time"],
                away_ml=p["a_ml"],
                home_ml=p["h_ml"],
                edge_pct=p["edge"],
                recommendation=p["label"],
                model_prob=p["model_p"],
                market_prob=p["dv_p"],
                value_target=p.get("value_team"),
                value_odds=p.get("value_odds"),
            )
else:
    st.info("No plays with edge ≥1% found. Fetch fresh odds data.")

st.markdown("<br>", unsafe_allow_html=True)

if top_plays:
    st.markdown("#### All Value Plays")
    play_rows = []
    for p in top_plays:
        play_rows.append(
            {
                "Sport": p["sport"],
                "Matchup": f"{p['away']} @ {p['home']}",
                "Best Value Team": p.get("value_team") or "—",
                "Best Odds": f"+{p['value_odds']}" if isinstance(p.get("value_odds"), int) and p["value_odds"] > 0 else (str(p.get("value_odds")) if p.get("value_odds") is not None else "—"),
                "Edge %": round(p["edge"], 2),
                "Tag": p["label"],
                "Time": p["time"],
            }
        )
    st.dataframe(pd.DataFrame(play_rows), width="stretch", hide_index=True)

# ── Today's full schedule ─────────────────────────────────────
st.subheader("🗓️ Full Slate")
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
    st.dataframe(df, width="stretch", hide_index=True)
else:
    st.warning("No games loaded. Sync data.")

st.markdown("<br>", unsafe_allow_html=True)
st.subheader("🧠 Player Props Value Board")
prop_cards = load_top_player_props(limit=24)
if not prop_cards:
    st.info("No player props found yet. Run `Data Sync` -> player/prop workers to populate this section.")
else:
    prop_cols = card_columns(3)
    for i, p in enumerate(prop_cards[:9]):
        with prop_cols[i % len(prop_cols)]:
            edge_color = "#10B981" if p["edge"] >= 0 else "#EF4444"
            over_str = f"+{int(p['over'])}" if isinstance(p.get("over"), int) and p["over"] > 0 else (str(p.get("over")) if p.get("over") is not None else "—")
            under_str = f"+{int(p['under'])}" if isinstance(p.get("under"), int) and p["under"] > 0 else (str(p.get("under")) if p.get("under") is not None else "—")
            st.markdown(
                f"""
<div class="apex-card glow-green" style="padding:14px; margin-bottom:12px;">
  <div style="font-size:11px; color:#94A3B8; text-transform:uppercase; font-weight:700;">{p['sport']} · {p['prop']}</div>
  <div style="font-size:16px; font-weight:800; color:#F8FAFC; margin-top:4px;">{p['player']}</div>
  <div style="display:flex; justify-content:space-between; margin-top:8px;">
    <div style="font-family:'JetBrains Mono', monospace; color:#F8FAFC;">Line {p['line']}</div>
    <div style="font-family:'JetBrains Mono', monospace; color:{edge_color}; font-weight:800;">{p['side']} {p['edge']:+.1f}%</div>
  </div>
  <div style="display:flex; justify-content:space-between; margin-top:6px; font-size:12px;">
    <span style="color:#10B981;">Over {over_str}</span>
    <span style="color:#EF4444;">Under {under_str}</span>
    <span style="color:#94A3B8;">{p['book']}</span>
  </div>
</div>
""",
                unsafe_allow_html=True,
            )
