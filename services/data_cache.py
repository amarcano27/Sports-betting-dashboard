"""
Shared data caching helpers to reduce redundant Supabase queries.

These helpers are deliberately lightweight (in-process TTL caches) so both
workers and Streamlit pages can reuse hydrated datasets without hammering the DB.
"""
from __future__ import annotations

import time
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from services.db import supabase

# Default TTLs (seconds)
SHORT_TTL = 30
MEDIUM_TTL = 120
LONG_TTL = 300

_cache: Dict[str, Dict[str, object]] = {}


def _make_cache_key(prefix: str, *parts: object) -> str:
    flattened = "::".join(str(part) for part in parts if part is not None)
    return f"{prefix}::{flattened}"


def _get_cached(key: str) -> Optional[object]:
    entry = _cache.get(key)
    now = time.time()
    if entry and entry["expires_at"] > now:
        return entry["value"]
    if entry:
        _cache.pop(key, None)
    return None


def _set_cached(key: str, value: object, ttl: int) -> None:
    _cache[key] = {"value": value, "expires_at": time.time() + ttl}


def _chunked(seq: Sequence[str], size: int = 100) -> Iterable[List[str]]:
    for idx in range(0, len(seq), size):
        yield list(seq[idx : idx + size])


def get_players_map(player_ids: Sequence[str], ttl: int = LONG_TTL) -> Dict[str, Dict]:
    """Return {player_id: player_row} for the requested IDs."""
    ids = sorted({pid for pid in player_ids if pid})
    if not ids:
        return {}
    key = _make_cache_key("players", ",".join(ids))
    cached = _get_cached(key)
    if cached is not None:
        return cached  # type: ignore[return-value]
    players: Dict[str, Dict] = {}
    for chunk in _chunked(ids, 200):
        resp = (
            supabase.table("players")
            .select("*")
            .in_("id", chunk)
            .execute()
        )
        for row in resp.data or []:
            if row.get("id"):
                players[row["id"]] = row
    _set_cached(key, players, ttl)
    return players


def get_games_map(game_ids: Sequence[str], ttl: int = MEDIUM_TTL) -> Dict[str, Dict]:
    """Return {game_id: game_row} for the requested IDs."""
    ids = sorted({gid for gid in game_ids if gid})
    if not ids:
        return {}
    key = _make_cache_key("games", ",".join(ids))
    cached = _get_cached(key)
    if cached is not None:
        return cached  # type: ignore[return-value]
    games: Dict[str, Dict] = {}
    for chunk in _chunked(ids, 200):
        resp = (
            supabase.table("games")
            .select("*")
            .in_("id", chunk)
            .execute()
        )
        for row in resp.data or []:
            if row.get("id"):
                games[row["id"]] = row
    _set_cached(key, games, ttl)
    return games


def get_recent_stats_map(
    player_ids: Sequence[str],
    limit_per_player: int = 15,
    ttl: int = SHORT_TTL,
) -> Dict[str, List[Dict]]:
    """
    Return {player_id: [recent stats]} for each requested player.

    The query batches IDs to minimize round-trips and trims each list to the
    desired per-player limit.
    """
    ids = sorted({pid for pid in player_ids if pid})
    if not ids:
        return {}
    key = _make_cache_key("player_stats", ",".join(ids), limit_per_player)
    cached = _get_cached(key)
    if cached is not None:
        return cached  # type: ignore[return-value]
    stats_map: Dict[str, List[Dict]] = {pid: [] for pid in ids}
    for chunk in _chunked(ids, 25):
        # Pull enough rows for the chunk (limit_per_player * chunk_size)
        chunk_limit = max(limit_per_player * len(chunk), limit_per_player)
        resp = (
            supabase.table("player_game_stats")
            .select("*")
            .in_("player_id", chunk)
            .order("date", desc=True)
            .limit(chunk_limit)
            .execute()
        )
        for row in resp.data or []:
            pid = row.get("player_id")
            if pid in stats_map:
                stats_map[pid].append(row)
    # Trim lists to requested limit
    for pid in list(stats_map.keys()):
        stats_map[pid] = stats_map[pid][:limit_per_player]
        if not stats_map[pid]:
            stats_map.pop(pid)
    _set_cached(key, stats_map, ttl)
    return stats_map


def get_projection_snapshots_map(
    player_ids: Sequence[str],
    game_ids: Optional[Sequence[str]] = None,
    prop_types: Optional[Sequence[str]] = None,
    ttl: int = SHORT_TTL,
) -> Dict[Tuple[str, Optional[str], str], Dict]:
    """
    Return {(player_id, game_id, prop_type): snapshot_row}.
    """
    ids = sorted({pid for pid in player_ids if pid})
    if not ids:
        return {}
    game_filter = {gid for gid in game_ids or [] if gid}
    prop_filter = {ptype for ptype in prop_types or [] if ptype}
    key = _make_cache_key(
        "projection_snapshots",
        ",".join(ids),
        ",".join(sorted(game_filter)) if game_filter else "",
        ",".join(sorted(prop_filter)) if prop_filter else "",
    )
    cached = _get_cached(key)
    if cached is not None:
        return cached  # type: ignore[return-value]
    snapshots: Dict[Tuple[str, Optional[str], str], Dict] = {}
    for chunk in _chunked(ids, 50):
        query = (
            supabase.table("player_projection_snapshots")
            .select("*")
            .in_("player_id", chunk)
        )
        if prop_filter:
            query = query.in_("prop_type", list(prop_filter))
        resp = query.execute()
        for row in resp.data or []:
            game_id = row.get("game_id")
            prop_type = row.get("prop_type")
            if prop_type is None:
                continue
            if game_filter and game_id not in game_filter:
                continue
            key_tuple = (row.get("player_id"), game_id, prop_type)
            snapshots[key_tuple] = row
    _set_cached(key, snapshots, ttl)
    return snapshots

