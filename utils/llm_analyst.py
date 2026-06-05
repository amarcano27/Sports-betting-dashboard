"""
APEX Analytics — LLM Analyst
==============================
Uses Claude API to generate a full expert-level betting analysis write-up
in the style of the May31_FullCart.xlsx betting cart.

Input:  raw games, odds, pitcher stats, player logs (from Supabase)
Output: structured JSON with slips, top props, priority rankings,
        full markdown write-up, and slate breakdown
"""
from __future__ import annotations
import os
import json
import math
from datetime import datetime, timezone
from typing import Optional


# ─────────────────────────────────────────────────────────────
# HELPERS — odds math (duplicated here so this module is standalone)
# ─────────────────────────────────────────────────────────────

def _american_to_implied(odds: int) -> float:
    """Convert American odds to implied probability (0–1)."""
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    return 100 / (odds + 100)

def _devig_pair(a: int, b: int) -> tuple[float, float]:
    pa = _american_to_implied(a)
    pb = _american_to_implied(b)
    t  = pa + pb
    return pa / t, pb / t

def _fmt_odds(o: int) -> str:
    return f"+{o}" if o > 0 else str(o)


# ─────────────────────────────────────────────────────────────
# DATA PREP — summarize raw Supabase data for the prompt
# ─────────────────────────────────────────────────────────────

def _build_slate_summary(games: list[dict], odds_map: dict[str, list]) -> list[dict]:
    """Condense each game into a dict Claude can reason about."""
    rows = []
    for g in games:
        sport = g.get("sport", "")
        away  = g.get("away_team", "")
        home  = g.get("home_team", "")
        gid   = g.get("id", "")

        try:
            t = datetime.fromisoformat(g["start_time"].replace("Z", "+00:00"))
            time_str = t.strftime("%-I:%M %p ET")
        except Exception:
            time_str = "TBD"

        game_odds = odds_map.get(gid, [])

        # Pull ML odds
        away_ml = next((int(r["price"]) for r in game_odds
                        if r.get("market_type") == "h2h"
                        and r.get("market_label") == away), None)
        home_ml = next((int(r["price"]) for r in game_odds
                        if r.get("market_type") == "h2h"
                        and r.get("market_label") == home), None)

        # Pull total (over/under)
        total_line = next((r.get("line") for r in game_odds
                           if r.get("market_type") == "totals"), None)

        # Devig probabilities
        away_prob = home_prob = None
        if away_ml and home_ml:
            away_prob, home_prob = _devig_pair(away_ml, home_ml)

        row = {
            "sport":       sport,
            "game":        f"{away} @ {home}",
            "game_id":     gid,
            "time":        time_str,
            "away_team":   away,
            "home_team":   home,
            "away_ml":     _fmt_odds(away_ml) if away_ml else "N/A",
            "home_ml":     _fmt_odds(home_ml) if home_ml else "N/A",
            "away_win_pct": f"{away_prob*100:.1f}%" if away_prob else "N/A",
            "home_win_pct": f"{home_prob*100:.1f}%" if home_prob else "N/A",
            "total":       total_line,
        }

        # Player prop lines (strikeouts, points, etc.)
        prop_lines = []
        for r in game_odds:
            if r.get("market_type") in ("player_strikeouts", "player_points",
                                        "player_rebounds", "player_assists",
                                        "player_total_bases", "batter_hits"):
                prop_lines.append({
                    "market": r.get("market_type"),
                    "player": r.get("market_label", ""),
                    "line":   r.get("line"),
                    "odds":   r.get("price"),
                    "side":   r.get("outcome_name", "Over"),
                })
        if prop_lines:
            row["prop_lines"] = prop_lines

        rows.append(row)
    return rows


def _build_pitcher_context(games: list[dict], pitcher_db: dict) -> list[dict]:
    """Build pitcher matchup context for the prompt."""
    TEAM_ABBR = {
        "Detroit Tigers": "DET", "Tampa Bay Rays": "TB",
        "San Diego Padres": "SD", "Philadelphia Phillies": "PHI",
        "Miami Marlins": "MIA", "Washington Nationals": "WSH",
        "Baltimore Orioles": "BAL", "Boston Red Sox": "BOS",
        "Cleveland Guardians": "CLE", "New York Yankees": "NYY",
        "Kansas City Royals": "KC", "Cincinnati Reds": "CIN",
        "Toronto Blue Jays": "TOR", "Atlanta Braves": "ATL",
        "Chicago White Sox": "CHW", "Minnesota Twins": "MIN",
        "San Francisco Giants": "SF", "Milwaukee Brewers": "MIL",
        "Texas Rangers": "TEX", "St. Louis Cardinals": "STL",
        "Athletics": "OAK", "Chicago Cubs": "CHC",
        "Pittsburgh Pirates": "PIT", "Houston Astros": "HOU",
        "Colorado Rockies": "COL", "Los Angeles Angels": "LAA",
        "Los Angeles Dodgers": "LAD", "Arizona Diamondbacks": "ARI",
        "New York Mets": "NYM", "Seattle Mariners": "SEA",
    }

    rows = []
    for g in games:
        if g.get("sport") != "MLB":
            continue
        away, home = g.get("away_team", ""), g.get("home_team", "")
        pair = {}
        for team, side in [(away, "away"), (home, "home")]:
            abbr = TEAM_ABBR.get(team, "")
            p = next((v for v in pitcher_db.values() if v.get("team") == abbr), None)
            name = next((k.title() for k, v in pitcher_db.items()
                         if v.get("team") == abbr), team)
            if p:
                pair[side] = {
                    "name": name,
                    "team": abbr,
                    "era":  p.get("era", "?"),
                    "fip":  p.get("fip", "?"),
                    "k9":   p.get("k9", "?"),
                    "whip": p.get("whip", "?"),
                }
            else:
                pair[side] = {"name": "TBD", "team": abbr}
        rows.append({
            "game": f"{away} @ {home}",
            "away_pitcher": pair.get("away", {}),
            "home_pitcher": pair.get("home", {}),
        })
    return rows


def _build_player_context(players: list[dict], logs_map: dict) -> list[dict]:
    """Summarize recent player performance for the prompt."""
    context = []
    for p in players[:60]:  # cap to avoid token overflow
        pid = p.get("id", "")
        logs = logs_map.get(pid, [])[:10]
        if not logs:
            continue
        sport = p.get("sport", "")
        name  = p.get("name", "")

        if sport == "NBA":
            pts  = [l.get("points", 0) or 0 for l in logs]
            reb  = [l.get("rebounds", 0) or 0 for l in logs]
            ast  = [l.get("assists", 0) or 0 for l in logs]
            context.append({
                "player": name, "sport": sport, "team": p.get("team", ""),
                "last10_pts_avg":  round(sum(pts) / len(pts), 1) if pts else 0,
                "last10_reb_avg":  round(sum(reb) / len(reb), 1) if reb else 0,
                "last10_ast_avg":  round(sum(ast) / len(ast), 1) if ast else 0,
                "games": len(logs),
            })

    return context


# ─────────────────────────────────────────────────────────────
# PROMPT BUILDER
# ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are APEX, an elite sports betting analyst. You specialize in:
- MLB pitcher strikeout props (Poisson K model, ERA/FIP/K9 matchup analysis)
- Moneyline edges (pitching mismatch, home/away splits, recent form)
- NBA player props (recent 10-game averages vs book lines)
- Correlated parlays (pitcher K prop + same-game team ML)
- Kelly criterion stake sizing
- Identifying -EV traps and skips

Your analysis style matches professional sharp bettors:
- Lead with the edge percentage and the math behind it
- Reference specific stats (ERA, FIP, K/9, wRC+, recent streaks)
- Identify correlations between same-game props
- Flag risky legs clearly with ⚠️
- Use fire ratings: 🔥🔥🔥 HIGH / 🔥🔥 MED-HIGH / 🔥 MED
- Use status badges: ✅ BEST VALUE / ✅ STRONG / ⚡ PLAY / ⚠️ RISKY / 🚫 SKIP

You MUST return valid JSON matching the exact schema provided. No extra text outside the JSON."""


def _build_user_prompt(
    slate: list[dict],
    pitchers: list[dict],
    players: list[dict],
    date_str: str,
) -> str:
    data_block = json.dumps({
        "date": date_str,
        "slate": slate,
        "pitcher_matchups": pitchers,
        "nba_player_averages": players,
    }, indent=2)

    schema = json.dumps({
        "executive_summary": "2-3 sentence overview of the day's best bets and key narratives",
        "slate_breakdown": [
            {
                "number": 1,
                "game": "Away @ Home",
                "time": "1:35 PM ET",
                "sport": "MLB",
                "away_ml": "+118",
                "home_ml": "-138",
                "away_pitcher": "Name (ERA, K/9)",
                "home_pitcher": "Name (ERA, K/9)",
                "pick": "HOME -138",
                "rating": "✅ STRONG",
                "dimers_win_pct": "58%",
                "reasoning": "Full expert reasoning paragraph referencing stats"
            }
        ],
        "pitcher_k_props": [
            {
                "ref": "P1",
                "pitcher": "Full Name",
                "team": "MIL",
                "game": "MIL @ HOU",
                "time": "2:10 PM ET",
                "line": 7.5,
                "odds": "-132",
                "implied_pct": "56.9%",
                "model_est_pct": "72-76%",
                "edge": "+15-19%",
                "confidence": "HIGH",
                "fire": "🔥🔥🔥",
                "status": "✅ BEST ANCHOR",
                "stake_rec": "$20-$30",
                "reasoning": "Full reasoning with K/9, ERA of opponent, recent K streak, correlation note if applicable"
            }
        ],
        "hitter_props": [
            {
                "ref": "H1",
                "player": "Full Name",
                "team": "BOS",
                "game": "BOS @ CLE",
                "time": "1:40 PM ET",
                "prop": "OVER 1.5 Total Bases",
                "line": 1.5,
                "odds": "-130",
                "implied_pct": "56.5%",
                "model_est_pct": "58-62%",
                "edge": "+2-6%",
                "confidence": "MED-HIGH",
                "fire": "🔥🔥",
                "status": "⚡ PLAY",
                "stake_rec": "$15-$25",
                "reasoning": "Full reasoning with recent stats, hit rate, matchup context"
            }
        ],
        "moneylines": [
            {
                "ref": "M1",
                "team": "Pittsburgh Pirates",
                "game": "MIN @ PIT",
                "time": "1:35 PM ET",
                "odds": "-142",
                "implied_pct": "58.7%",
                "model_est_pct": "63-66%",
                "edge": "+4-7%",
                "confidence": "HIGH",
                "fire": "🔥🔥🔥",
                "status": "✅ STRONG",
                "use": "Slip 3",
                "reasoning": "Full reasoning referencing pitcher ERA, home/away advantage, recent form"
            }
        ],
        "priority_rankings": [
            {
                "rank": 1,
                "medal": "🥇",
                "ref": "P1",
                "play": "Full description",
                "game": "Game string",
                "time": "2:10 PM ET",
                "odds": "-132",
                "implied_pct": "56.9%",
                "real_est_pct": "72-76%",
                "edge": "+15-19%",
                "stake_rec": "$20-$30",
                "best_use": "Primary anchor — use in Slips 2+4",
                "one_liner": "Concise reason why this is ranked here"
            }
        ],
        "slips": [
            {
                "number": 1,
                "emoji": "🔵",
                "name": "MLB ANCHOR — Miz + Yamamoto Correlated K+ML",
                "type": "ANCHOR",
                "stake_rec": "$50-$75",
                "target": "+350 to +500",
                "confidence": "HIGH",
                "legs": [
                    {
                        "ref": "P1",
                        "leg_number": 1,
                        "play": "Misiorowski OVER 7.5 Ks — MIL @ HOU",
                        "odds": "-132",
                        "confidence": "HIGH",
                        "fire": "🔥🔥🔥",
                        "key_reason": "One sentence reason"
                    }
                ],
                "slip_note": "📌 Full paragraph explaining the slip structure, correlations, and why it works",
                "combined_odds_approx": "+350",
                "win_prob_approx": "35-40%"
            }
        ],
        "skips": [
            {
                "ref": "MX1",
                "play": "PHI ML @ LAD",
                "odds": "+175",
                "reason": "Why to skip — brief"
            }
        ],
        "full_markdown_writeup": "Complete markdown-formatted write-up mimicking the Excel sheet style. Include all sections: date header, verified sources note, key information rows, pitcher K section, hitter props section, ML section, your existing parlay review (if any), and footer. Use markdown tables, bold for key plays, and emoji ratings."
    }, indent=2)

    return f"""Today is {date_str}. Analyze the following betting data and return a comprehensive expert analysis.

## DATA
{data_block}

## REQUIRED OUTPUT SCHEMA
Return ONLY valid JSON matching this schema exactly:
{schema}

## ANALYSIS INSTRUCTIONS

### Pitcher K Props
- For each MLB starting pitcher, estimate expected Ks in ~6 IP using K/9 rate
- Compare to available prop lines; calculate edge = model prob - implied prob
- Only include plays with edge >= +3%
- Lead plays should reference: K streak, ERA of opponent starter, K/9 vs opp lineup, correlation with team ML
- Flag plus-money K props as BEST VALUE

### Moneylines
- Use pitching ERA differential as primary signal
- Use devigged win probability from odds to find market prob
- Skip games where both starters are bad (coin flip) or juice is -200+
- Flag correlated plays (K prop + same-game ML) in both sections
- Mark -200+ juice as PARLAY ONLY

### Priority Rankings
- Rank ALL plays by edge percentage descending
- Top 3 get medal emojis 🥇🥈🥉
- Include a ⚠️ row for risky legs
- Include a ❌ row for must-skip games

### Slips
Build 4 slips total:
1. ANCHOR (2-3 legs, safest plays, ~$50-75 stake, correlated if possible)
2. VALUE (3-4 legs, mix of sports, $30-50 stake, diversified)
3. MLB CORRELATED (2-4 legs, K props + same-game MLs, $25-50 stake)
4. SWING (4-5 legs, higher payout target, $15-25 stake, include plus-money)

Each slip must have a 📌 note explaining the correlation structure and why it works.

### Markdown Writeup
Write in the exact style of a professional betting cart:
- Header: "📅 [DATE] — FULL BETTING CART | [SPORT] [N] Games | Sources: ..."
- Source verification line
- Key info rows (situation notes, parlay reviews)
- Pitcher K section with table
- Hitter Props section
- Moneyline section
- Your parlay review section (if relevant plays exist)
- Priority Rankings table

Be specific, reference actual stat numbers, explain correlations clearly."""


# ─────────────────────────────────────────────────────────────
# MAIN FUNCTION
# ─────────────────────────────────────────────────────────────

def generate_llm_analysis(
    games: list[dict],
    odds_map: dict[str, list],
    pitcher_db: dict,
    players: list[dict],
    logs_map: dict[str, list],
    model: str = "claude-sonnet-4-5",
    max_tokens: int = 8000,
) -> dict:
    """
    Call Claude API with today's odds data and return structured analysis.

    Returns a dict with keys:
      - executive_summary
      - slate_breakdown
      - pitcher_k_props
      - hitter_props
      - moneylines
      - priority_rankings
      - slips
      - skips
      - full_markdown_writeup
      - generated_at
      - model_used
      - error (only if something failed)
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        # Try Streamlit secrets
        try:
            import streamlit as st
            api_key = st.secrets.get("ANTHROPIC_API_KEY") or st.secrets.get("anthropic_api_key")
        except Exception:
            pass

    if not api_key:
        return {
            "error": "ANTHROPIC_API_KEY not set",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    try:
        import anthropic
    except ImportError:
        return {
            "error": "anthropic package not installed — run: pip install anthropic",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    date_str = datetime.now().strftime("%B %-d, %Y")

    # Build context
    slate    = _build_slate_summary(games, odds_map)
    pitchers = _build_pitcher_context(games, pitcher_db)
    player_ctx = _build_player_context(players, logs_map)

    if not slate:
        return {
            "error": "No games found — odds may not have been fetched yet",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    user_prompt = _build_user_prompt(slate, pitchers, player_ctx, date_str)

    client = anthropic.Anthropic(api_key=api_key)

    print(f"[llm_analyst] Calling Claude ({model}) with {len(slate)} games...")

    try:
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = message.content[0].text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rsplit("```", 1)[0].strip()

        result = json.loads(raw)
        result["generated_at"] = datetime.now(timezone.utc).isoformat()
        result["model_used"]   = model
        result["n_games"]      = len(slate)
        result["n_props"]      = (
            len(result.get("pitcher_k_props", [])) +
            len(result.get("hitter_props", [])) +
            len(result.get("moneylines", []))
        )

        print(f"[llm_analyst] Done — {result['n_props']} plays, "
              f"{len(result.get('slips', []))} slips, "
              f"{len(result.get('priority_rankings', []))} ranked plays")

        return result

    except json.JSONDecodeError as e:
        print(f"[llm_analyst] JSON parse error: {e}")
        # Return raw text as fallback so we don't lose the analysis
        return {
            "error": f"JSON parse failed: {e}",
            "raw_response": raw if "raw" in dir() else "",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model_used": model,
        }
    except Exception as e:
        print(f"[llm_analyst] API error: {e}")
        return {
            "error": str(e),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model_used": model,
        }
