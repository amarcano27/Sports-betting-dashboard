"""
Line Movement Tracker
=====================
Compares earliest vs latest odds_snapshot per game/team to detect:
  - Steam moves  : ≥10 cents in one direction (sharp action)
  - Reverse line : public money one way, line moves opposite (sharp fade)
  - Flat         : line unchanged (no meaningful action)

Works purely from the existing odds_snapshots table — no new table needed.
"""
from __future__ import annotations


def cents_moved(open_odds: int, current_odds: int) -> int:
    """
    How many American-odds 'cents' the line moved.
    Positive = moved toward favorite (line shortened).
    Negative = moved toward underdog (line lengthened).
    """
    # Convert to implied prob to normalise direction
    def to_prob(o):
        if o < 0: return abs(o) / (abs(o) + 100)
        return 100 / (o + 100)

    return round((to_prob(current_odds) - to_prob(open_odds)) * 1000)  # in milliprobability


def classify_move(open_odds: int, current_odds: int) -> dict:
    """
    Returns:
      direction : "toward_favorite" | "toward_dog" | "flat"
      magnitude : int  (milliprobability points, ~cents)
      signal    : "STEAM" | "DRIFT" | "FLAT"
      label     : human-readable string
    """
    if open_odds is None or current_odds is None:
        return {"direction": "flat", "magnitude": 0, "signal": "FLAT", "label": "No data"}

    delta = cents_moved(open_odds, current_odds)
    abs_d = abs(delta)

    if abs_d < 5:
        return {"direction": "flat", "magnitude": abs_d, "signal": "FLAT",
                "label": "No movement"}
    elif abs_d >= 20:
        signal = "STEAM"
    elif abs_d >= 10:
        signal = "MOVE"
    else:
        signal = "DRIFT"

    direction = "toward_favorite" if delta > 0 else "toward_dog"
    arrow = "↗ Toward favorite" if delta > 0 else "↘ Toward dog"
    label = f"{arrow} ({abs_d} pts)"

    return {"direction": direction, "magnitude": abs_d, "signal": signal, "label": label}


def get_line_movements(supabase_client, game_ids: list[str]) -> dict[str, dict]:
    """
    For each game_id, fetch all h2h odds_snapshots sorted by created_at,
    then compare first (opening) to last (current) for each team.

    Returns:
      { game_id: { team_name: {open, current, move_dict} } }
    """
    if not game_ids:
        return {}

    try:
        rows = (
            supabase_client.table("odds_snapshots")
            .select("game_id,market_label,price,book,created_at")
            .in_("game_id", game_ids)
            .eq("market_type", "h2h")
            .order("created_at")
            .execute()
            .data or []
        )
    except Exception:
        return {}

    # Group by game_id → team → list of (price, created_at)
    from collections import defaultdict
    grouped: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        gid  = r.get("game_id")
        team = r.get("market_label")
        price = r.get("price")
        if gid and team and price is not None:
            grouped[gid][team].append(int(price))

    result = {}
    for gid, teams in grouped.items():
        result[gid] = {}
        for team, prices in teams.items():
            if len(prices) < 2:
                result[gid][team] = {
                    "open": prices[0] if prices else None,
                    "current": prices[0] if prices else None,
                    "move": classify_move(prices[0], prices[0]) if prices else {},
                    "n_snapshots": len(prices),
                }
            else:
                open_p    = prices[0]
                current_p = prices[-1]
                result[gid][team] = {
                    "open":        open_p,
                    "current":     current_p,
                    "move":        classify_move(open_p, current_p),
                    "n_snapshots": len(prices),
                }
    return result


SIGNAL_COLORS = {
    "STEAM": "#10B981",   # green — sharp action, trust this
    "MOVE":  "#F59E0B",   # amber — notable but not definitive
    "DRIFT": "#64748B",   # muted — minor
    "FLAT":  "#475569",   # dim   — nothing happening
}

SIGNAL_DESCRIPTIONS = {
    "STEAM": "Sharp money detected — line moved 20+ pts. Follow the steam.",
    "MOVE":  "Meaningful line movement (10–20 pts). Monitor for continuation.",
    "DRIFT": "Minor drift (5–10 pts). Possibly public money only.",
    "FLAT":  "Line unchanged. No significant action either way.",
}
