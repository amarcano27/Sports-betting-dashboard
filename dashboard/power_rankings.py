"""
APEX ANALYTICS - Power Rankings
Live team Elo ratings from real standings + line movement leaderboard.
"""
import sys
from pathlib import Path
import streamlit as st
import pandas as pd

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.elo_seeds import (
    get_mlb_elo_seeds, get_nba_elo_seeds, get_nhl_elo_seeds,
    BASE_ELO,
)
from utils.line_movement import get_line_movements, SIGNAL_COLORS, SIGNAL_DESCRIPTIONS
from services.db import supabase
from dashboard.premium_styles import TOKENS
from dashboard.mobile_utils import inject_mobile_css

inject_mobile_css()

st.title("🏆 Power Rankings")
st.caption("Live team strength ratings from real standings · Line movement alerts")

sport = st.selectbox("Sport", ["MLB", "NBA", "NHL"], label_visibility="collapsed")

# ── Elo ratings table ────────────────────────────────────────
@st.cache_data(ttl=3600)
def _mlb(): return get_mlb_elo_seeds()
@st.cache_data(ttl=3600)
def _nba(): return get_nba_elo_seeds()
@st.cache_data(ttl=3600)
def _nhl(): return get_nhl_elo_seeds()

seeds = {"MLB": _mlb, "NBA": _nba, "NHL": _nhl}[sport]()

if seeds:
    rows = []
    for name, elo in sorted(seeds.items(), key=lambda x: -x[1]):
        diff  = elo - BASE_ELO
        tier  = ("Elite"    if diff >= 100 else
                 "Strong"   if diff >= 40  else
                 "Average"  if diff >= -40 else
                 "Weak"     if diff >= -100 else "Rebuilding")
        tier_c = {"Elite":    TOKENS["green"],
                  "Strong":   "#1A7F37",
                  "Average":  TOKENS["amber"],
                  "Weak":     TOKENS["red"],
                  "Rebuilding": TOKENS["text_dim"]}.get(tier, TOKENS["text_muted"])
        rows.append({
            "Team":  name,
            "Elo":   round(elo),
            "±":     f"{diff:+.0f}",
            "Tier":  tier,
            "_tier_c": tier_c,
        })

    df = pd.DataFrame(rows)
    df.insert(0, "#", range(1, len(df) + 1))

    st.subheader(f"📊 {sport} Elo Power Rankings")
    st.caption("Based on current W/L records + Pythagorean run differential. Updates every hour.")

    # Colour-band the tier column
    st.dataframe(
        df.drop(columns=["_tier_c"]),
        use_container_width=True,
        hide_index=True,
        column_config={
            "#":    st.column_config.NumberColumn(width=45),
            "Team": st.column_config.TextColumn(width=220),
            "Elo":  st.column_config.NumberColumn(width=75),
            "±":    st.column_config.TextColumn(width=70),
            "Tier": st.column_config.TextColumn(width=100),
        }
    )

    # Quick visual bar chart
    import plotly.graph_objects as go
    top20 = df.head(20)
    bar_colors = [r["_tier_c"] for _, r in top20.iterrows()]
    fig = go.Figure(go.Bar(
        x=top20["Team"].apply(lambda n: n.split()[-1]),
        y=top20["Elo"],
        marker_color=bar_colors,
        text=top20["Elo"].astype(str),
        textposition="outside",
    ))
    fig.add_hline(y=BASE_ELO, line_dash="dot",
                  line_color=TOKENS["amber"], line_width=1)
    fig.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=dict(color=TOKENS["text_muted"], size=10)),
        yaxis=dict(visible=False),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning(f"Could not load {sport} standings. API may be temporarily unavailable.")

st.markdown("---")

# ── Line movement alerts ─────────────────────────────────────
st.subheader("⚡ Line Movement Alerts")
st.caption("Compares opening odds to current odds. Steam = 20+ point move = sharp money signal.")

@st.cache_data(ttl=120)
def _load_games(sp):
    return supabase.table("games").select("*").eq("sport", sp).execute().data or []

games = _load_games(sport)
if not games:
    st.info(f"No {sport} games in DB. Fetch odds first via Data Sync.")
    st.stop()

moves = get_line_movements(supabase, [g["id"] for g in games])

alerts = []
for g in games:
    gm = moves.get(g["id"], {})
    for team, mv in gm.items():
        sig = mv.get("move", {}).get("signal", "FLAT")
        if sig in ("STEAM", "MOVE"):
            alerts.append({
                "game":      f"{g['away_team'].split()[-1]} @ {g['home_team'].split()[-1]}",
                "team":      team.split()[-1],
                "signal":    sig,
                "open":      mv.get("open"),
                "current":   mv.get("current"),
                "move":      mv.get("move", {}),
                "snapshots": mv.get("n_snapshots", 0),
            })

alerts.sort(key=lambda x: {"STEAM": 0, "MOVE": 1}.get(x["signal"], 2))

if alerts:
    for a in alerts:
        sc    = SIGNAL_COLORS.get(a["signal"], TOKENS["text_muted"])
        op    = a["open"]
        cu    = a["current"]
        o_str = (f"+{op}" if op and op > 0 else str(op)) if op else "—"
        c_str = (f"+{cu}" if cu and cu > 0 else str(cu)) if cu else "—"
        st.markdown(f"""
<div style="background:{sc}18;border:1px solid {sc}44;border-left:4px solid {sc};
            border-radius:8px;padding:14px 18px;margin-bottom:10px">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
    <div>
      <span style="font-size:13px;font-weight:800;color:{sc}">
        {'⚡ STEAM MOVE' if a['signal']=='STEAM' else '📈 LINE MOVE'}
      </span>
      <span style="font-size:13px;color:{TOKENS['text_primary']};font-weight:700;margin-left:10px">
        {a['team']} ML · {a['game']}
      </span>
    </div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:16px;font-weight:800;color:{sc}">
      {o_str} → {c_str}
    </div>
  </div>
  <div style="font-size:12px;color:{TOKENS['text_muted']};margin-top:6px">
    {SIGNAL_DESCRIPTIONS.get(a['signal'],'')} · {a['snapshots']} price snapshots on file.
  </div>
</div>""", unsafe_allow_html=True)
else:
    st.info("No significant line moves detected in today's slate. Check back after more odds snapshots accumulate.")
    st.caption("Line movement becomes meaningful after 2–3 odds refreshes across the day.")
