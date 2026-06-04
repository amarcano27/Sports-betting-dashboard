"""
APEX ANALYTICS - PGA / Golf Model
Tournament outright odds · Best price line shopping · Devigged implied probability ·
Value plays · Top-10/20 finish analysis
"""
import sys, math
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from collections import defaultdict

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from dashboard.premium_styles import TOKENS
from dashboard.mobile_utils import inject_mobile_css

inject_mobile_css()

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def american_to_prob(odds: int) -> float:
    if odds < 0: return abs(odds) / (abs(odds) + 100)
    return 100 / (odds + 100)

def prob_to_american(p: float) -> int:
    p = max(0.001, min(0.999, p))
    if p >= 0.5: return round(-p / (1-p) * 100)
    return round((1-p) / p * 100)

def devig_field(players: list[dict]) -> dict[str, float]:
    """
    Remove the vig from a golf outright field.
    Method: sum all implied probs (will be >1.0 due to overround),
    normalize each back to sum to 1.0.
    Returns {player_name: true_prob}.
    """
    total_implied = sum(american_to_prob(p["best_odds"]) for p in players)
    if total_implied == 0:
        return {}
    return {p["name"]: american_to_prob(p["best_odds"]) / total_implied for p in players}

def overround_pct(players: list[dict]) -> float:
    total = sum(american_to_prob(p["best_odds"]) for p in players)
    return round((total - 1.0) * 100, 1)

def format_odds(odds: int) -> str:
    return f"+{odds}" if odds > 0 else str(odds)

# ─────────────────────────────────────────────────────────────
# DATA LOADERS
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_pga_tournaments() -> list[dict]:
    """Load PGA games (each tournament = 1 game record)."""
    return (supabase.table("games").select("*")
            .eq("sport", "PGA").order("start_time").execute().data or [])

@st.cache_data(ttl=300)
def load_tournament_odds(game_id: str) -> list[dict]:
    return (supabase.table("odds_snapshots").select("*")
            .eq("game_id", game_id).execute().data or [])


def build_player_board(odds_rows: list[dict]) -> list[dict]:
    """
    Aggregate all odds snapshots into a per-player board.
    Returns sorted list of player dicts with best odds + all book prices.
    """
    # Group by player name, then by book
    by_player: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for r in odds_rows:
        player = r.get("market_label", "")
        book   = r.get("book", "?")
        price  = r.get("price")
        if player and price is not None:
            by_player[player][book].append(int(price))

    board = []
    for player, books in by_player.items():
        # Best price = highest American odds (best for bettor)
        all_prices = []
        book_best  = {}
        for book, prices in books.items():
            best_p = max(prices)
            book_best[book] = best_p
            all_prices.extend(prices)

        best_odds  = max(all_prices)
        best_book  = max(book_best, key=lambda b: book_best[b])
        worst_odds = min(all_prices)

        board.append({
            "name":       player,
            "best_odds":  best_odds,
            "best_book":  best_book.upper(),
            "worst_odds": worst_odds,
            "spread":     best_odds - worst_odds,   # line shopping value
            "book_prices": book_best,
            "n_books":    len(book_best),
        })

    # Sort by best odds ascending (favorites first)
    board.sort(key=lambda x: american_to_prob(x["best_odds"]), reverse=True)
    return board


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
st.title("⛳ PGA Golf")
st.caption("Tournament outright odds · Devigged win probabilities · Best price finder · Value analysis")

tournaments = load_pga_tournaments()
if not tournaments:
    st.warning("No PGA tournament data. Go to **Data Sync** → enter password → **Fetch All Sports**.")
    st.stop()

# Tournament picker
tourn_names = {t.get("home_team") or t.get("away_team") or f"Tournament {i}": t
               for i, t in enumerate(tournaments)}
sel_name = st.selectbox("Tournament", list(tourn_names.keys()),
                        label_visibility="collapsed")
tourn = tourn_names[sel_name]
odds_rows = load_tournament_odds(tourn["id"])

if not odds_rows:
    st.warning("No odds for this tournament yet. Fetch via Data Sync.")
    st.stop()

board = build_player_board(odds_rows)
if not board:
    st.info("No player odds found in snapshots.")
    st.stop()

# Devig the full field
true_probs = devig_field(board)
overround  = overround_pct(board)

# ── Tournament header strip ───────────────────────────────────
from datetime import datetime
try:
    t   = datetime.fromisoformat(tourn["start_time"].replace("Z","+00:00"))
    tstr = t.strftime("%b %d, %Y")
except Exception:
    tstr = "—"

all_books = sorted({b for p in board for b in p["book_prices"].keys()})

m1, m2, m3, m4 = st.columns(4)
m1.metric("Tournament",  sel_name[:22])
m2.metric("Start Date",  tstr)
m3.metric("Field Size",  f"{len(board)} players")
m4.metric("Book Overround", f"{overround:.1f}%",
          help="How much of every $1 wagered goes to the house. Golf outrights have very high overround (120-160%).")

st.markdown("---")

# ── Tabs ─────────────────────────────────────────────────────
tab_odds, tab_value, tab_shop, tab_chart = st.tabs([
    "🏆 Full Odds Board",
    "💎 Value Plays",
    "🛒 Line Shopping",
    "📊 Probability Chart",
])

# ─────────────────────────────────────────────────────────────
# TAB 1 — FULL ODDS BOARD
# ─────────────────────────────────────────────────────────────
with tab_odds:
    st.subheader("🏆 Full Field — Best Odds")
    st.caption(f"Best price across {len(all_books)} books: {', '.join(b.upper() for b in all_books[:6])}")

    search = st.text_input("🔍 Search player", placeholder="e.g. Scheffler", label_visibility="collapsed")

    rows = []
    for i, p in enumerate(board, 1):
        if search and search.lower() not in p["name"].lower():
            continue
        true_p = true_probs.get(p["name"], 0)
        fair_o = prob_to_american(true_p)
        implied = american_to_prob(p["best_odds"])
        # Cross-book edge: best price vs fair (devigged consensus) odds
        edge = round((implied - true_p) * 100, 1)  # negative = market overpricing player
        rows.append({
            "#":         i,
            "Player":    p["name"],
            "Best Odds": format_odds(p["best_odds"]),
            "@ Book":    p["best_book"],
            "Fair Odds": format_odds(fair_o),
            "Win Prob":  f"{true_p*100:.1f}%",
            "Implied":   f"{implied*100:.1f}%",
            "Books":     p["n_books"],
        })

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True,
            height=min(600, 36*len(rows)+38),
            column_config={
                "#":         st.column_config.NumberColumn(width=45),
                "Player":    st.column_config.TextColumn(width=185),
                "Best Odds": st.column_config.TextColumn(width=95),
                "@ Book":    st.column_config.TextColumn(width=90),
                "Fair Odds": st.column_config.TextColumn(width=90),
                "Win Prob":  st.column_config.TextColumn(width=80),
                "Implied":   st.column_config.TextColumn(width=80),
                "Books":     st.column_config.NumberColumn(width=60),
            })


# ─────────────────────────────────────────────────────────────
# TAB 2 — VALUE PLAYS
# ─────────────────────────────────────────────────────────────
with tab_value:
    st.subheader("💎 Value Plays")
    st.caption("""
**How golf value works:** The devigged consensus across all books is the best estimate of "true" probability.
When one book offers significantly better odds than the consensus fair price — that's value.
Also: long shots with plus-money where the consensus underestimates them.
    """)

    val_rows = []
    for p in board:
        true_p = true_probs.get(p["name"], 0)
        if true_p == 0:
            continue
        fair_odds = prob_to_american(true_p)
        best      = p["best_odds"]
        spread    = p["spread"]

        # Value score: how much better than fair odds
        if best > 0 and fair_odds > 0:
            value_pct = round((best - fair_odds) / fair_odds * 100, 1)
        elif best < 0 and fair_odds < 0:
            # Both negative: best is more positive = better
            value_pct = round((abs(fair_odds) - abs(best)) / abs(fair_odds) * 100, 1)
        else:
            value_pct = round(best - fair_odds, 0)

        # Only show plays where there's meaningful line shopping value or positive value
        if value_pct >= 5 or spread >= 200:
            tier = ("🔥 BEST VALUE" if value_pct >= 20 else
                    "✅ STRONG"     if value_pct >= 10 else
                    "⚡ PLAY")
            val_rows.append({
                "Player":       p["name"],
                "Best Odds":    format_odds(best),
                "@ Book":       p["best_book"],
                "Fair Odds":    format_odds(fair_odds),
                "Value %":      f"+{value_pct:.0f}%",
                "Book Spread":  f"+{spread}" if spread > 0 else "—",
                "Win Prob":     f"{true_p*100:.1f}%",
                "Rating":       tier,
            })

    if val_rows:
        val_rows.sort(key=lambda x: float(x["Value %"].lstrip("+").rstrip("%")), reverse=True)
        st.dataframe(pd.DataFrame(val_rows), use_container_width=True, hide_index=True,
            column_config={
                "Player":      st.column_config.TextColumn(width=185),
                "Best Odds":   st.column_config.TextColumn(width=95),
                "@ Book":      st.column_config.TextColumn(width=90),
                "Fair Odds":   st.column_config.TextColumn(width=90),
                "Value %":     st.column_config.TextColumn(width=75),
                "Book Spread": st.column_config.TextColumn(width=90),
                "Win Prob":    st.column_config.TextColumn(width=80),
                "Rating":      st.column_config.TextColumn(width=110),
            })
    else:
        st.info("No significant value plays detected. All books are closely aligned.")

    st.markdown("---")
    st.subheader("🎯 Top Long Shots (100/1+)")
    st.caption("High-odds players where a small bet can pay big. Sorted by devigged win probability.")
    long_shots = [p for p in board if p["best_odds"] >= 10000]
    long_shots.sort(key=lambda x: true_probs.get(x["name"],0), reverse=True)
    if long_shots:
        ls_rows = [{
            "Player":   p["name"],
            "Best":     format_odds(p["best_odds"]),
            "@ Book":   p["best_book"],
            "Win Prob": f"{true_probs.get(p['name'],0)*100:.2f}%",
            "$10 pays": f"${10 * p['best_odds']/100:.0f}",
            "$25 pays": f"${25 * p['best_odds']/100:.0f}",
        } for p in long_shots[:20]]
        st.dataframe(pd.DataFrame(ls_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No 100/1+ long shots found.")


# ─────────────────────────────────────────────────────────────
# TAB 3 — LINE SHOPPING
# ─────────────────────────────────────────────────────────────
with tab_shop:
    st.subheader("🛒 Line Shopping — Cross-Book Comparison")
    st.caption("Find the biggest discrepancies between books for any player. Biggest spread = most line shopping value.")

    # Sort by cross-book spread
    shop_rows = sorted(board, key=lambda x: -x["spread"])

    search2 = st.text_input("🔍 Search player", key="shop_search",
                             placeholder="e.g. McIlroy", label_visibility="collapsed")

    for p in shop_rows[:30]:
        if search2 and search2.lower() not in p["name"].lower():
            continue
        if p["spread"] < 100:
            continue
        true_p = true_probs.get(p["name"], 0)
        with st.expander(f"**{p['name']}** — spread: {p['best_odds']:+d} vs {p['worst_odds']:+d} "
                         f"(gap: +{p['spread']}) | Win Prob: {true_p*100:.1f}%"):
            book_rows = []
            for book, price in sorted(p["book_prices"].items(), key=lambda x: -x[1]):
                implied = american_to_prob(price) * 100
                book_rows.append({
                    "Book":      book.upper(),
                    "Odds":      format_odds(price),
                    "Implied %": f"{implied:.1f}%",
                    "vs Fair":   f"{implied - true_p*100:+.1f}%",
                    "Best?":     "✅ Best" if price == p["best_odds"] else "",
                })
            st.dataframe(pd.DataFrame(book_rows), use_container_width=True, hide_index=True,
                column_config={
                    "Book":      st.column_config.TextColumn(width=120),
                    "Odds":      st.column_config.TextColumn(width=90),
                    "Implied %": st.column_config.TextColumn(width=90),
                    "vs Fair":   st.column_config.TextColumn(width=80),
                    "Best?":     st.column_config.TextColumn(width=80),
                })


# ─────────────────────────────────────────────────────────────
# TAB 4 — PROBABILITY CHART
# ─────────────────────────────────────────────────────────────
with tab_chart:
    st.subheader("📊 Win Probability Distribution")

    top_n = st.slider("Show top N players", 10, min(50, len(board)), 20, 5)
    top   = board[:top_n]

    names  = [p["name"].split()[-1] for p in top]
    probs  = [true_probs.get(p["name"], 0) * 100 for p in top]
    colors = [TOKENS["green"] if p["best_odds"] < 1000 else
              TOKENS["amber"] if p["best_odds"] < 3000 else
              TOKENS["text_muted"] for p in top]

    fig = go.Figure(go.Bar(
        x=names, y=probs,
        marker_color=colors,
        text=[f"{p:.1f}%" for p in probs],
        textposition="outside",
    ))
    fig.update_layout(
        height=380,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=dict(color=TOKENS["text_muted"], size=10)),
        yaxis=dict(visible=False),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Green = favorites (<+1000), Amber = mid-range, Grey = long shots. "
               "Probabilities are devigged consensus — not raw implied.")

    # Top 5 cumulative
    top5_prob = sum(probs[:5])
    st.markdown(f"""
<div style="background:{TOKENS['bg_panel_2']};border-radius:8px;padding:14px;margin-top:8px">
  <b style="color:{TOKENS['text_primary']}">Top 5 combined win probability: {top5_prob:.1f}%</b>
  <span style="color:{TOKENS['text_muted']};font-size:13px"> — roughly 1-in-{100/top5_prob:.0f} chance one of the top 5 wins</span>
  <br><span style="color:{TOKENS['text_muted']};font-size:12px">Field overround: {overround:.1f}% — the house takes {overround:.1f}¢ for every $1 wagered in outright markets</span>
</div>""", unsafe_allow_html=True)
