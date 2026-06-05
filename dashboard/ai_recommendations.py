"""
APEX ANALYTICS — AI Recommendations
=====================================
Tab 1: 🧠 AI Analysis  — Full LLM write-up (Claude API), priority rankings,
                          slips, K props, MLs, hitter props
Tab 2: 🎯 Math Slips   — Poisson/Elo engine slips + top props table
Tab 3: ⚙️  Rebuild      — Manual trigger
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
        llm_raw   = r.get("llm_analysis")
        if isinstance(llm_raw, str):
            try:
                llm_analysis = json.loads(llm_raw)
            except Exception:
                llm_analysis = {"error": "JSON parse failed", "raw": llm_raw}
        else:
            llm_analysis = llm_raw or {}

        return {
            "generated_at": r["generated_at"],
            "n_games":      r.get("n_games", 0),
            "n_plays":      r.get("n_plays", 0),
            "slips":        slips or [],
            "top_props":    top_props or [],
            "llm_analysis": llm_analysis,
        }
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────
# STYLE HELPERS
# ─────────────────────────────────────────────────────────────
SLIP_COLORS = {
    "CORRELATED":  TOKENS["green"],
    "ANCHOR":      TOKENS["cyan"],
    "VALUE_MIX":   TOKENS["amber"],
    "VALUE":       TOKENS["amber"],
    "SWING":       TOKENS["purple"],
}
SLIP_ICONS = {
    "CORRELATED": "🔗", "ANCHOR": "⚓", "VALUE_MIX": "⚡",
    "VALUE": "⚡", "SWING": "🎯",
}
CONF_COLORS = {
    "HIGH":     TOKENS["green"],
    "MED-HIGH": TOKENS["green"],
    "MED":      TOKENS["amber"],
    "LOW":      TOKENS["text_muted"],
}
STATUS_MAP = {
    ("HIGH",     True):  ("✅ BEST VALUE", TOKENS["green"]),
    ("HIGH",     False): ("✅ STRONG",     TOKENS["green"]),
    ("MED-HIGH", True):  ("⚡ VALUE",      TOKENS["amber"]),
    ("MED-HIGH", False): ("⚡ PLAY",       TOKENS["amber"]),
    ("MED",      True):  ("🔄 LEAN",       TOKENS["text_muted"]),
    ("MED",      False): ("🔄 LEAN",       TOKENS["text_muted"]),
}
CONF_TO_STATUS = {
    "HIGH":     ("✅ STRONG",  TOKENS["green"]),
    "MED-HIGH": ("⚡ PLAY",    TOKENS["amber"]),
    "MED":      ("🔄 LEAN",    TOKENS["text_muted"]),
    "LOW":      ("🚫 SKIP",    TOKENS["red"] if "red" in TOKENS else "#EF4444"),
}

def fmt_odds(o) -> str:
    try:
        iv = int(float(str(o).replace("+",""))) if str(o).startswith("+") else int(float(str(o)))
        return f"+{iv}" if iv > 0 else str(iv)
    except Exception:
        return str(o)

def conf_color(c: str) -> str:
    return CONF_COLORS.get(c, TOKENS["text_muted"])


# ─────────────────────────────────────────────────────────────
# LLM ANALYSIS RENDERERS
# ─────────────────────────────────────────────────────────────

def render_executive_summary(llm: dict):
    summary = llm.get("executive_summary", "")
    if not summary:
        return
    st.markdown(f"""
<div style="background:{TOKENS['bg_panel']};border:1px solid {TOKENS['cyan']}44;
            border-left:4px solid {TOKENS['cyan']};border-radius:10px;
            padding:16px 20px;margin-bottom:20px">
  <div style="font-size:11px;font-weight:800;color:{TOKENS['cyan']};
              text-transform:uppercase;margin-bottom:8px">📌 TODAY'S KEY NARRATIVE</div>
  <div style="font-size:14px;color:{TOKENS['text_primary']};line-height:1.7">{summary}</div>
</div>
""", unsafe_allow_html=True)


def render_priority_rankings(llm: dict):
    rankings = llm.get("priority_rankings", [])
    if not rankings:
        return

    st.markdown(f"""
<div style="margin:20px 0 12px;padding-bottom:6px;border-bottom:2px solid {TOKENS['amber']}">
  <span style="font-size:16px;font-weight:800;color:{TOKENS['amber']}">
    📊 PRIORITY RANKINGS
  </span>
  <span style="font-size:12px;color:{TOKENS['text_muted']};margin-left:10px">
    Ranked by edge % · Implied vs real estimated probability
  </span>
</div>
""", unsafe_allow_html=True)

    rows = []
    for r in rankings:
        rank = r.get("rank", "")
        medal = r.get("medal", str(rank))
        rows.append({
            "Rank":        f"{medal}",
            "Play":        r.get("play", r.get("ref", "")),
            "Game":        r.get("game", ""),
            "Odds":        r.get("odds", ""),
            "Implied %":   r.get("implied_pct", ""),
            "Real Est %":  r.get("real_est_pct", ""),
            "Edge":        r.get("edge", ""),
            "Stake":       r.get("stake_rec", ""),
            "Best Use":    r.get("best_use", r.get("one_liner", "")),
        })

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True,
            height=min(700, 36 * len(rows) + 38),
            column_config={
                "Rank":       st.column_config.TextColumn(width=55),
                "Play":       st.column_config.TextColumn(width=220),
                "Game":       st.column_config.TextColumn(width=160),
                "Odds":       st.column_config.TextColumn(width=75),
                "Implied %":  st.column_config.TextColumn(width=85),
                "Real Est %": st.column_config.TextColumn(width=95),
                "Edge":       st.column_config.TextColumn(width=80),
                "Stake":      st.column_config.TextColumn(width=90),
                "Best Use":   st.column_config.TextColumn(width=260),
            })


def _prop_section_card(props: list[dict], title: str, icon: str, accent: str):
    if not props:
        return

    st.markdown(f"""
<div style="margin:24px 0 14px;padding-bottom:6px;border-bottom:2px solid {accent}">
  <span style="font-size:15px;font-weight:800;color:{accent}">{icon} {title}</span>
  <span style="font-size:12px;color:{TOKENS['text_muted']};margin-left:10px">{len(props)} plays</span>
</div>
""", unsafe_allow_html=True)

    for p in props:
        conf = p.get("confidence", "MED")
        status_txt, status_clr = CONF_TO_STATUS.get(conf, ("⚡ PLAY", TOKENS["amber"]))
        is_value = "VALUE" in p.get("status", "")
        if is_value:
            status_txt = p.get("status", status_txt)
        fire  = p.get("fire", "🔥")
        odds  = p.get("odds", "")
        edge  = p.get("edge", "")
        stake = p.get("stake_rec", "")
        ref   = p.get("ref", "")

        play_label = (p.get("play") or
                      f"{p.get('pitcher', p.get('player', p.get('team', '')))} "
                      f"{p.get('prop', p.get('line',''))}")

        reasoning = p.get("reasoning", "")
        game      = p.get("game", "")
        time_str  = p.get("time", "")

        model_est = p.get("model_est_pct", p.get("real_est_pct", ""))
        implied   = p.get("implied_pct", "")

        odds_color = TOKENS["green"] if str(odds).startswith("+") else TOKENS["text_primary"]

        st.markdown(f"""
<div style="background:{TOKENS['bg_panel']};border:1px solid {status_clr}33;
            border-left:4px solid {status_clr};border-radius:8px;
            padding:14px 16px;margin-bottom:10px">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;
              flex-wrap:wrap;gap:8px;margin-bottom:8px">
    <div style="flex:1">
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px">
        <span style="font-size:10px;font-weight:800;color:{TOKENS['text_muted']};
                     text-transform:uppercase">{ref}</span>
        <span style="font-size:11px;font-weight:700;color:{status_clr};
                     background:{status_clr}22;padding:2px 7px;border-radius:3px">{status_txt}</span>
        <span style="font-size:12px">{fire}</span>
      </div>
      <div style="font-size:15px;font-weight:800;color:{TOKENS['text_primary']}">{play_label}</div>
      <div style="font-size:11px;color:{TOKENS['text_muted']};margin-top:2px">{game} · {time_str}</div>
    </div>
    <div style="text-align:right">
      <div style="font-family:'JetBrains Mono',monospace;font-size:22px;
                  font-weight:800;color:{odds_color}">{odds}</div>
      <div style="font-size:11px;color:{TOKENS['green']};font-weight:700">{edge}</div>
    </div>
  </div>
  <div style="background:{TOKENS['bg_panel_2']};border-radius:6px;padding:10px 12px;
              font-size:12px;color:{TOKENS['text_secondary']};line-height:1.6">
    {reasoning}
  </div>
  <div style="display:flex;gap:20px;margin-top:8px;font-size:10px;color:{TOKENS['text_muted']}">
    {"<span>Implied: <b>" + implied + "</b></span>" if implied else ""}
    {"<span>Model Est: <b style='color:" + TOKENS['green'] + "'>" + model_est + "</b></span>" if model_est else ""}
    {"<span>Stake: <b style='color:" + TOKENS['amber'] + "'>" + stake + "</b></span>" if stake else ""}
  </div>
</div>
""", unsafe_allow_html=True)


def render_llm_slips(llm: dict):
    slips = llm.get("slips", [])
    if not slips:
        return

    st.markdown(f"""
<div style="margin:24px 0 14px;padding-bottom:6px;border-bottom:2px solid {TOKENS['purple']}">
  <span style="font-size:15px;font-weight:800;color:{TOKENS['purple']}">
    🎯 AI-RECOMMENDED SLIPS
  </span>
  <span style="font-size:12px;color:{TOKENS['text_muted']};margin-left:10px">
    Built by Claude · {len(slips)} slips
  </span>
</div>
""", unsafe_allow_html=True)

    for slip in slips:
        stype   = slip.get("type", "ANCHOR").upper()
        color   = SLIP_COLORS.get(stype, TOKENS["cyan"])
        icon    = SLIP_ICONS.get(stype, "⚡")
        legs    = slip.get("legs", [])
        name    = slip.get("name", f"Slip {slip.get('number','')}")
        stake   = slip.get("stake_rec", "")
        target  = slip.get("target", "")
        conf    = slip.get("confidence", "MED")
        c_odds  = slip.get("combined_odds_approx", slip.get("combined_odds", ""))
        win_prob = slip.get("win_prob_approx", "")
        note    = slip.get("slip_note", slip.get("reasoning", ""))

        legs_html = ""
        for li, leg in enumerate(legs):
            play    = leg.get("play", "")
            lodds   = leg.get("odds", "")
            lconf   = leg.get("confidence", "MED")
            lfire   = leg.get("fire", "🔥")
            lref    = leg.get("ref", "")
            lreason = leg.get("key_reason", "")
            lcolor  = conf_color(lconf)
            l_odds_color = TOKENS["green"] if str(lodds).startswith("+") else TOKENS["text_primary"]
            reason_html = (f"<div style='font-size:11px;color:{TOKENS['text_secondary']};margin-top:3px'>"
                           f"{lreason}</div>") if lreason else ""
            legs_html += f"""
<div style="background:{TOKENS['bg_panel_2']};border-radius:8px;padding:10px 12px;
            margin-bottom:8px;border:1px solid {TOKENS['border']}">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px">
    <div style="flex:1">
      <div style="font-size:10px;color:{TOKENS['text_muted']};font-weight:700;
                  text-transform:uppercase;margin-bottom:3px">
        LEG {li+1} {lfire} <span style="color:{lcolor}">{lref}</span>
      </div>
      <div style="font-size:14px;font-weight:800;color:{TOKENS['text_primary']}">{play}</div>
      {reason_html}
    </div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:18px;
                font-weight:800;color:{l_odds_color}">{lodds}</div>
  </div>
</div>"""

        st.markdown(f"""
<div style="background:{TOKENS['bg_panel']};border:1px solid {color}44;
            border-left:4px solid {color};border-radius:10px;
            padding:0;margin-bottom:18px;overflow:hidden">
  <div style="background:{color}18;padding:14px 18px;
              display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
    <div>
      <span style="font-size:13px;font-weight:800;color:{color}">
        {icon} SLIP {slip.get('number','')} — {stype}
      </span>
      <div style="font-size:12px;color:{TOKENS['text_muted']};margin-top:2px">{name}</div>
    </div>
    <div style="text-align:right">
      <div style="font-family:'JetBrains Mono',monospace;font-size:20px;font-weight:800;
                  color:{TOKENS['green'] if str(c_odds).startswith('+') else TOKENS['text_primary']}">{c_odds}</div>
      <div style="font-size:11px;color:{TOKENS['text_muted']}">Win prob: {win_prob}</div>
    </div>
  </div>
  <div style="padding:10px 18px;background:{TOKENS['bg_panel_2']};
              border-bottom:1px solid {TOKENS['border']};
              font-size:12px;color:{TOKENS['text_secondary']};font-style:italic">{note}</div>
  <div style="padding:10px 18px;display:flex;gap:24px;flex-wrap:wrap;
              border-bottom:1px solid {TOKENS['border']}">
    <div>
      <div style="font-size:9px;color:{TOKENS['text_muted']};text-transform:uppercase">Stake</div>
      <div style="font-weight:700;color:{TOKENS['text_primary']}">{stake}</div>
    </div>
    <div>
      <div style="font-size:9px;color:{TOKENS['text_muted']};text-transform:uppercase">Target</div>
      <div style="font-weight:700;color:{TOKENS['amber']}">{target}</div>
    </div>
    <div>
      <div style="font-size:9px;color:{TOKENS['text_muted']};text-transform:uppercase">Conf</div>
      <div style="font-weight:700;color:{conf_color(conf)}">{conf}</div>
    </div>
  </div>
  <div style="padding:12px 18px">{legs_html}</div>
</div>
""", unsafe_allow_html=True)


def render_skips(llm: dict):
    skips = llm.get("skips", [])
    if not skips:
        return
    st.markdown(f"""
<div style="margin:20px 0 10px;padding-bottom:6px;border-bottom:1px solid {TOKENS['border']}">
  <span style="font-size:13px;font-weight:800;color:{TOKENS['text_muted']}">
    🚫 SKIPS — DO NOT BET
  </span>
</div>
""", unsafe_allow_html=True)
    for s in skips:
        st.markdown(f"""
<div style="background:{TOKENS['bg_panel']};border:1px solid {TOKENS['border']};
            border-left:3px solid #EF4444;border-radius:6px;
            padding:8px 14px;margin-bottom:6px;
            display:flex;justify-content:space-between;align-items:center">
  <div>
    <span style="font-size:12px;font-weight:700;color:{TOKENS['text_primary']}">{s.get('ref','')} · {s.get('play','')}</span>
    <div style="font-size:11px;color:{TOKENS['text_muted']};margin-top:2px">{s.get('reason','')}</div>
  </div>
  <span style="font-size:11px;color:#EF4444;font-weight:700">{s.get('odds','')}</span>
</div>
""", unsafe_allow_html=True)


def render_full_writeup(llm: dict):
    writeup = llm.get("full_markdown_writeup", "")
    if not writeup:
        return
    st.markdown("---")
    st.markdown(f"""
<div style="margin:20px 0 10px">
  <span style="font-size:14px;font-weight:800;color:{TOKENS['cyan']}">
    📄 FULL ANALYSIS WRITE-UP
  </span>
  <span style="font-size:11px;color:{TOKENS['text_muted']};margin-left:8px">
    AI-generated · mirrors Excel betting cart style
  </span>
</div>
""", unsafe_allow_html=True)
    st.markdown(writeup)


def render_slate_breakdown(llm: dict):
    slate = llm.get("slate_breakdown", [])
    if not slate:
        return

    st.markdown(f"""
<div style="margin:24px 0 12px;padding-bottom:6px;border-bottom:2px solid {TOKENS['cyan']}">
  <span style="font-size:15px;font-weight:800;color:{TOKENS['cyan']}">⚾ TODAY'S FULL SLATE</span>
  <span style="font-size:12px;color:{TOKENS['text_muted']};margin-left:10px">{len(slate)} games</span>
</div>
""", unsafe_allow_html=True)

    rows = []
    for g in slate:
        rating = g.get("rating", "")
        pick   = g.get("pick", "")
        clr    = (TOKENS["green"] if "STRONG" in rating or "VALUE" in rating
                  else TOKENS["amber"] if "LEAN" in rating
                  else "#EF4444" if "SKIP" in rating
                  else TOKENS["text_muted"])
        rows.append({
            "#":          g.get("number", ""),
            "Time":       g.get("time", ""),
            "Game":       g.get("game", ""),
            "Away ML":    g.get("away_ml", ""),
            "Home ML":    g.get("home_ml", ""),
            "Starters":   f"{g.get('away_pitcher','')} vs {g.get('home_pitcher','')}",
            "Pick":       pick,
            "Rating":     rating,
            "Reasoning":  g.get("reasoning", "")[:120] + ("…" if len(g.get("reasoning","")) > 120 else ""),
        })

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True,
            height=min(700, 38 * len(rows) + 38),
            column_config={
                "#":         st.column_config.NumberColumn(width=40),
                "Time":      st.column_config.TextColumn(width=90),
                "Game":      st.column_config.TextColumn(width=190),
                "Away ML":   st.column_config.TextColumn(width=75),
                "Home ML":   st.column_config.TextColumn(width=75),
                "Starters":  st.column_config.TextColumn(width=250),
                "Pick":      st.column_config.TextColumn(width=130),
                "Rating":    st.column_config.TextColumn(width=110),
                "Reasoning": st.column_config.TextColumn(width=400),
            })


def render_llm_analysis_tab(llm: dict):
    """Full LLM analysis — primary tab."""
    if not llm:
        st.info("No LLM analysis generated yet. Click **Rebuild** to run Claude analysis.")
        return

    if "error" in llm:
        err = llm["error"]
        if "ANTHROPIC_API_KEY" in err:
            st.error("🔑 **ANTHROPIC_API_KEY not configured.** Add it to your GitHub Secrets and Streamlit Cloud secrets to enable LLM analysis.")
        else:
            st.error(f"LLM analysis failed: {err}")
        if llm.get("raw_response"):
            with st.expander("📄 Raw response (partial parse)"):
                st.text(llm["raw_response"][:3000])
        return

    # Model info badge
    model = llm.get("model_used", "claude")
    n_props = llm.get("n_props", "?")
    n_slips = len(llm.get("slips", []))
    st.markdown(f"""
<div style="background:{TOKENS['bg_panel']};border:1px solid {TOKENS['border']};
            border-radius:6px;padding:8px 14px;margin-bottom:16px;
            display:flex;gap:20px;align-items:center;flex-wrap:wrap">
  <span style="font-size:11px;color:{TOKENS['cyan']};font-weight:700">🤖 {model}</span>
  <span style="font-size:11px;color:{TOKENS['text_muted']}">
    {n_props} plays analyzed · {n_slips} slips built · {len(llm.get('priority_rankings',[]))} ranked
  </span>
</div>
""", unsafe_allow_html=True)

    # 1. Executive summary
    render_executive_summary(llm)

    # 2. Priority rankings table
    render_priority_rankings(llm)

    st.markdown("---")

    # 3. AI Slips
    render_llm_slips(llm)

    st.markdown("---")

    # 4. Pitcher K props
    _prop_section_card(
        llm.get("pitcher_k_props", []),
        "PITCHER STRIKEOUT PROPS",
        "⚾",
        TOKENS["cyan"],
    )

    # 5. Hitter props
    _prop_section_card(
        llm.get("hitter_props", []),
        "HITTER PROPS",
        "🏏",
        TOKENS["amber"],
    )

    # 6. Moneylines
    _prop_section_card(
        llm.get("moneylines", []),
        "MONEYLINES",
        "💰",
        TOKENS["green"],
    )

    # 7. Skips
    render_skips(llm)

    st.markdown("---")

    # 8. Full slate breakdown
    render_slate_breakdown(llm)

    # 9. Full markdown write-up (collapsed)
    with st.expander("📄 Full Write-Up (Cart Style)", expanded=False):
        render_full_writeup(llm)


# ─────────────────────────────────────────────────────────────
# MATH ENGINE RENDERERS (unchanged)
# ─────────────────────────────────────────────────────────────

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
    ev_color = TOKENS["green"] if ev50 > 0 else "#EF4444"

    legs_html = ""
    for li, leg in enumerate(legs):
        lconf    = leg.get("confidence", "MED")
        lfire    = leg.get("fire", "🔥")
        lcat     = leg.get("category", "")
        lodds    = leg.get("odds", 0)
        lline    = leg.get("line")
        lplayer  = leg.get("player", "")
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
        odds_clr     = TOKENS["green"] if lodds > 0 else TOKENS["text_primary"]
        line_display = f"O{lline}" if lline else lplayer.split()[-1]
        sport_icon   = {"MLB": "⚾", "NBA": "🏀", "NHL": "🏒", "NFL": "🏈"}.get(lsport, "🏆")
        edge_clr     = TOKENS["green"] if ledge >= 5 else TOKENS["amber"]
        legs_html += f"""
<div style="background:{TOKENS['bg_panel_2']};border-radius:8px;padding:12px;
            margin-bottom:8px;border:1px solid {TOKENS['border']}">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">
    <div style="flex:1">
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px">
        <span style="font-size:10px;font-weight:800;color:{TOKENS['text_muted']};text-transform:uppercase">{sport_icon} LEG {li+1}</span>
        <span style="font-size:11px;font-weight:700;color:{status_clr};background:{status_clr}22;padding:1px 6px;border-radius:3px">{status_txt}</span>
        <span style="font-size:11px;color:{TOKENS['text_muted']}">{lfire}</span>
      </div>
      <div style="font-size:15px;font-weight:800;color:{TOKENS['text_primary']}">{lplayer} {line_display}</div>
      <div style="font-size:11px;color:{TOKENS['text_muted']};margin-top:2px">{lcat} · {lgame} · {ltime}</div>
    </div>
    <div style="text-align:right">
      <div style="font-family:'JetBrains Mono',monospace;font-size:20px;font-weight:800;color:{odds_clr}">{fmt_odds(lodds)}</div>
      <div style="font-size:10px;color:{edge_clr};font-weight:700">Edge +{ledge:.1f}%</div>
    </div>
  </div>
  <div style="background:{TOKENS['bg_main']};border-radius:6px;padding:8px 10px;margin-top:8px;font-size:11px;color:{TOKENS['text_secondary']}">
    {lreason[:160]}{'...' if len(lreason) > 160 else ''}
  </div>
  <div style="display:flex;gap:16px;margin-top:8px;font-size:10px;color:{TOKENS['text_muted']}">
    <span>Model: <b style="color:{TOKENS['text_primary']}">{lmodel:.0f}%</b></span>
    <span>Mkt: <b>{lmarket:.0f}%</b></span>
    <span>Kelly: <b style="color:{TOKENS['amber']}">{lkelly:.1f}%</b></span>
  </div>
</div>"""

    tags_html = "".join(
        f'<div style="background:{color}22;color:{color};padding:2px 8px;border-radius:4px;'
        f'font-size:10px;font-weight:700;align-self:center">{t}</div>'
        for t in tags[:3]
    )
    st.markdown(f"""
<div style="background:{TOKENS['bg_panel']};border:1px solid {color}44;
            border-left:4px solid {color};border-radius:10px;
            padding:0;margin-bottom:18px;overflow:hidden">
  <div style="background:{color}18;padding:14px 18px;
              display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
    <div>
      <span style="font-size:13px;font-weight:800;color:{color}">{icon} SLIP {idx+1} — {stype}</span>
      <div style="font-size:12px;color:{TOKENS['text_muted']};margin-top:2px">{name}</div>
    </div>
    <div style="text-align:right">
      <div style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:800;
                  color:{'#10B981' if odds > 0 else TOKENS['text_primary']}">{fmt_odds(odds)}</div>
      <div style="font-size:11px;color:{TOKENS['text_muted']}">Win prob: {wp:.0f}%</div>
    </div>
  </div>
  <div style="padding:10px 18px;background:{TOKENS['bg_panel_2']};
              border-bottom:1px solid {TOKENS['border']};
              font-size:12px;color:{TOKENS['text_secondary']};font-style:italic">{reason}</div>
  <div style="padding:12px 18px;display:flex;gap:24px;flex-wrap:wrap;
              border-bottom:1px solid {TOKENS['border']}">
    <div>
      <div style="font-size:9px;color:{TOKENS['text_muted']};text-transform:uppercase">Stake</div>
      <div style="font-weight:700;color:{TOKENS['text_primary']}">{stake}</div>
    </div>
    <div>
      <div style="font-size:9px;color:{TOKENS['text_muted']};text-transform:uppercase">EV on $50</div>
      <div style="font-family:'JetBrains Mono',monospace;font-weight:700;color:{ev_color}">${ev50:+.2f}</div>
    </div>
    <div>
      <div style="font-size:9px;color:{TOKENS['text_muted']};text-transform:uppercase">Confidence</div>
      <div style="color:{CONF_COLORS.get(conf, TOKENS['text_muted'])};font-weight:700">{conf}</div>
    </div>
    {tags_html}
  </div>
  <div style="padding:12px 18px">{legs_html}</div>
</div>
""", unsafe_allow_html=True)


def prop_table(props: list[dict]):
    rows = []
    for i, p in enumerate(props, 1):
        conf = p.get("confidence", "MED")
        plus = p.get("is_plus_money", False)
        status, _ = STATUS_MAP.get((conf, plus), ("⚡ PLAY", TOKENS["amber"]))
        rows.append({
            "#":             i,
            "Fire":          p.get("fire", "🔥"),
            "Status":        status,
            "Player / Team": p.get("player", "?"),
            "Prop":          f"{p.get('side','')} {p.get('line','')} {p.get('category','')}".strip(),
            "Odds":          fmt_odds(p.get("odds", 0)),
            "Model %":       f"{p.get('model_prob',0):.0f}%",
            "Mkt %":         f"{p.get('market_prob',0):.0f}%",
            "Edge":          f"+{p.get('edge_pct',0):.1f}%",
            "Kelly":         f"{p.get('kelly_pct',0):.1f}%",
            "Game":          (p.get("game","?").replace(" @ ","@").split("@")[0].strip().split()[-1]
                              + "@" + p.get("game","?").split("@")[-1].strip().split()[-1]
                              if "@" in p.get("game","") else p.get("game","?")),
            "Time":          p.get("game_time", "?"),
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
st.caption("Claude-powered daily analysis · Full write-up · Priority rankings · Slips · Refreshed 7 AM & 11:30 AM ET")

recs = load_latest_recs()

if recs is None:
    st.info("**No AI recommendations generated yet.** The first batch is generated automatically at 7 AM ET daily.")
    if st.button("⚡ Generate Recommendations Now", type="primary"):
        with st.spinner("Running Claude analysis on today's slate — 30-60 seconds..."):
            try:
                import subprocess
                r = subprocess.run(
                    [sys.executable, "workers/build_ai_recommendations.py"],
                    capture_output=True, text=True, cwd=str(project_root), timeout=180
                )
                st.cache_data.clear()
                if r.returncode == 0:
                    st.success("Done! Refreshing...")
                    st.rerun()
                else:
                    st.error(r.stderr[-800:] or r.stdout[-800:])
            except Exception as e:
                st.error(str(e))
    st.stop()

recs = recs or {"slips": [], "top_props": [], "n_plays": 0,
                "generated_at": "", "n_games": 0, "llm_analysis": {}}

# ── Header metrics ────────────────────────────────────────────
try:
    gen_ts  = datetime.fromisoformat(recs["generated_at"].replace("Z", "+00:00"))
    age_min = (datetime.now(timezone.utc) - gen_ts).total_seconds() / 60
    gen_str = gen_ts.strftime("%b %d %I:%M %p ET")
    freshness = (f"✅ Fresh ({age_min:.0f} min ago)"
                 if age_min < 120 else f"⚠️ {age_min/60:.1f}h old — rebuild or wait for next auto-run")
    fresh_color = TOKENS["green"] if age_min < 120 else TOKENS["amber"]
except Exception:
    gen_str, freshness, fresh_color = "Unknown", "—", TOKENS["text_muted"]

llm = recs.get("llm_analysis") or {}
llm_ok = llm and "error" not in llm

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Generated",      gen_str[:13])
c2.metric("AI Plays",       llm.get("n_props", "—"))
c3.metric("AI Slips",       len(llm.get("slips", [])))
c4.metric("Math Slips",     len(recs["slips"]))
c5.metric("Model",          "Claude ✓" if llm_ok else "Math only")

st.markdown(f"""
<div style="background:{fresh_color}18;border:1px solid {fresh_color}44;
            border-radius:6px;padding:8px 14px;margin:10px 0;
            font-size:12px;font-weight:700;color:{fresh_color}">{freshness}</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ── Tabs ──────────────────────────────────────────────────────
tab_llm, tab_math, tab_rebuild = st.tabs([
    "🧠 AI Analysis",
    f"📐 Math Slips ({len(recs['slips'])})",
    "⚙️ Rebuild",
])

with tab_llm:
    render_llm_analysis_tab(llm)

with tab_math:
    if not recs["slips"]:
        st.info("No math slips generated — odds data may be empty. Fetch odds first.")
    else:
        by_type = {"CORRELATED": [], "ANCHOR": [], "VALUE_MIX": [], "SWING": []}
        for s in recs["slips"]:
            by_type.setdefault(s.get("slip_type", "ANCHOR"), []).append(s)

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

    if recs["top_props"]:
        st.markdown("---")
        st.subheader("📋 Top Props (Math Engine)")
        prop_table(recs["top_props"])

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
            border-left:4px solid {sclr};border-radius:8px;padding:16px;margin-bottom:12px">
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
      <div style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:800;
                  color:{'#10B981' if p.get('odds',0)>0 else TOKENS['text_primary']};margin-top:6px">
        {fmt_odds(p.get('odds',0))}
      </div>
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

with tab_rebuild:
    st.subheader("⚙️ Rebuild Recommendations")
    st.caption("Manually trigger a new analysis run. Normally auto-runs after the scheduled odds pulls.")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
**Auto-Schedule (GitHub Actions):**
- 🌅 **7:00 AM ET** — Morning scan
- ☀️ **11:35 AM ET** — Pre-game midday pull

**Pipeline:**
1. Fetch odds → Supabase `odds_snapshots`
2. Fetch pitcher stats → MLB StatsAPI
3. **Claude ({llm.get('model_used','claude-sonnet-4-5')}) analyzes full slate**
4. Math engine (Poisson/Elo) builds slips
5. Results saved to `ai_recommendations` table

**Data sources:**
- Odds: The Odds API
- Pitchers: MLB StatsAPI (live FIP/K9)
- Players: NBA Stats API (game logs)
""")
    with col2:
        if st.button("🤖 Rebuild Now (Math + Claude)", type="primary", use_container_width=True):
            with st.spinner("Running Claude analysis — 30-60 seconds..."):
                try:
                    import subprocess
                    r = subprocess.run(
                        [sys.executable, "workers/build_ai_recommendations.py"],
                        capture_output=True, text=True, cwd=str(project_root), timeout=180
                    )
                    st.cache_data.clear()
                    if r.returncode == 0:
                        st.success("Done! Switch to AI Analysis tab.")
                        st.code(r.stdout[-800:] if r.stdout else "(no output)")
                    else:
                        st.error("Build failed:")
                        st.code((r.stderr or r.stdout)[-1000:])
                except Exception as e:
                    st.error(str(e))
