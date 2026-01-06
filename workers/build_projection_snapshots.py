"""
Worker that pre-computes player prop projection snapshots.

Usage:
    python workers/build_projection_snapshots.py --sport NBA --hours 48 --limit 300
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.data_cache import get_games_map, get_players_map
from services.db import supabase
from services.projections import calculate_projection


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build player projection snapshots")
    parser.add_argument("--sport", help="Filter by sport (NBA, NFL, etc.)")
    parser.add_argument("--hours", type=int, default=48, help="Lookback window for props")
    parser.add_argument("--limit", type=int, default=500, help="Max props to scan")
    parser.add_argument(
        "--verbose", action="store_true", help="Print per-projection debug output"
    )
    return parser.parse_args()


def _fetch_recent_props(hours: int, limit: int) -> List[Dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    query = (
        supabase.table("player_prop_odds")
        .select("id, player_id, game_id, prop_type, line, book, created_at")
        .gte("created_at", cutoff.isoformat())
        .order("created_at", desc=True)
    )
    if limit:
        query = query.limit(limit)
    resp = query.execute()
    return resp.data or []


def _dedupe_props(props: List[Dict]) -> Tuple[Dict[Tuple[str, str, str], Dict], Dict]:
    latest: Dict[Tuple[str, str, str], Dict] = {}
    bovada_lines: Dict[Tuple[str, str, str], float] = {}
    for prop in props:
        player_id = prop.get("player_id")
        game_id = prop.get("game_id")
        prop_type = prop.get("prop_type")
        if not all([player_id, game_id, prop_type]):
            continue
        key = (player_id, game_id, prop_type)
        created_at = prop.get("created_at") or ""
        if key not in latest or created_at > (latest[key].get("created_at") or ""):
            latest[key] = prop
        if prop.get("book") == "Bovada" and prop.get("line") is not None:
            bovada_lines[key] = prop["line"]
    return latest, bovada_lines


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
        # Fallback: assume player is home team
        opponent = away_team or home_team
        is_home = True if opponent == away_team else False
    return opponent, is_home


def build_snapshots(args: argparse.Namespace) -> None:
    props = _fetch_recent_props(args.hours, args.limit)
    if not props:
        print("No props found in the requested window.")
        return

    players_map = get_players_map([p.get("player_id") for p in props])
    games_map = get_games_map([p.get("game_id") for p in props])

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

    latest_props, bovada_lines = _dedupe_props(props)
    snapshots_to_upsert: List[Dict] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for key, prop in latest_props.items():
        player_id, game_id, prop_type = key
        player = players_map.get(player_id)
        game = games_map.get(game_id)
        if not player or not game:
            continue
        opponent, is_home = _resolve_matchup(player.get("team"), game)
        projection = calculate_projection(
            player_id=player_id,
            prop_type=prop_type,
            opponent_team=opponent,
            is_home=is_home if is_home is not None else True,
            game_id=game_id,
            bovada_line=bovada_lines.get(key),
        )
        projected_line = projection.get("projected_line")
        if projected_line is None:
            continue
        factors = projection.get("factors") or {}
        snapshot = {
            "player_id": player_id,
            "game_id": game_id,
            "sport": player.get("sport"),
            "prop_type": prop_type,
            "opponent": opponent,
            "is_home": is_home,
            "projected_line": projected_line,
            "confidence": projection.get("confidence"),
            "baseline_source": projection.get("baseline_source"),
            "bovada_line": projection.get("bovada_line"),
            "factors": factors,
            "sample_size": projection.get("sample_size"),
            "injury_status": projection.get("injury_status"),
            "rest_days": factors.get("rest_days"),
            "source_prop_id": prop.get("id"),
            "snapshot_version": "v1",
            "snapshot_at": now_iso,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        snapshots_to_upsert.append(snapshot)
        if args.verbose:
            print(
                f"{player.get('name')} {prop_type}: {projected_line} "
                f"(conf {projection.get('confidence')}, opp {opponent})"
            )

    if not snapshots_to_upsert:
        print("No projections produced; nothing to upsert.")
        return

    print(f"Upserting {len(snapshots_to_upsert)} projection snapshots...")
    for idx in range(0, len(snapshots_to_upsert), 100):
        chunk = snapshots_to_upsert[idx : idx + 100]
        supabase.table("player_projection_snapshots").upsert(
            chunk, on_conflict="player_id,game_id,prop_type"
        ).execute()
    print("Done.")


if __name__ == "__main__":
    arguments = _parse_args()
    build_snapshots(arguments)

