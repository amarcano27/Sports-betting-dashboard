"""
APEX ANALYTICS — AI Recommendations
Daily analysis: 10 structured slips + Top 20 props with full reasoning.
Data refreshes ~5 min after morning (7 AM ET) and midday (11:30 AM ET) odds pulls.
"""
import sys, json
from pathlib import Path
import streamlit as st
import pandas as pd
from datetime import datetime, timezone

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase
from dashboard.premium_styles import TOKENS
from dashboard.mobile_utils import inject_mobile_css

inject_mobile_css()

# ─────────────────────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_latest_recs() -> dict | None:
    try:
        rows = (supabase.table("ai_recommendations")
                .select("*").order("generated_at", desc=True)
                .limit(1).execute().data or [])
        if not rows:
            return None
        r = rows[0]
        slips     = json.loads(r["slips"])     if isinstance(r["slips"], str)     else r["slips"]
        top_props = json.loads(r["top_props"]) if isinstance(r["top_props"], str) else r["top_props"]
        return {
            "generated_at": r["generated_at"],
            "n_games":      r.get("n_games", 0),
            "n_plays":      r.get("n_plays", 0),
            "slips":        slips or [],
            "top_props":    top_props or [],
        }
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
SLIP_COLORS = {
    "CORRELATED":  TOKENS["green"],
    "ANCHOR":      TOKENS["cyan"],
    "VALUE_MIX":   TOKENS["amber"],
    "SWING":       TOKENS["purple"],
}
SLIP_ICONS = {
    "CORRELATED":  "🔗",
    "ANCHOR":      "⚓",
    "VALUE_MIX":   "⚡",
    "SWING":       "🎯",
}
CONF_COLORS = {
    "HIGH":     TOKENS["green"],
    "MED-HIGH": TOKENS["green"],
    "MED":      TOKENS["amber"],
    "LOW":      TOKENS["text_muted"],
}
STATUS_MAP = {
    ("HIGH",     True):  ("✅ BEST VALUE",  TOKENS["green"]),
    ("HIGH",     False): ("✅ STRONG",      TOKENS["green"]),
    ("MED-HIGH", True):  ("⚡ VALUE",       TOKENS["amber"]),
    ("MED-HIGH", False): ("⚡ PLAY",        TOKENS["amber"]),
    ("MED",      True):  ("🔄 LEAN",        TOKENS["text_muted"]),
    ("MED",      False): ("🔄 LEAN",        TOKENS["text_muted"]),
}


def fmt_odds(o) -> str:
    try:
        iv = int(o)
        return f"+{iv}" if iv > 0 else str(iv)
    except Exception:
        return str(o)


def slip_card(slip: dict, idx: int):
    stype  = slip.get("slip_type", "ANCHOR")
    color  = SLIP_COLORS.get(stype, TOKENS["cyan"])
    icon   = SLIP_ICONS.get(stype, "⚡")
    legs   = slip.get("legs", [])
    odds   = slip.get("combined_odds", 0)
    wp     = slip.get("win_prob", 0)
    ev50   = slip.get("ev_50", 0)
    stake  = slip.get("stake_rec", "$25-$50")
    payout = slip.get("target_payout", "")
    conf   = slip.get("confidence", "MED")
    tags   = slip.get("tags", [])
    reason = slip.get("reasoning", "")
    name   = slip.get("name", f"Slip {idx+1}")
    ev_color = TOKENS["green"] if ev50 > 0 else TOKENS["red"]

    with st.container():
        st.markdown(f"""
<div style="background:{TOKENS['bg_panel']};border:1px solid {color}44;
            border-left:4px solid {color};border-radius:10px;
            padding:0;margin-bottom:18px;overflow:hidden">

  <!-- Header -->
  <div style="background:{color}18;padding:14px 18px;
              display:flex;justify-content:space-between;align-items:center;
              flex-wrap:wrap;gap:8px">
    <div>
      <span style="font-size:13px;font-weight:800;color:{color}">
        {icon} SLIP {idx+1} — {stype}
      </span>
      <div style="font-size:12px;color:{TOKENS['text_muted']};margin-top:2px">
        {name}
      </div>
    </div>
    <div style="text-align:right">
      <div style="font-family:'JetBrains Mono',monospace;font-size:22px;
                  font-weight:800;color:{'#10B981' if odds > 0 else TOKENS['text_primary']}">
        {fmt_odds(odds)}
      </div>
      <div style="font-size:11px;color:{TOKENS['text_muted']}">
        Win prob: {wp:.0f}%
      </div>
    </div>
  </div>

  <!-- Reasoning -->
  <div style="padding:10px 18px;background:{TOKENS['bg_panel_2']};
              border-bottom:1px solid {TOKENS['border']};
              font-size:12px;color:{TOKENS['text_secondary']};font-style:italic">
    {reason}
  </div>

  <!-- Stats row -->
  <div style="padding:12px 18px;display:flex;gap:24px;flex-wrap:wrap;
              border-bottom:1px solid {TOKENS['border']}">
    <div>
      <div style="font-size:9px;color:{TOKENS['text_muted']};text-transform:uppercase">Stake</div>
      <div style="font-weight:700;color:{TOKENS['text_primary']}">{stake}</div>
    </div>
    <div>
      <div style="font-size:9px;color:{TOKENS['text_muted']};text-transform:uppercase">EV on $50</div>
      <div style="font-family:'JetBrains Mono',monospace;font-weight:700;color:{ev_color}">
        ${ev50:+.2f}
      </div>
    </div>
    <div>
      <div style="font-size:9px;color:{TOKENS['text_muted']};text-transform:uppercase">Confidence</div>
      <div style="color:{CONF_COLORS.get(conf, TOKENS['text_muted'])};font-weight:700">{conf}</div>
    </div>
    {"".join(f'<div style="background:{color}22;color:{color};padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700;align-self:center">{t}</div>' for t in tags[:3])}
  </div>

  <!-- Legs -->
  <div style="padding:12px 18px">
""", unsafe_allow_html=True)

        for li, leg in enumerate(legs):
            lconf    = leg.get("confidence", "MED")
            lfire    = leg.get("fire", "🔥")
            lcat     = leg.get("category", "")
            lodds    = leg.get("odds", 0)
            lline    = leg.get("line")
            lplayer  = leg.get("player", "")
            lside    = leg.get("side", "")
            ledge    = leg.get("edge_pct", 0)
            lreason  = leg.get("reasoning", "")
            ltime    = leg.get("game_time", "")
            lgame    = leg.get("game", "")
            lmodel   = leg.get("model_prob", 0)
            lmarket  = leg.get("market_prob", 0)
            lkelly   = leg.get("kelly_pct", 0)
            lplus    = leg.get("is_plus_money", False)
            lsport   = leg.get("sport", "")

            status_txt, status_clr = STATUS_MAP.get((lconf, lplus), ("⚡ PLAY", TOKENS["amber"]))
            odds_clr = TOKENS["green"] if lodds > 0 else TOKENS["text_primary"]

            line_display = f"O{lline}" if lline else lplayer.split()[-1]
            sport_icon = {"MLB": "⚾", "NBA": "🏀", "NHL": "🏒", "NFL": "🏈"}.get(lsport, "🏆")

            st.markdown(f"""
<div style="background:{TOKENS['bg_panel_2']};border-radius:8px;padding:12px;
            margin-bottom:8px;border:1px solid {TOKENS['border']}">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">
    <div style="flex:1">
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px">
        <span style="font-size:10px;font-weight:800;color:{TOKENS['text_muted']};
                     text-transform:uppercase">{sport_icon} LEG {li+1}</span>
        <span style="font-size:11px;font-weight:700;color:{status_clr};
                     background:{status_clr}22;padding:1px 6px;border-radius:3px">{status_txt}</span>
        <span style="font-size:11px;color:{TOKENS['text_muted']}">{lfire}</span>
      </div>
      <div style="font-size:15px;font-weight:800;color:{TOKENS['text_primary']}">
        {lplayer} {line_display}
      </div>
      <div style="font-size:11px;color:{TOKENS['text_muted']};margin-top:2px">
        {lcat} · {lgame.split('@')[0].strip().split()[-1] if '@' in lgame else lgame} @ {lgame.split('@')[1].strip().split()[-1] if '@' in lgame else ''} · {ltime}
      </div>
    </div>
    <div style="text-align:right">
      <div style="font-family:'JetBrains Mono',monospace;font-size:20px;
                  font-weight:800;color:{odds_clr}">{fmt_odds(lodds)}</div>
      <div style="font-size:10px;color:{TOKENS['green'] if ledge >= 5 else TOKENS['amber']};
                  font-weight:700">Edge +{ledge:.1f}%</div>
    </div>
  </div>
  <div style="background:{TOKENS['bg_main']};border-radius:6px;padding:8px 10px;
              margin-top:8px;font-size:11px;color:{TOKENS['text_secondary']}">
    {lreason[:160]}{'...' if len(lreason) > 160 else ''}
  </div>
  <div style="display:flex;gap:16px;margin-top:8px;font-size:10px;color:{TOKENS['text_muted']}">
    <span>Model: <b style="color:{TOKENS['text_primary']}">{lmodel:.0f}%</b></span>
    <span>Mkt: <b>{lmarket:.0f}%</b></span>
    <span>Kelly: <b style="color:{TOKENS['amber']}">{lkelly:.1f}%</b></span>
  </div>
</div>
""", unsafe_allow_html=True)

        st.markdown("</div></div>", unsafe_allow_html=True)


def prop_table(props: list[dict]):
    rows = []
    for i, p in enumerate(props, 1):
        conf = p.get("confidence", "MED")
        plus = p.get("is_plus_money", False)
        status, _ = STATUS_MAP.get((conf, plus), ("⚡ PLAY", TOKENS["amber"]))
        rows.append({
            "#":        i,
            "Fire":     p.get("fire", "🔥"),
            "Status":   status,
            "Player / Team": p.get("player", "?"),
            "Prop":     f"{p.get('side','')} {p.get('line','')} {p.get('category','')}".strip(),
            "Odds":     fmt_odds(p.get("odds", 0)),
            "Model %":  f"{p.get('model_prob',0):.0f}%",
            "Mkt %":    f"{p.get('market_prob',0):.0f}%",
            "Edge":     f"+{p.get('edge_pct',0):.1f}%",
            "Kelly":    f"{p.get('kelly_pct',0):.1f}%",
            "Game":     (p.get("game","?").replace(" @ ", "@")
                         .split("@")[0].strip().split()[-1] + "@" +
                         p.get("game","?").split("@")[-1].strip().split()[-1]
                         if "@" in p.get("game","") else p.get("game","?")),
            "Time":     p.get("game_time", "?"),
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True,
            height=min(600, 36 * len(rows) + 38),
            column_config={
                "#":             st.column_config.NumberColumn(width=40),
                "Fire":          st.column_config.TextColumn(width=50),
                "Status":        st.column_config.TextColumn(width=110),
                "Player / Team": st.column_config.TextColumn(width=175),
                "Prop":          st.column_config.TextColumn(width=160),
                "Odds":          st.column_config.TextColumn(width=75),
                "Model %":       st.column_config.TextColumn(width=75),
                "Mkt %":         st.column_config.TextColumn(width=65),
                "Edge":          st.column_config.TextColumn(width=70),
                "Kelly":         st.column_config.TextColumn(width=65),
                "Game":          st.column_config.TextColumn(width=120),
                "Time":          st.column_config.TextColumn(width=95),
            })


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
st.title("🤖 AI Recommendations")
st.caption("Auto-generated daily slips + top props · Refreshed 7 AM ET and 11:30 AM ET · Based on Elo+FIP model, Poisson K props, correlation analysis")

recs = load_latest_recs()

if recs is None:
    st.info("""
**No AI recommendations generated yet.**

The first batch is generated automatically after the morning odds pull (7 AM ET daily).
Click below to generate now.
""")
    if st.button("⚡ Generate Recommendations Now", type="primary"):
        with st.spinner("Analyzing today's slate..."):
            try:
                import subprocess
                r = subprocess.run(
                    [sys.executable, "workers/build_ai_recommendations.py"],
                    capture_output=True, text=True, cwd=str(project_root), timeout=120
                )
                st.cache_data.clear()
                if r.returncode == 0:
                    st.success("Done! Refresh the page.")
                    st.rerun()
                else:
                    st.error(r.stderr[-500:] or r.stdout[-500:])
            except Exception as e:
                st.error(str(e))
# ── recs exist — render the full dashboard ───────────────────
if recs is None:
    st.stop()

# Safe fallback for import-time testing (st.stop() is no-op outside Streamlit)
recs = recs or {"slips": [], "top_props": [], "n_plays": 0, "generated_at": "", "n_games": 0}

# ── Header strip ─────────────────────────────────────────────
try:
    gen_ts = datetime.fromisoformat(recs["generated_at"].replace("Z", "+00:00"))
    age_min = (datetime.now(timezone.utc) - gen_ts).total_seconds() / 60
    gen_str = gen_ts.strftime("%b %d %Y %I:%M %p ET")
    freshness = f"✅ Fresh ({age_min:.0f} min ago)" if age_min < 120 else f"⚠️ {age_min/60:.1f}h old — refresh odds in Data Sync"
    fresh_color = TOKENS["green"] if age_min < 120 else TOKENS["amber"]
except Exception:
    gen_str = "Unknown"
    freshness = "—"
    fresh_color = TOKENS["text_muted"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Generated",    gen_str[:12])
c2.metric("Slips Built",  len(recs["slips"]))
c3.metric("Top Props",    len(recs["top_props"]))
c4.metric("Plays Analyzed", recs.get("n_plays", 0))

st.markdown(f"""
<div style="background:{fresh_color}18;border:1px solid {fresh_color}44;
            border-radius:6px;padding:8px 14px;margin:10px 0;
            font-size:12px;font-weight:700;color:{fresh_color}">
  {freshness}
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ── Main tabs ─────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    f"🎯 Today's Slips ({len(recs['slips'])})",
    f"📋 Top Props ({len(recs['top_props'])})",
    "⚙️ Rebuild",
])

with tab1:
    if not recs["slips"]:
        st.info("No slips generated yet — odds data may be empty. Fetch odds first.")
    else:
        # Group by type
        by_type = {"CORRELATED": [], "ANCHOR": [], "VALUE_MIX": [], "SWING": []}
        for s in recs["slips"]:
            st_key = s.get("slip_type", "ANCHOR")
            by_type.setdefault(st_key, []).append(s)

        type_labels = {
            "CORRELATED": "🔗 Correlated (K Prop + Same-Game ML)",
            "ANCHOR":     "⚓ Anchor (High Confidence 2-Leg)",
            "VALUE_MIX":  "⚡ Value Mix (3-Leg Diversified)",
            "SWING":      "🎯 Swing (4-Leg High Payout)",
        }

        global_idx = 0
        for stype, label in type_labels.items():
            group = by_type.get(stype, [])
            if not group:
                continue
            st.markdown(f"""
<div style="margin:16px 0 10px;padding-bottom:6px;border-bottom:1px solid {TOKENS['border']}">
  <span style="font-size:14px;font-weight:800;color:{SLIP_COLORS.get(stype,TOKENS['cyan'])}">{label}</span>
  <span style="font-size:11px;color:{TOKENS['text_muted']};margin-left:8px">{len(group)} slip(s)</span>
</div>
""", unsafe_allow_html=True)
            for s in group:
                slip_card(s, global_idx)
                global_idx += 1

with tab2:
    if not recs["top_props"]:
        st.info("No props ranked yet.")
    else:
        st.subheader("📋 Top Plays of the Day")
        st.caption("""
Ranked by edge (model probability − devigged market probability).
🔥🔥🔥 = HIGH confidence edge ≥7% · 🔥🔥 = MED-HIGH ≥4% · 🔥 = MED ≥2%
✅ BEST VALUE = plus-money + high edge · ✅ STRONG = high edge · ⚡ PLAY = positive edge
""")
        prop_table(recs["top_props"])

        # Individual reasoning cards for top 5
        st.markdown("---")
        st.subheader("🔍 Top 5 Deep Dives")
        for i, p in enumerate(recs["top_props"][:5], 1):
            conf = p.get("confidence", "MED")
            plus = p.get("is_plus_money", False)
            status, sclr = STATUS_MAP.get((conf, plus), ("⚡ PLAY", TOKENS["amber"]))
            sport_icon = {"MLB": "⚾", "NBA": "🏀", "NHL": "🏒", "NFL": "🏈"}.get(p.get("sport",""), "🏆")
            lline = p.get("line")
            line_str = f"O{lline}" if lline else ""

            st.markdown(f"""
<div style="background:{TOKENS['bg_panel']};border:1px solid {sclr}44;
            border-left:4px solid {sclr};border-radius:8px;
            padding:16px;margin-bottom:12px">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;
              flex-wrap:wrap;gap:8px;margin-bottom:10px">
    <div>
      <span style="font-size:10px;color:{TOKENS['text_muted']};font-weight:700;
                   text-transform:uppercase">{sport_icon} #{i} · {p.get('category','')}</span>
      <div style="font-size:17px;font-weight:800;color:{TOKENS['text_primary']};margin-top:4px">
        {p.get('player','')} {line_str}
      </div>
      <div style="font-size:11px;color:{TOKENS['text_muted']};margin-top:2px">
        {p.get('game','')} · {p.get('game_time','')}
      </div>
    </div>
    <div style="text-align:right">
      <div style="font-size:11px;font-weight:800;background:{sclr};color:#050B14;
                  padding:3px 10px;border-radius:4px">{status}</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:22px;
                  font-weight:800;color:{'#10B981' if p.get('odds',0)>0 else TOKENS['text_primary']};
                  margin-top:6px">{fmt_odds(p.get('odds',0))}</div>
    </div>
  </div>
  <div style="background:{TOKENS['bg_panel_2']};border-radius:6px;padding:10px 12px;
              font-size:12px;color:{TOKENS['text_secondary']};line-height:1.6">
    {p.get('fire','🔥')} {p.get('reasoning','')}
  </div>
  <div style="display:flex;gap:20px;margin-top:10px;font-size:11px;color:{TOKENS['text_muted']}">
    <span>Model: <b style="color:{TOKENS['text_primary']}">{p.get('model_prob',0):.0f}%</b></span>
    <span>Market: <b>{p.get('market_prob',0):.0f}%</b></span>
    <span>Edge: <b style="color:{TOKENS['green']}">+{p.get('edge_pct',0):.1f}%</b></span>
    <span>Kelly: <b style="color:{TOKENS['amber']}">{p.get('kelly_pct',0):.1f}% bankroll</b></span>
  </div>
</div>
""", unsafe_allow_html=True)

with tab3:
    st.subheader("⚙️ Rebuild Recommendations")
    st.caption("Manually trigger a new analysis run. Normally this runs automatically after the scheduled odds pulls.")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
**Schedule:** Auto-runs daily
- 🌅 **7:00 AM ET** — Morning scan
- ☀️ **11:35 AM ET** — Pre-game midday
- Runs ~5 min after odds are refreshed

**Data sources:**
- Odds: The Odds API (4,000+ rows)
- Pitchers: MLB StatsAPI (live FIP/K9)
- Players: NBA Stats API (game logs)
- Model: Elo+FIP + Poisson
""")
    with col2:
        if st.button("🤖 Rebuild Now", type="primary", use_container_width=True):
            with st.spinner("Analyzing today's slate — takes ~30 seconds..."):
                try:
                    import subprocess
                    r = subprocess.run(
                        [sys.executable, "workers/build_ai_recommendations.py"],
                        capture_output=True, text=True, cwd=str(project_root), timeout=120
                    )
                    st.cache_data.clear()
                    if r.returncode == 0:
                        st.success("Done! Switch to Today's Slips tab.")
                        st.code(r.stdout[-800:] if r.stdout else "(no output)")
                    else:
                        st.error("Build failed:")
                        st.code((r.stderr or r.stdout)[-1000:])
                except Exception as e:
                    st.error(str(e))
