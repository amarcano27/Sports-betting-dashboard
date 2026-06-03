"""
Priority Rankings — Elo+FIP model edge sorted across all sports.
Uses devigged market probability as the truth baseline.
"""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from utils.model import (
    devig, american_to_prob, prob_to_american,
    quarter_kelly, vig_pct, build_game_model,
    REC_COLORS, MIN_EDGE_PCT,
)
from dashboard.mlb_page import find_pitcher
from dashboard.premium_styles import color


@st.cache_data(ttl=120)
def build_all_rankings() -> list[dict]:
    """
    For every game in the DB, run the Elo+FIP model and compute:
      - Model probability (Elo + FIP + home field)
      - Devigged market probability (MPTO)
      - Edge = model − devig
      - Quarter Kelly stake
    """
    games = supabase.table("games").select("*").execute().data or []
    rankings = []

    for g in games:
        sport = g.get("sport","?")
        odds_rows = (
            supabase.table("odds_snapshots")
            .select("*").eq("game_id", g["id"]).execute().data or []
        )

        away, home = g["away_team"], g["home_team"]
        h2h = [r for r in odds_rows if r.get("market_type") == "h2h"]

        def best(team):
            m = [r for r in h2h if r.get("market_label") == team]
            if not m: return None, None
            b = max(m, key=lambda r: r.get("price") or -9999)
            return int(b["price"]), b.get("book","?")

        away_ml, away_book = best(away)
        home_ml, home_book = best(home)
        if away_ml is None or home_ml is None:
            continue

        # Devig (always available when we have both sides)
        dv_away, dv_home = devig(away_ml, home_ml)
        v = vig_pct(away_ml, home_ml)

        try:
            t_str = g["start_time"]
            from datetime import datetime
            t = datetime.fromisoformat(t_str.replace("Z","+00:00"))
            time_str = t.strftime("%I:%M %p ET")
        except Exception:
            time_str = "TBD"

        matchup = f"{away} @ {home}"

        # For MLB use full Elo+FIP model
        if sport == "MLB":
            apn, apd = find_pitcher(away)
            hpn, hpd = find_pitcher(home)
            if apd and hpd:
                gm = build_game_model(
                    away, home,
                    apd["fip"], hpd["fip"],
                    away_ml, home_ml,
                    away_pitcher_name=apn or away,
                    home_pitcher_name=hpn or home,
                )
                for team, ml, book, model_p, dv_p, edge, kelly in [
                    (away, away_ml, away_book, gm.model_away_prob, dv_away, gm.away_edge, gm.away_kelly),
                    (home, home_ml, home_book, gm.model_home_prob, dv_home, gm.home_edge, gm.home_kelly),
                ]:
                    rankings.append(_make_row(
                        sport, team, matchup, time_str, ml, book,
                        model_p, dv_p, edge, kelly, v
                    ))
            else:
                # No pitcher data — use devig-only (no model edge, just market)
                for team, ml, book, dv_p in [
                    (away, away_ml, away_book, dv_away),
                    (home, home_ml, home_book, dv_home),
                ]:
                    rankings.append(_make_row(
                        sport, team, matchup, time_str, ml, book,
                        dv_p, dv_p, 0.0, 0.0, v,
                        note="No pitcher data"
                    ))
        else:
            # Non-MLB: use devig market only (no FIP data)
            for team, ml, book, dv_p in [
                (away, away_ml, away_book, dv_away),
                (home, home_ml, home_book, dv_home),
            ]:
                rankings.append(_make_row(
                    sport, team, matchup, time_str, ml, book,
                    dv_p, dv_p, 0.0, 0.0, v,
                    note="Market devig only (no model)"
                ))

    rankings.sort(key=lambda r: -r["edge"])
    return rankings


def _make_row(sport, team, matchup, time_str, ml, book,
              model_p, dv_p, edge, kelly, vig, note=""):
    ml_str = f"+{ml}" if ml > 0 else str(ml)
    if abs(ml) >= 200 and ml < 0:
        rec = "PARLAY ONLY"
    elif edge >= 8:   rec = "BEST VALUE"
    elif edge >= 5:   rec = "STRONG"
    elif edge >= 2:   rec = "PLAY"
    elif edge >= 0:   rec = "LEAN"
    else:             rec = "SKIP"

    # Kelly stake ranges
    if kelly >= 0.06:       stake = "$50–$75"
    elif kelly >= 0.04:     stake = "$35–$50"
    elif kelly >= 0.02:     stake = "$20–$35"
    elif kelly > 0:         stake = "$10–$20"
    else:                   stake = "—"

    return {
        "sport":      sport,
        "team":       team,
        "matchup":    matchup,
        "time":       time_str,
        "ml":         ml,
        "ml_str":     ml_str,
        "book":       book.upper() if book else "?",
        "model_pct":  round(model_p * 100, 1),
        "devig_pct":  round(dv_p  * 100, 1),
        "edge":       edge,
        "kelly":      round(kelly * 100, 2),
        "stake":      stake,
        "rec":        rec,
        "vig":        vig,
        "note":       note,
    }


# ─────────────────────────────────────────────────────────────
# PAGE
# ─────────────────────────────────────────────────────────────
st.title("📊 Priority Rankings")
st.caption("All plays sorted by edge (model prob − devigged market prob). Top plays highlighted. Quarter Kelly stakes.")

rankings = build_all_rankings()
if not rankings:
    st.warning("No data. Go to **Data Manager → Fetch odds**.")
    st.stop()

# ── Filters ───────────────────────────────────────────────────
fc1, fc2, fc3 = st.columns(3)
sport_filter = fc1.selectbox("Sport", ["All"] + sorted({r["sport"] for r in rankings}))
min_edge     = fc2.slider("Min Edge %", -10.0, 20.0, 0.0, 0.5)
hide_parlay  = fc3.checkbox("Hide parlay-only (−200+)", value=True)

filtered = [r for r in rankings
            if (sport_filter == "All" or r["sport"] == sport_filter)
            and r["edge"] >= min_edge
            and not (hide_parlay and r["rec"] == "PARLAY ONLY")]

st.caption(f"Showing **{len(filtered)}** of {len(rankings)} plays")

# ── Model confidence banner ───────────────────────────────────
actionable = [r for r in filtered if r["edge"] >= MIN_EDGE_PCT]
st.markdown(f"""
<div style="background:{color('bg_panel')};border:1px solid {color('border')};
            border-radius:8px;padding:12px 16px;margin-bottom:16px;
            display:flex;gap:32px;align-items:center;flex-wrap:wrap">
  <div>
    <div style="font-size:10px;color:{color('text_muted')};text-transform:uppercase;font-weight:600">
      Actionable Plays (≥2% edge)
    </div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:24px;font-weight:700;
                color:{color('green')}">{len(actionable)}</div>
  </div>
  <div>
    <div style="font-size:10px;color:{color('text_muted')};text-transform:uppercase;font-weight:600">
      Best Edge
    </div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:24px;font-weight:700;
                color:{color('green')}">+{filtered[0]['edge']:.1f}%</div>
  </div>
  <div>
    <div style="font-size:10px;color:{color('text_muted')};text-transform:uppercase;font-weight:600">
      Model Source
    </div>
    <div style="font-size:13px;font-weight:600;color:{color('text_primary')}">
      Elo+FIP (MLB) · Devig-only (other)
    </div>
  </div>
  <div style="font-size:11px;color:{color('text_muted')};max-width:300px">
    Edge = model probability − no-vig (devigged) market probability.
    Beating the closing line by 2–5% consistently = long-term profitable.
  </div>
</div>
""", unsafe_allow_html=True)

# ── Top 3 gold/silver/bronze ──────────────────────────────────
medals = ["🥇 #1", "🥈 #2", "🥉 #3"]
medal_bg = [
    f"linear-gradient(90deg, {color('gold')}22, {color('bg_panel')})",
    f"linear-gradient(90deg, {color('silver')}22, {color('bg_panel')})",
    f"linear-gradient(90deg, {color('bronze')}22, {color('bg_panel')})",
]
medal_border = [color("gold"), color("silver"), color("bronze")]
sport_icon = {"MLB":"⚾","NBA":"🏀","NHL":"🏒","NFL":"🏈","PGA":"⛳"}

for i, r in enumerate(filtered[:3]):
    rc   = REC_COLORS.get(r["rec"], color("text_primary"))
    mlc  = color("green") if r["ml"] > 0 else color("text_primary")
    note = f' · {r["note"]}' if r["note"] else ""

    st.markdown(f"""
<div style="background:{medal_bg[i]};border-left:4px solid {medal_border[i]};
            border-radius:8px;padding:18px;margin-bottom:12px;
            border:1px solid {color('border')}">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px">
    <div>
      <div style="font-size:13px;color:{color('text_muted')};font-weight:600;margin-bottom:4px">
        {medals[i]} · {sport_icon.get(r['sport'],'🏆')} {r['sport']} · {r['time']}
      </div>
      <div style="font-size:18px;font-weight:700;color:{color('text_primary')}">{r['team']} ML</div>
      <div style="font-size:13px;color:{color('text_muted')};margin-top:2px">{r['matchup']}</div>
    </div>
    <div style="text-align:right">
      <div style="font-family:'JetBrains Mono',monospace;font-size:26px;
                  font-weight:700;color:{mlc}">{r['ml_str']}</div>
      <div style="font-size:11px;color:{color('text_muted')};text-transform:uppercase">{r['book']}</div>
      <div style="margin-top:4px;display:inline-block;background:{rc};color:#0d1117;
                  padding:3px 10px;border-radius:4px;font-size:11px;font-weight:800">{r['rec']}</div>
    </div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px;
              margin-top:14px;padding-top:14px;border-top:1px solid {color('border')}">
    <div>
      <div style="font-size:9px;color:{color('text_muted')};text-transform:uppercase">Model %</div>
      <div style="font-family:'JetBrains Mono',monospace;font-weight:700;
                  color:{color('text_primary')}">{r['model_pct']}%</div>
    </div>
    <div>
      <div style="font-size:9px;color:{color('text_muted')};text-transform:uppercase">Devig Mkt</div>
      <div style="font-family:'JetBrains Mono',monospace;font-weight:700;
                  color:{color('text_muted')}">{r['devig_pct']}%</div>
    </div>
    <div>
      <div style="font-size:9px;color:{color('text_muted')};text-transform:uppercase">Edge</div>
      <div style="font-family:'JetBrains Mono',monospace;font-weight:700;
                  color:{color('green') if r['edge']>=2 else color('amber')}">{'+' if r['edge']>=0 else ''}{r['edge']:.1f}%</div>
    </div>
    <div>
      <div style="font-size:9px;color:{color('text_muted')};text-transform:uppercase">Vig</div>
      <div style="font-family:'JetBrains Mono',monospace;font-weight:700;
                  color:{color('text_muted')}">{r['vig']:.1f}%</div>
    </div>
    <div>
      <div style="font-size:9px;color:{color('text_muted')};text-transform:uppercase">Kelly / Stake</div>
      <div style="font-size:13px;font-weight:700;color:{color('amber')}">{r['stake']}</div>
      <div style="font-size:10px;color:{color('text_muted')}">{r['kelly']:.1f}% bankroll{note}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ── Full rankings table ────────────────────────────────────────
st.subheader("All Plays")
if len(filtered) > 3:
    table_rows = []
    for idx, r in enumerate(filtered[3:], 4):
        rc  = REC_COLORS.get(r["rec"], color("text_primary"))
        table_rows.append({
            "Rank":      f"#{idx}",
            "Sport":     r["sport"],
            "Team ML":   f"{r['team']} {r['ml_str']}",
            "Matchup":   r["matchup"],
            "Time":      r["time"],
            "Book":      r["book"],
            "Model %":   f"{r['model_pct']}%",
            "Devig %":   f"{r['devig_pct']}%",
            "Edge":      f"{'+' if r['edge']>=0 else ''}{r['edge']:.1f}%",
            "Vig":       f"{r['vig']:.1f}%",
            "Stake":     r["stake"],
            "Status":    r["rec"],
        })
    st.dataframe(
        pd.DataFrame(table_rows),
        width="stretch",
        hide_index=True,
        column_config={
            "Rank":    st.column_config.TextColumn(width=55),
            "Sport":   st.column_config.TextColumn(width=70),
            "Team ML": st.column_config.TextColumn(width=200),
            "Matchup": st.column_config.TextColumn(width=240),
            "Time":    st.column_config.TextColumn(width=110),
            "Book":    st.column_config.TextColumn(width=90),
            "Model %": st.column_config.TextColumn(width=80),
            "Devig %": st.column_config.TextColumn(width=80),
            "Edge":    st.column_config.TextColumn(width=70),
            "Vig":     st.column_config.TextColumn(width=60),
            "Stake":   st.column_config.TextColumn(width=100),
            "Status":  st.column_config.TextColumn(width=100),
        }
    )

st.markdown("---")
st.caption("""
**Model notes:** MLB rankings use Elo+FIP model (57.33% backtested accuracy).
NHL/NBA/NFL use devigged market only — no model edge computed until team Elo data is added.
Edge formula: Model Probability − No-Vig (MPTO devigged) Market Probability.
Beat closing line consistently by 2–5% = long-term profitable (Pinnacle/CLV methodology).
""")
