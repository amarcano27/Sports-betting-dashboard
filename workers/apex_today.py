"""
APEX LLM Analysis Writer
========================
Reads today's latest ai_recommendations row, builds the APEX analysis,
and PATCHes it back as llm_analysis.

Run manually any time after build_ai_recommendations.py has inserted a fresh row,
or trigger via the Claude Code scheduled task.
"""
import sys, io, json, os, requests
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
KEY          = os.getenv('SUPABASE_KEY', '')
HEADERS      = {
    'apikey':        KEY,
    'Authorization': f'Bearer {KEY}',
    'Content-Type':  'application/json',
    'Prefer':        'return=minimal',
}


# ─────────────────────────────────────────────────────────────
# STEP 1 — get latest row ID + math engine results
# ─────────────────────────────────────────────────────────────

def get_latest_row():
    r = requests.get(
        f'{SUPABASE_URL}/rest/v1/ai_recommendations'
        '?select=id,generated_at,n_games,n_plays,slips,top_props'
        '&order=generated_at.desc&limit=1',
        headers=HEADERS,
    )
    rows = r.json()
    return rows[0] if rows else None


# ─────────────────────────────────────────────────────────────
# STEP 2 — get today's odds from Supabase
# ─────────────────────────────────────────────────────────────

def get_todays_games():
    r = requests.get(
        f'{SUPABASE_URL}/rest/v1/games'
        '?select=id,sport,home_team,away_team,start_time'
        '&order=start_time.asc&limit=50',
        headers=HEADERS,
    )
    return r.json()


def get_todays_odds(game_ids: list[str]):
    if not game_ids:
        return []
    id_list = ','.join(game_ids[:20])
    r = requests.get(
        f'{SUPABASE_URL}/rest/v1/odds_snapshots'
        f'?select=game_id,market_type,market_label,line,price'
        f'&game_id=in.({id_list})'
        '&order=created_at.desc&limit=2000',
        headers=HEADERS,
    )
    return r.json()


# ─────────────────────────────────────────────────────────────
# STEP 3 — build analysis from live data
# ─────────────────────────────────────────────────────────────

def build_analysis(row: dict, games: list, odds: list) -> dict:
    """
    Build APEX analysis JSON from live Supabase data.
    Uses math engine's top_props + slips as the base, enriches with
    expert reasoning for each play.
    """
    today = datetime.now().strftime('%B %d, %Y').replace(' 0', ' ')
    slips_raw     = row.get('slips') or []
    top_props_raw = row.get('top_props') or []

    if isinstance(slips_raw, str):
        slips_raw = json.loads(slips_raw)
    if isinstance(top_props_raw, str):
        top_props_raw = json.loads(top_props_raw)

    # Build odds map: game_id -> {away_ml, home_ml, total}
    odds_map: dict[str, dict] = {}
    for o in odds:
        gid = o['game_id']
        if gid not in odds_map:
            odds_map[gid] = {}
        mt = o.get('market_type', '')
        if mt == 'h2h':
            odds_map[gid].setdefault('h2h', []).append({
                'label': o.get('market_label'), 'price': o.get('price')
            })
        elif mt == 'totals':
            odds_map[gid]['total'] = o.get('line')

    # Build game lookup
    game_lookup = {g['id']: g for g in games}

    # Build priority rankings from top_props
    rankings = []
    medals = {1: '🥇', 2: '🥈', 3: '🥉'}
    for i, p in enumerate(top_props_raw[:13], 1):
        conf  = p.get('confidence', 'MED')
        plus  = p.get('is_plus_money', False)
        fire  = p.get('fire', '🔥')
        edge  = p.get('edge_pct', 0)
        odds_val = p.get('odds', 0)
        mkt_prob = p.get('market_prob', 0)
        mdl_prob = p.get('model_prob', 0)
        cat  = p.get('category', '')
        side = p.get('side', '')
        line = p.get('line')
        play_str = f"{p.get('player', '')} {side} {line if line else ''} {cat}".strip()
        game_str = p.get('game', '')
        gt   = p.get('game_time', '')
        rankings.append({
            'rank':         i,
            'medal':        medals.get(i, '⚠️' if conf == 'MED' else ''),
            'ref':          f"{'P' if cat == 'Pitcher K' else 'M' if cat == 'Moneyline' else 'H' if cat == 'Hitter Prop' else 'N'}{i}",
            'play':         play_str,
            'game':         f"{game_str} ({gt})" if gt else game_str,
            'odds':         f"+{odds_val}" if odds_val > 0 else str(odds_val),
            'implied_pct':  f"{mkt_prob:.1f}%",
            'real_est_pct': f"{mdl_prob:.0f}-{mdl_prob+4:.0f}%",
            'edge':         f"+{edge:.1f}%",
            'stake_rec':    '$25-$40' if conf == 'HIGH' else '$15-$25',
            'best_use':     p.get('reasoning', '')[:80],
            'one_liner':    p.get('reasoning', '')[:100],
        })

    # Build slip structures from math engine
    slip_icons = {'ANCHOR': '🔵', 'CORRELATED': '🟢', 'VALUE_MIX': '🟡', 'SWING': '🔴'}
    built_slips = []
    for i, s in enumerate(slips_raw[:4], 1):
        stype = s.get('slip_type', 'ANCHOR')
        legs  = s.get('legs', [])
        built_legs = []
        for j, leg in enumerate(legs, 1):
            lo = leg.get('odds', 0)
            built_legs.append({
                'ref':        f"L{j}",
                'leg_number': j,
                'play':       f"{leg.get('player','')} {leg.get('side','')} {leg.get('line','') or ''} {leg.get('category','')} — {leg.get('game','')} ({leg.get('game_time','')})".strip(),
                'odds':       f"+{lo}" if lo > 0 else str(lo),
                'confidence': leg.get('confidence', 'MED'),
                'fire':       leg.get('fire', '🔥'),
                'key_reason': leg.get('reasoning', '')[:100],
            })
        c_odds = s.get('combined_odds', 0)
        wp     = s.get('win_prob', 0)
        built_slips.append({
            'number':              i,
            'emoji':               slip_icons.get(stype, '🔵'),
            'name':                s.get('name', f'Slip {i}'),
            'type':                stype,
            'stake_rec':           s.get('stake_rec', '$25-$50'),
            'target':              s.get('target_payout', ''),
            'confidence':          s.get('confidence', 'MED'),
            'combined_odds_approx': f"+{c_odds}" if c_odds > 0 else str(c_odds),
            'win_prob_approx':     f"{wp:.0f}%",
            'legs':                built_legs,
            'slip_note':           f"📌 {s.get('reasoning', '')}",
        })

    # Top K props and MLs for display cards
    k_props  = [p for p in top_props_raw if p.get('category') == 'Pitcher K']
    mls      = [p for p in top_props_raw if p.get('category') == 'Moneyline']
    hitters  = [p for p in top_props_raw if p.get('category') not in ('Pitcher K', 'Moneyline')]

    def fmt_play_card(p: dict, ref_prefix: str, idx: int) -> dict:
        lo   = p.get('odds', 0)
        mp   = p.get('market_prob', 0)
        mdl  = p.get('model_prob', 0)
        edge = p.get('edge_pct', 0)
        conf = p.get('confidence', 'MED')
        plus = p.get('is_plus_money', False)
        status = ('✅ BEST VALUE' if conf == 'HIGH' and plus
                  else '✅ STRONG' if conf == 'HIGH'
                  else '⚡ PLAY' if conf == 'MED-HIGH'
                  else '🔄 LEAN')
        return {
            'ref':          f"{ref_prefix}{idx}",
            'pitcher' if ref_prefix == 'P' else 'player' if ref_prefix == 'H' else 'team':
                            p.get('player', ''),
            'game':         p.get('game', ''),
            'time':         p.get('game_time', ''),
            'line':         p.get('line'),
            'odds':         f"+{lo}" if lo > 0 else str(lo),
            'implied_pct':  f"{mp:.1f}%",
            'model_est_pct': f"{mdl:.0f}-{mdl+4:.0f}%",
            'edge':         f"+{edge:.1f}%",
            'confidence':   conf,
            'fire':         p.get('fire', '🔥'),
            'status':       status,
            'stake_rec':    '$20-$30' if conf == 'HIGH' else '$10-$20',
            'reasoning':    p.get('reasoning', ''),
        }

    top_prop = top_props_raw[0] if top_props_raw else {}
    summary = (
        f"{today} slate: {len(games)} games across MLB/NBA/NHL. "
        f"Top play: {top_prop.get('player','')} "
        f"{top_prop.get('side','')} {top_prop.get('line','')} "
        f"at +{top_prop.get('edge_pct',0):.1f}% edge. "
        f"Math engine identified {row.get('n_plays',0)} plays across "
        f"{len(built_slips)} slips."
    )

    return {
        'executive_summary':  summary,
        'slate_breakdown':    [],
        'pitcher_k_props':    [fmt_play_card(p, 'P', i) for i, p in enumerate(k_props[:6], 1)],
        'hitter_props':       [fmt_play_card(p, 'H', i) for i, p in enumerate(hitters[:4], 1)],
        'moneylines':         [fmt_play_card(p, 'M', i) for i, p in enumerate(mls[:8], 1)],
        'priority_rankings':  rankings,
        'slips':              built_slips,
        'skips':              [],
        'full_markdown_writeup': (
            f"# {today} — APEX BETTING CART\n\n"
            f"**{row.get('n_plays',0)} plays identified across {len(games)} games.**\n\n"
            "## PRIORITY RANKINGS\n\n"
            + '\n'.join(
                f"{r['medal']} {r['rank']}. {r['play']} | {r['odds']} | Edge {r['edge']} | {r['stake_rec']}"
                for r in rankings
            )
            + "\n\n## SLIPS\n\n"
            + '\n'.join(
                f"**SLIP {s['number']} — {s['type']}** {s['combined_odds_approx']} | {s['stake_rec']}\n"
                + '\n'.join(f"  - Leg {l['leg_number']}: {l['play']} ({l['odds']})" for l in s['legs'])
                for s in built_slips
            )
        ),
        'generated_at':  datetime.now(timezone.utc).isoformat(),
        'model_used':    'apex-math-engine',
        'n_games':       len(games),
        'n_props':       row.get('n_plays', 0),
    }


# ─────────────────────────────────────────────────────────────
# STEP 4 — PATCH to Supabase
# ─────────────────────────────────────────────────────────────

def patch_analysis(row_id: str, analysis: dict):
    r = requests.patch(
        f'{SUPABASE_URL}/rest/v1/ai_recommendations?id=eq.{row_id}',
        headers=HEADERS,
        data=json.dumps({'llm_analysis': analysis}, ensure_ascii=False).encode('utf-8'),
    )
    return r.status_code


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def run():
    print(f"[apex] Starting — {datetime.now().strftime('%H:%M ET')}")

    row = get_latest_row()
    if not row:
        print("[apex] No ai_recommendations row found — run build_ai_recommendations.py first")
        return

    row_id = row['id']
    print(f"[apex] Latest row: {row_id} | generated {row['generated_at']} | {row.get('n_plays',0)} plays")

    games = get_todays_games()
    print(f"[apex] Loaded {len(games)} games from Supabase")

    # Get odds for today's game IDs
    today_ids = [g['id'] for g in games[:20]]
    odds = get_todays_odds(today_ids)
    print(f"[apex] Loaded {len(odds)} odds rows")

    analysis = build_analysis(row, games, odds)
    status = patch_analysis(row_id, analysis)

    if status in (200, 204):
        print(f"[apex] Patched row {row_id} — {analysis.get('n_props',0)} plays, "
              f"{len(analysis.get('slips',[]))} slips, "
              f"{len(analysis.get('priority_rankings',[]))} rankings")
    else:
        print(f"[apex] PATCH failed — status {status}")


if __name__ == '__main__':
    run()
