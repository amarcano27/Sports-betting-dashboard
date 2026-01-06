"""
Worker that assembles enriched prop feed snapshots for the dashboard.

Usage:
    python workers/build_prop_feed_snapshots.py --sport NBA --hours 48 --limit 600
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.data_cache import (
    get_games_map,
    get_players_map,
    get_projection_snapshots_map,
    get_recent_stats_map,
)
from services.db import supabase
from services.line_helpers import adjust_for_dfs_line, get_scraped_dfs_line
from services.projections import get_prop_value_from_stat
from utils.ev import ev


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build prop feed snapshots")
    parser.add_argument("--sport", help="Filter by sport")
    parser.add_argument("--hours", type=int, default=48, help="Lookback window")
    parser.add_argument("--limit", type=int, default=800, help="Max props to scan")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    return parser.parse_args()


def _fetch_recent_props(hours: int, limit: int) -> List[Dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    query = (
        supabase.table("player_prop_odds")
        .select(
            "id, player_id, game_id, prop_type, line, over_price, under_price, book, created_at"
        )
        .gte("created_at", cutoff.isoformat())
        .order("created_at", desc=True)
    )
    if limit:
        query = query.limit(limit)
    resp = query.execute()
    return resp.data or []


def _dedupe_props(props: List[Dict]) -> List[Dict]:
    latest: Dict[Tuple[str, str, str, float, str], Dict] = {}
    for prop in props:
        player_id = prop.get("player_id")
        game_id = prop.get("game_id")
        prop_type = prop.get("prop_type")
        line = prop.get("line")
        book = prop.get("book")
        if not all([player_id, game_id, prop_type, book]) or line is None:
            continue
        key = (player_id, game_id, prop_type, float(line), book)
        created_at = prop.get("created_at") or ""
        if key not in latest or created_at > (latest[key].get("created_at") or ""):
            latest[key] = prop
    return list(latest.values())


def _resolve_matchup(player_team: Optional[str], game: Dict) -> Tuple[Optional[str], Optional[bool]]:
    if not game:
        return None, None
    home_team = game.get("home_team")
    away_team = game.get("away_team")
    opponent = None
    is_home = None
    if player_team:
        if player_team == home_team:
            opponent = away_team
            is_home = True
        elif player_team == away_team:
            opponent = home_team
            is_home = False
    if opponent is None:
        opponent = away_team or home_team
        is_home = True if opponent == away_team else False
    return opponent, is_home


def _build_sparkline_values(stats: List[Dict], prop_type: str, limit: int = 10) -> List[float]:
    if not stats:
        return []
    recent = stats[:limit]
    values: List[float] = []
    for stat in reversed(recent):
        value = get_prop_value_from_stat(stat, prop_type)
        if value is not None:
            values.append(float(value))
    return values


def _calculate_matchup_stats(stats: List[Dict], opponent: Optional[str], prop_type: str) -> Optional[Dict]:
    if not stats or not opponent:
        return None
    values = [
        get_prop_value_from_stat(stat, prop_type)
        for stat in stats
        if stat.get("opponent") == opponent
    ]
    values = [float(v) for v in values if v is not None]
    if not values:
        return None
    return {
        "avg_vs_opponent": sum(values) / len(values),
        "games": len(values),
    }


def _calculate_edge_and_hitrate(prop: Dict, stats: List[Dict]) -> Tuple[Optional[Dict], Optional[Dict]]:
    if not stats or prop.get("line") is None:
        return None, None
    prop_type = prop.get("prop_type")
    line = float(prop.get("line"))
    prop_values: List[float] = []
    for stat in stats:
        value = get_prop_value_from_stat(stat, prop_type)
        if value is not None:
            prop_values.append(float(value))
    if not prop_values:
        return None, None
    total_games = len(prop_values)
    hits_over = sum(1 for v in prop_values if v > line)
    hits_under = sum(1 for v in prop_values if v < line)
    pushes = total_games - hits_over - hits_under
    smoothing = 0.1
    over_prob = (hits_over + smoothing) / (total_games + smoothing * 2)
    under_prob = (hits_under + smoothing) / (total_games + smoothing * 2)
    total_prob = over_prob + under_prob
    if total_prob > 0:
        over_prob /= total_prob
        under_prob /= total_prob
    over_price = prop.get("over_price")
    under_price = prop.get("under_price")
    over_ev = ev(over_prob, int(over_price)) if over_price else None
    under_ev = ev(under_prob, int(under_price)) if under_price else None
    edge_data = None
    if over_ev is not None and (under_ev is None or over_ev >= under_ev):
        edge_data = {"edge": over_ev, "side": "over", "prob": over_prob, "odds": over_price}
    elif under_ev is not None:
        edge_data = {"edge": under_ev, "side": "under", "prob": under_prob, "odds": under_price}
    hit_rate = {
        "total_games": total_games,
        "over_pct": round((hits_over / total_games) * 100, 1),
        "under_pct": round((hits_under / total_games) * 100, 1),
        "pushes": pushes,
        "over_count": hits_over,
        "under_count": hits_under,
    }
    return edge_data, hit_rate


def build_snapshots(args: argparse.Namespace) -> None:
    props = _fetch_recent_props(args.hours, args.limit)
    if not props:
        print("No props found in requested window.")
        return
    players_map = get_players_map([p.get("player_id") for p in props])
    if args.sport:
        if args.sport == "Esports":
            sub_sports = ["CS2", "LoL", "Dota2", "Valorant"]
            props = [
                prop
                for prop in props
                if players_map.get(prop.get("player_id"), {}).get("sport") in sub_sports
            ]
        else:
            props = [
                prop
                for prop in props
                if players_map.get(prop.get("player_id"), {}).get("sport") == args.sport
            ]
        if not props:
            print(f"No props found for sport {args.sport}.")
            return
    props = _dedupe_props(props)
    games_map = get_games_map([p.get("game_id") for p in props])
    stats_map = get_recent_stats_map([p.get("player_id") for p in props], limit_per_player=20)
    projection_map = get_projection_snapshots_map(
        [p.get("player_id") for p in props],
        game_ids=[p.get("game_id") for p in props],
        prop_types=[p.get("prop_type") for p in props],
    )
    now_iso = datetime.now(timezone.utc).isoformat()
    rows: List[Dict] = []
    for prop in props:
        player_id = prop.get("player_id")
        game_id = prop.get("game_id")
        prop_type = prop.get("prop_type")
        if not all([player_id, game_id, prop_type]):
            continue
        player = players_map.get(player_id)
        game = games_map.get(game_id)
        if not player or not game:
            continue
        stats = stats_map.get(player_id, [])
        edge_data, hit_rate = _calculate_edge_and_hitrate(prop, stats)
        opponent, is_home = _resolve_matchup(player.get("team"), game)
        projection = projection_map.get((player_id, game_id, prop_type))
        dfs_line = None
        if prop.get("line") is not None:
            dfs_line = get_scraped_dfs_line(player_id, game_id, prop_type, "prizepicks")
            if dfs_line is None:
                dfs_line = get_scraped_dfs_line(player_id, game_id, prop_type, "underdog")
            if dfs_line is None:
                dfs_line = adjust_for_dfs_line(float(prop.get("line")), prop_type)
        row = {
            "prop_id": prop.get("id"),
            "player_id": player_id,
            "game_id": game_id,
            "sport": player.get("sport"),
            "player_name": player.get("name"),
            "team": player.get("team"),
            "opponent": opponent,
            "is_home": is_home,
            "prop_type": prop_type,
            "line": prop.get("line"),
            "over_price": prop.get("over_price"),
            "under_price": prop.get("under_price"),
            "book": prop.get("book"),
            "projection_line": projection.get("projected_line") if projection else None,
            "projection_confidence": projection.get("confidence") if projection else None,
            "projection_baseline": projection.get("baseline_source") if projection else None,
            "projection_bovada_line": projection.get("bovada_line") if projection else None,
            "edge": edge_data.get("edge") if edge_data else None,
            "edge_side": edge_data.get("side") if edge_data else None,
            "edge_prob": edge_data.get("prob") if edge_data else None,
            "ev_odds": edge_data.get("odds") if edge_data else None,
            "hitrate_over_pct": hit_rate.get("over_pct") if hit_rate else None,
            "hitrate_under_pct": hit_rate.get("under_pct") if hit_rate else None,
            "hitrate_games": hit_rate.get("total_games") if hit_rate else None,
            "dfs_line": dfs_line,
            "snapshot_at": now_iso,
            "source_prop_created_at": prop.get("created_at"),
            "metadata": {
                "edge": edge_data,
                "hit_rate": hit_rate,
                "sparkline_values": _build_sparkline_values(stats, prop_type),
                "matchup_stats": _calculate_matchup_stats(stats, opponent, prop_type),
                "player_position": player.get("position"),
                "projection_snapshot": {
                    "injury_status": projection.get("injury_status") if projection else None,
                    "rest_days": projection.get("rest_days") if projection else None,
                    "factors": projection.get("factors") if projection else None,
                } if projection else None,
            },
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        rows.append(row)
        if args.verbose:
            proj_line = row["projection_line"]
            edge = row["edge"]
            print(
                f"{player.get('name')} {prop_type} {prop.get('line')} "
                f"proj={proj_line} edge={edge}"
            )
    if not rows:
        print("No rows produced.")
        return
    print(f"Upserting {len(rows)} prop feed snapshots...")
    for idx in range(0, len(rows), 100):
        chunk = rows[idx : idx + 100]
        supabase.table("prop_feed_snapshots").upsert(
            chunk, on_conflict="prop_id"
        ).execute()
    print("Done.")


if __name__ == "__main__":
    build_snapshots(_parse_args())

