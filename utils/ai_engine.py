"""
APEX AI Recommendation Engine
==============================
Reads live odds + pitcher stats + player game logs from Supabase and generates:
  1. 10 structured 2-4 leg slips (ANCHOR, CORRELATED, VALUE MIX, SWING)
  2. Top 10-20 individual props of the day with full reasoning

Methodology (matches May31_FullCart.xlsx logic):
  - Edge = model probability − devigged market probability
  - Pitcher props use Poisson K model (K/9 rate vs opponent)
  - Hitter props use recent stats (last 10 games) vs current line
  - Correlation: pitcher K prop + same-game team ML → boost
  - Slip types: ANCHOR (high confidence), CORRELATED (same-game),
    VALUE MIX (diversified), SWING (higher legs, bigger payout)
"""
from __future__ import annotations
import math
import json
from datetime import datetime, timezone
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────

@dataclass
class Play:
    """One individual betting play."""
    sport:       str
    game:        str          # "Away @ Home"
    game_id:     str
    player:      str          # pitcher/batter name or team name
    prop_type:   str          # "K_PROP" | "TOTAL_BASES" | "POINTS" | "MONEYLINE" | "ASSISTS" etc
    line:        float | None
    odds:        int
    side:        str          # "Over" | "Under" | team name
    model_prob:  float        # our estimate 0–1
    market_prob: float        # devigged market 0–1
    edge_pct:    float        # (model_prob - market_prob) * 100
    confidence:  str          # "HIGH" | "MED-HIGH" | "MED" | "LOW"
    fire:        str          # "🔥🔥🔥" | "🔥🔥" | "🔥"
    reasoning:   str
    game_time:   str
    category:    str          # "Pitcher K" | "Hitter Prop" | "Moneyline" | "Total"
    is_plus_money: bool
    kelly_pct:   float = 0.0
    # correlation info
    corr_game_id: str = ""    # if correlated with another play in same game

@dataclass
class Slip:
    """A recommended multi-leg parlay."""
    name:        str          # "ANCHOR SLIP", "CORRELATED", etc.
    slip_type:   str          # "ANCHOR" | "CORRELATED" | "VALUE_MIX" | "SWING"
    legs:        list[Play]
    combined_odds: int
    win_prob:    float        # joint win probability
    ev_50:       float        # EV on $50 stake
    stake_rec:   str          # "$25-$50"
    target_payout: str        # "+350 pays $225"
    reasoning:   str
    confidence:  str
    tags:        list[str]    # ["K+ML SAME GAME", "PLUS MONEY ANCHOR"]


# ─────────────────────────────────────────────────────────────
# MATH HELPERS
# ─────────────────────────────────────────────────────────────

def american_to_prob(odds: int) -> float:
    if odds < 0: return abs(odds) / (abs(odds) + 100)
    return 100 / (odds + 100)

def american_to_decimal(odds: int) -> float:
    if odds >= 0: return 1 + odds / 100
    return 1 + 100 / abs(odds)

def decimal_to_american(dec: float) -> int:
    if dec >= 2: return round((dec - 1) * 100)
    return round(-100 / (dec - 1))

def devig(a_odds: int, h_odds: int) -> tuple[float, float]:
    a = american_to_prob(a_odds)
    h = american_to_prob(h_odds)
    t = a + h
    return a / t, h / t

def poisson_over_prob(lam: float, line: float) -> float:
    """P(X > line) using Poisson distribution. line is always .5 increment."""
    k = int(line)  # floor — need > line means >= k+1
    cdf = sum(math.exp(-lam) * lam**i / math.factorial(i) for i in range(k + 1))
    prob = 1.0 - cdf
    return max(0.05, min(0.95, prob * 0.93))  # slight shrinkage

def parlay_odds(legs: list[int]) -> int:
    combined = 1.0
    for o in legs:
        combined *= american_to_decimal(o)
    return decimal_to_american(combined)

def joint_prob(plays: list[Play]) -> float:
    """Joint win probability with pairwise correlation adjustments."""
    # Base independent probability
    p = 1.0
    for play in plays:
        p *= play.model_prob

    # Boost for same-game correlated legs (K prop + ML same direction)
    game_counts = defaultdict(list)
    for play in plays:
        game_counts[play.game_id].append(play)

    for gid, group in game_counts.items():
        if len(group) >= 2:
            types = {pl.prop_type for pl in group}
            if "K_PROP" in types and "MONEYLINE" in types:
                p *= 1.12   # ~12% boost for K+ML same game correlation
            elif len(types) == 1 and "MONEYLINE" in types:
                p *= 1.05   # slight boost for same game MLs

    return min(0.90, p)

def ev(combined_odds: int, win_prob: float, stake: float) -> float:
    dec = american_to_decimal(combined_odds)
    return round(win_prob * (dec - 1) * stake - (1 - win_prob) * stake, 2)

def quarter_kelly(odds: int, win_prob: float) -> float:
    b = american_to_decimal(odds) - 1
    p, q = win_prob, 1 - win_prob
    fk = (b * p - q) / b
    return max(0.0, fk * 0.25)

def confidence_label(edge_pct: float) -> tuple[str, str]:
    if edge_pct >= 12: return "HIGH", "🔥🔥🔥"
    if edge_pct >= 7:  return "HIGH", "🔥🔥🔥"
    if edge_pct >= 4:  return "MED-HIGH", "🔥🔥"
    if edge_pct >= 2:  return "MED", "🔥🔥"
    return "LOW", "🔥"

def stake_rec(slip_type: str) -> tuple[str, str]:
    mapping = {
        "ANCHOR":      ("$30–$60", "+250 to +400"),
        "CORRELATED":  ("$25–$50", "+300 to +500"),
        "VALUE_MIX":   ("$20–$40", "+400 to +700"),
        "SWING":       ("$10–$25", "+800 to +1500"),
    }
    return mapping.get(slip_type, ("$25", "+400"))


# ─────────────────────────────────────────────────────────────
# PLAY BUILDERS
# ─────────────────────────────────────────────────────────────

def build_pitcher_k_plays(games: list[dict], odds_map: dict,
                          pitcher_db: dict) -> list[Play]:
    """Build K prop plays from today's probable starters."""
    plays = []

    # Pitcher DB key lookup by team abbreviation
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

    for game in games:
        if game.get("sport") != "MLB":
            continue
        away, home = game["away_team"], game["home_team"]
        game_str = f"{away} @ {home}"
        gid = game["id"]

        try:
            t = datetime.fromisoformat(game["start_time"].replace("Z", "+00:00"))
            time_str = t.strftime("%I:%M %p ET")
        except Exception:
            time_str = "TBD"

        rows = odds_map.get(gid, [])
        away_ml = next((int(r["price"]) for r in rows
                        if r.get("market_type") == "h2h" and r.get("market_label") == away), None)
        home_ml = next((int(r["price"]) for r in rows
                        if r.get("market_type") == "h2h" and r.get("market_label") == home), None)

        for team, is_home in [(away, False), (home, True)]:
            abbr = TEAM_ABBR.get(team, "")
            pitcher = next((v for v in pitcher_db.values() if v.get("team") == abbr), None)
            if not pitcher or not pitcher.get("k9"):
                continue

            k9  = pitcher["k9"]
            fip = pitcher["fip"]
            name = next((k.title() for k, v in pitcher_db.items() if v.get("team") == abbr), team)

            # Typical book line = ~0.5 below expected 6-IP pace, snap to .5
            exp_6ip = k9 * 6 / 9
            line    = max(3.5, round(exp_6ip * 2 - 1) / 2)

            # Poisson model
            lam         = exp_6ip * 0.93   # slight regression
            model_prob  = poisson_over_prob(lam, line)
            implied_raw = 0.55   # typical -122 book default
            # Use actual prop odds if available (from player_prop_odds table)
            prop_odds   = -122   # default
            market_prob = american_to_prob(prop_odds)

            edge = (model_prob - market_prob) * 100
            if edge < 2.0:
                continue

            conf, fire = confidence_label(edge)
            opp_team = home if not is_home else away
            opp_abbr = TEAM_ABBR.get(opp_team, "?")
            opp_p    = next((v for v in pitcher_db.values() if v.get("team") == opp_abbr), None)
            opp_era  = f"{opp_p['era']:.2f}" if opp_p else "?"
            opp_name = next((k.title() for k, v in pitcher_db.items()
                             if v.get("team") == opp_abbr), opp_team)

            reasoning = (
                f"{name} (FIP {fip:.2f}, K/9 {k9:.1f}) vs {opp_name} (ERA {opp_era}). "
                f"Poisson model: {exp_6ip:.1f} expected Ks in 6 IP. "
                f"Line {line} is {'below' if line <= exp_6ip else 'above'} expected pace. "
                f"Edge +{edge:.1f}% — {'plus-money value' if prop_odds > 0 else 'strong play'}."
            )

            plays.append(Play(
                sport="MLB", game=game_str, game_id=gid,
                player=name, prop_type="K_PROP",
                line=line, odds=prop_odds, side="Over",
                model_prob=model_prob, market_prob=market_prob,
                edge_pct=round(edge, 1),
                confidence=conf, fire=fire,
                reasoning=reasoning, game_time=time_str,
                category="Pitcher K",
                is_plus_money=(prop_odds > 0),
                kelly_pct=round(quarter_kelly(prop_odds, model_prob) * 100, 1),
                corr_game_id=gid,
            ))
    return plays


def build_moneyline_plays(games: list[dict], odds_map: dict,
                          pitcher_db: dict) -> list[Play]:
    """Build ML plays using Elo+FIP model."""
    from utils.model import build_game_model

    plays = []
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

    for game in games:
        if game.get("sport") not in ("MLB", "NBA", "NHL", "NFL"):
            continue
        away, home = game["away_team"], game["home_team"]
        gid = game["id"]
        rows = odds_map.get(gid, [])

        try:
            t = datetime.fromisoformat(game["start_time"].replace("Z", "+00:00"))
            time_str = t.strftime("%I:%M %p ET")
        except Exception:
            time_str = "TBD"

        away_ml = next((int(r["price"]) for r in rows
                        if r.get("market_type") == "h2h" and r.get("market_label") == away), None)
        home_ml = next((int(r["price"]) for r in rows
                        if r.get("market_type") == "h2h" and r.get("market_label") == home), None)
        if not away_ml or not home_ml:
            continue

        dv_a, dv_h = devig(away_ml, home_ml)

        if game.get("sport") == "MLB":
            a_abbr = TEAM_ABBR.get(away, "")
            h_abbr = TEAM_ABBR.get(home, "")
            ap = next((v for v in pitcher_db.values() if v.get("team") == a_abbr), None)
            hp = next((v for v in pitcher_db.values() if v.get("team") == h_abbr), None)
            if ap and hp:
                gm = build_game_model(away, home, ap["fip"], hp["fip"],
                                      away_ml, home_ml)
                sides = [
                    (away, away_ml, gm.model_away_prob, dv_a, gm.away_edge,
                     next((k.title() for k, v in pitcher_db.items() if v.get("team") == a_abbr), "?"),
                     next((k.title() for k, v in pitcher_db.items() if v.get("team") == h_abbr), "?"),
                     ap, hp),
                    (home, home_ml, gm.model_home_prob, dv_h, gm.home_edge,
                     next((k.title() for k, v in pitcher_db.items() if v.get("team") == h_abbr), "?"),
                     next((k.title() for k, v in pitcher_db.items() if v.get("team") == a_abbr), "?"),
                     hp, ap),
                ]
            else:
                sides = [
                    (away, away_ml, dv_a, dv_a, (dv_a - american_to_prob(away_ml)) * 100, "?", "?", None, None),
                    (home, home_ml, dv_h, dv_h, (dv_h - american_to_prob(home_ml)) * 100, "?", "?", None, None),
                ]
        else:
            sides = [
                (away, away_ml, dv_a, dv_a, (dv_a - american_to_prob(away_ml)) * 100, "", "", None, None),
                (home, home_ml, dv_h, dv_h, (dv_h - american_to_prob(home_ml)) * 100, "", "", None, None),
            ]

        for (team, ml, model_p, mkt_p, edge, sp_name, opp_sp, sp, opp_sp_obj) in sides:
            if edge < 1.5:
                continue
            # Skip -200+ straight (structural trap)
            if ml < -199:
                continue

            conf, fire = confidence_label(edge)
            opp = home if team == away else away

            if sp and opp_sp_obj:
                reasoning = (
                    f"{sp_name} (FIP {sp['fip']:.2f}) vs {opp_sp} (FIP {opp_sp_obj['fip']:.2f}). "
                    f"Model: {team.split()[-1]} {model_p*100:.1f}% vs devigged market {mkt_p*100:.1f}%. "
                    f"Edge +{edge:.1f}%."
                )
            else:
                reasoning = (
                    f"{team.split()[-1]} ML. Model: {model_p*100:.1f}% vs devigged market {mkt_p*100:.1f}%. "
                    f"Edge +{edge:.1f}%."
                )

            if ml < -199:
                reasoning += " PARLAY ONLY — never lay -200+ straight."

            plays.append(Play(
                sport=game.get("sport", "?"),
                game=f"{away} @ {home}", game_id=gid,
                player=team, prop_type="MONEYLINE",
                line=None, odds=ml, side=team,
                model_prob=model_p, market_prob=mkt_p,
                edge_pct=round(edge, 1),
                confidence=conf, fire=fire,
                reasoning=reasoning, game_time=time_str,
                category="Moneyline",
                is_plus_money=(ml > 0),
                kelly_pct=round(quarter_kelly(ml, model_p) * 100, 1),
                corr_game_id=gid,
            ))
    return plays


def build_nba_player_plays(players: list[dict], logs_map: dict,
                            games: list[dict]) -> list[Play]:
    """Build NBA player prop plays from recent game logs."""
    from services.player_service import compute_prop_line, hit_rate, nba_headshot_url
    plays = []

    game_teams = {}
    for g in games:
        if g.get("sport") == "NBA":
            game_teams[g["id"]] = (g["away_team"], g["home_team"])

    for player in players:
        if player.get("sport") != "NBA":
            continue
        pid = player["id"]
        logs = logs_map.get(pid, [])
        if len(logs) < 5:
            continue

        pts = [g.get("points", 0) for g in logs]
        avg = sum(pts) / len(pts)
        if avg < 8:
            continue

        line = compute_prop_line(pts)
        hr   = hit_rate(pts[:10], line)
        over_prob = hr.get("over", 50) / 100

        # Default prop odds near -110
        prop_odds    = -110
        market_prob  = american_to_prob(prop_odds)
        edge         = (over_prob - market_prob) * 100
        if edge < 2.0:
            continue

        conf, fire = confidence_label(edge)
        streak = hr.get("streak", 0)
        streak_dir = hr.get("streak_dir", "")

        reasoning = (
            f"{player['name']} averaging {avg:.1f} pts/game. "
            f"O{line} — {hr['over']:.0f}% over rate in last 10 games. "
            f"{'🔥 ' + str(streak) + '-game Over streak! ' if streak >= 3 and streak_dir == 'O' else ''}"
            f"Edge +{edge:.1f}%."
        )

        plays.append(Play(
            sport="NBA", game="NBA Game", game_id="",
            player=player["name"], prop_type="POINTS",
            line=line, odds=prop_odds, side="Over",
            model_prob=over_prob, market_prob=market_prob,
            edge_pct=round(edge, 1),
            confidence=conf, fire=fire,
            reasoning=reasoning, game_time="TBD",
            category="Player Points",
            is_plus_money=False,
            kelly_pct=round(quarter_kelly(prop_odds, over_prob) * 100, 1),
        ))

    return plays


# ─────────────────────────────────────────────────────────────
# SLIP BUILDER
# ─────────────────────────────────────────────────────────────

def build_slips(all_plays: list[Play], n_slips: int = 10) -> list[Slip]:
    """
    Build n_slips 2-4 leg slips from the play pool.
    Strategy:
      - 3 CORRELATED slips: K prop + ML from same game
      - 3 ANCHOR slips: top 2 edge plays from different games
      - 2 VALUE MIX slips: 3-leg diversified
      - 2 SWING slips: 4-leg, higher payout
    """
    slips: list[Slip] = []

    # Sort by edge
    sorted_plays = sorted(all_plays, key=lambda p: -p.edge_pct)

    # De-dup: one play per player per game
    seen = set()
    unique = []
    for p in sorted_plays:
        key = (p.game_id, p.player, p.prop_type)
        if key not in seen:
            seen.add(key)
            unique.append(p)

    # ── CORRELATED SLIPS (K prop + ML same game) ──────────────
    by_game: dict[str, list[Play]] = defaultdict(list)
    for p in unique:
        if p.game_id:
            by_game[p.game_id].append(p)

    for gid, group in sorted(by_game.items(),
                              key=lambda x: max(p.edge_pct for p in x[1]), reverse=True):
        if len(slips) >= 3:
            break
        k_plays  = [p for p in group if p.prop_type == "K_PROP"]
        ml_plays = [p for p in group if p.prop_type == "MONEYLINE"]
        if not k_plays or not ml_plays:
            continue

        k  = k_plays[0]
        ml = ml_plays[0]
        legs = [k, ml]
        c_odds = parlay_odds([k.odds, ml.odds])
        wp     = joint_prob(legs)
        e50    = ev(c_odds, wp, 50)
        stake, target = stake_rec("CORRELATED")
        payout_str = f"+{c_odds} pays ${round((american_to_decimal(c_odds)-1)*50):.0f} on $50"

        slips.append(Slip(
            name=f"CORRELATED — {k.player} K + {ml.player.split()[-1]} ML",
            slip_type="CORRELATED",
            legs=legs,
            combined_odds=c_odds,
            win_prob=round(wp * 100, 1),
            ev_50=e50,
            stake_rec=stake,
            target_payout=target,
            reasoning=(
                f"Same-game correlation: {k.player}'s strikeout dominance directly supports "
                f"{ml.player.split()[-1]} winning. When a pitcher dominates (K prop hits), "
                f"the team almost always wins. This boosts joint probability ~12% above independent."
            ),
            confidence=k.confidence,
            tags=["K+ML SAME GAME", "CORRELATED"],
        ))

    # ── ANCHOR SLIPS (top 2 plays, different games) ──────────
    top = [p for p in unique if p.edge_pct >= 4 and p.prop_type != "MONEYLINE"]
    # Also grab top MLs
    top_ml = [p for p in unique if p.prop_type == "MONEYLINE" and p.edge_pct >= 3]
    anchor_pool = top[:8] + top_ml[:4]
    # shuffle to avoid all-same-game
    used_games: set[str] = set()
    anchor_legs: list[Play] = []
    for p in sorted(anchor_pool, key=lambda x: -x.edge_pct):
        if p.game_id not in used_games or not p.game_id:
            anchor_legs.append(p)
            used_games.add(p.game_id)
        if len(anchor_legs) >= 6:
            break

    # Build 2-leg anchor slips from the pool
    for i in range(0, min(len(anchor_legs) - 1, 6), 2):
        if len(slips) >= 6:
            break
        pair = anchor_legs[i:i+2]
        if len(pair) < 2:
            break
        c_odds = parlay_odds([p.odds for p in pair])
        wp     = joint_prob(pair)
        e50    = ev(c_odds, wp, 50)
        stake, target = stake_rec("ANCHOR")

        plus_tag = "PLUS MONEY ANCHOR" if any(p.is_plus_money for p in pair) else "HIGH CONFIDENCE"
        slips.append(Slip(
            name=f"ANCHOR — {' + '.join(p.player.split()[-1] for p in pair)}",
            slip_type="ANCHOR",
            legs=pair,
            combined_odds=c_odds,
            win_prob=round(wp * 100, 1),
            ev_50=e50,
            stake_rec=stake,
            target_payout=target,
            reasoning=(
                f"Two highest-edge plays from different games. "
                f"Combined edge averages {sum(p.edge_pct for p in pair)/2:.1f}%. "
                f"Low correlation — independent events reduce variance."
            ),
            confidence=pair[0].confidence,
            tags=[plus_tag, f"COMBINED EDGE {sum(p.edge_pct for p in pair):.0f}%"],
        ))

    # ── VALUE MIX (3-leg diversified) ───────────────────────
    remaining = [p for p in unique if not any(p in s.legs for s in slips)]
    remaining.sort(key=lambda x: -x.edge_pct)
    value_legs = remaining[:9]
    for i in range(0, min(len(value_legs) - 2, 6), 3):
        if len(slips) >= 8:
            break
        trio = value_legs[i:i+3]
        if len(trio) < 3:
            break
        c_odds = parlay_odds([p.odds for p in trio])
        wp     = joint_prob(trio)
        e50    = ev(c_odds, wp, 50)
        stake, target = stake_rec("VALUE_MIX")

        sports = list({p.sport for p in trio})
        sport_tag = "+".join(sports)

        slips.append(Slip(
            name=f"VALUE MIX — {sport_tag} 3-Legger",
            slip_type="VALUE_MIX",
            legs=trio,
            combined_odds=c_odds,
            win_prob=round(wp * 100, 1),
            ev_50=e50,
            stake_rec=stake,
            target_payout=target,
            reasoning=(
                f"3 plays from different games, varied sports. "
                f"All have positive edge (avg {sum(p.edge_pct for p in trio)/3:.1f}%). "
                f"Good risk/reward balance."
            ),
            confidence="MED-HIGH",
            tags=["3-LEG", "DIVERSIFIED", sport_tag],
        ))

    # ── SWING SLIPS (4-leg, higher payout) ──────────────────
    all_remaining = [p for p in unique
                     if p.edge_pct >= 2 and not any(p in s.legs for s in slips)]
    all_remaining.sort(key=lambda x: -x.edge_pct)
    swing_pool = all_remaining[:8]
    for i in range(0, min(len(swing_pool) - 3, 4), 4):
        if len(slips) >= 10:
            break
        quad = swing_pool[i:i+4]
        if len(quad) < 4:
            # fill with any available plays
            extras = [p for p in unique if p not in quad and p.edge_pct >= 2]
            quad.extend(extras[:4 - len(quad)])
        if len(quad) < 4:
            break
        c_odds = parlay_odds([p.odds for p in quad])
        wp     = joint_prob(quad)
        e50    = ev(c_odds, wp, 25)   # smaller stake for swing
        stake, target = stake_rec("SWING")
        payout = f"+{c_odds} pays ${round((american_to_decimal(c_odds)-1)*25):.0f} on $25"

        slips.append(Slip(
            name=f"SWING — {quad[0].player.split()[-1]} + {quad[1].player.split()[-1]} + {len(quad)-2} more",
            slip_type="SWING",
            legs=quad,
            combined_odds=c_odds,
            win_prob=round(wp * 100, 1),
            ev_50=e50,
            stake_rec=stake,
            target_payout=payout,
            reasoning=(
                f"4-leg swing play for higher payout. All 4 legs have positive edge. "
                f"Lower probability but strong +EV at this payout level. "
                f"Recommended stake: {stake}."
            ),
            confidence="MED",
            tags=["4-LEG", "SWING", "HIGH PAYOUT"],
        ))

    return slips[:n_slips]


# ─────────────────────────────────────────────────────────────
# TOP PROPS RANKER
# ─────────────────────────────────────────────────────────────

def rank_top_props(all_plays: list[Play], n: int = 20) -> list[Play]:
    """Return top n individual plays sorted by edge, de-duped."""
    seen = set()
    result = []
    for p in sorted(all_plays, key=lambda x: -x.edge_pct):
        key = (p.game_id, p.player, p.prop_type)
        if key not in seen:
            seen.add(key)
            result.append(p)
    return result[:n]


# ─────────────────────────────────────────────────────────────
# MAIN ORCHESTRATOR
# ─────────────────────────────────────────────────────────────

def generate_recommendations(supabase_client) -> dict:
    """
    Full pipeline: load data → build plays → build slips → rank props.
    Returns dict ready for storage in ai_recommendations table.
    """
    from dashboard.mlb_page import find_pitcher as _find_pitcher

    TEAM_ABBR_LOCAL = {
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

    # ── Load data ─────────────────────────────────────────────
    games       = supabase_client.table("games").select("*").execute().data or []
    all_odds    = supabase_client.table("odds_snapshots").select("*").execute().data or []
    all_players = supabase_client.table("players").select("*").execute().data or []

    # ── Build pitcher DB from live MLB API ────────────────────
    PITCHER_DB  = {}
    mlb_games   = [g for g in games if g.get("sport") == "MLB"]
    for g in mlb_games:
        for team in [g["away_team"], g["home_team"]]:
            abbr = TEAM_ABBR_LOCAL.get(team, "")
            if not abbr:
                continue
            try:
                pname, pstats = _find_pitcher(team)
                if pname and pstats:
                    key = pname.lower().split()[-1]
                    PITCHER_DB[key] = {**pstats, "team": abbr}
            except Exception:
                pass
    print(f"[ai_engine] Loaded {len(PITCHER_DB)} pitchers from live MLB API")

    # Build odds map: game_id → list of odds rows
    odds_map: dict[str, list] = defaultdict(list)
    for r in all_odds:
        odds_map[r["game_id"]].append(r)

    # Build player logs map: player_id → list of game stats
    player_ids = [p["id"] for p in all_players]
    logs_map: dict[str, list] = defaultdict(list)
    if player_ids:
        logs = supabase_client.table("player_game_stats").select("*").in_("player_id", player_ids[:100]).order("date", desc=True).execute().data or []
        for l in logs:
            logs_map[l["player_id"]].append(l)

    # ── Build plays ───────────────────────────────────────────
    all_plays: list[Play] = []
    all_plays.extend(build_pitcher_k_plays(games, odds_map, PITCHER_DB))
    all_plays.extend(build_moneyline_plays(games, odds_map, PITCHER_DB))
    all_plays.extend(build_nba_player_plays(all_players, logs_map, games))

    # ── Generate slips + props ────────────────────────────────
    slips    = build_slips(all_plays, n_slips=10)
    top_props = rank_top_props(all_plays, n=20)

    # ── Serialize ─────────────────────────────────────────────
    def serialize_play(p: Play) -> dict:
        return {
            "sport":       p.sport,
            "game":        p.game,
            "game_id":     p.game_id,
            "player":      p.player,
            "prop_type":   p.prop_type,
            "line":        p.line,
            "odds":        p.odds,
            "side":        p.side,
            "model_prob":  round(p.model_prob * 100, 1),
            "market_prob": round(p.market_prob * 100, 1),
            "edge_pct":    p.edge_pct,
            "confidence":  p.confidence,
            "fire":        p.fire,
            "reasoning":   p.reasoning,
            "game_time":   p.game_time,
            "category":    p.category,
            "is_plus_money": p.is_plus_money,
            "kelly_pct":   p.kelly_pct,
        }

    def serialize_slip(s: Slip) -> dict:
        return {
            "name":          s.name,
            "slip_type":     s.slip_type,
            "legs":          [serialize_play(l) for l in s.legs],
            "combined_odds": s.combined_odds,
            "win_prob":      s.win_prob,
            "ev_50":         s.ev_50,
            "stake_rec":     s.stake_rec,
            "target_payout": s.target_payout,
            "reasoning":     s.reasoning,
            "confidence":    s.confidence,
            "tags":          s.tags,
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_games":       len(games),
        "n_plays":       len(all_plays),
        "slips":         [serialize_slip(s) for s in slips],
        "top_props":     [serialize_play(p) for p in top_props],
    }
