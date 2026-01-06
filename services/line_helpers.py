"""
Line helper utilities shared between workers and dashboard components.
"""
from __future__ import annotations

from typing import Dict, Optional

from services.db import supabase

SHARPER_BOOKS = ["Bovada", "Pinnacle", "DraftKings", "FanDuel", "BetMGM"]


def get_scraped_dfs_line(
    player_id: str,
    game_id: str,
    prop_type: str,
    source: str = "prizepicks",
) -> Optional[float]:
    """Return the most recent DFS line (PrizePicks/Underdog) for the player/prop."""
    try:
        dfs_lines = (
            supabase.table("dfs_lines")
            .select("line")
            .eq("player_id", player_id)
            .eq("game_id", game_id)
            .eq("prop_type", prop_type)
            .eq("source", source)
            .order("scraped_at", desc=True)
            .limit(1)
            .execute()
        )
        if dfs_lines.data and dfs_lines.data[0].get("line") is not None:
            return dfs_lines.data[0]["line"]
    except Exception:
        pass
    return None


def adjust_for_dfs_line(book_line: float, prop_type: str) -> float:
    """
    Heuristically adjust sharper book lines to match DFS apps.

    PrizePicks/Underdog tend to hang lines 1-1.5 units higher depending on the stat.
    """
    adjustments = {
        "points": 1.5,
        "rebounds": 1.0,
        "assists": 1.0,
        "pra": 2.5,
        "threes": 0.5,
    }
    adjustment = adjustments.get(prop_type, 1.0)
    dfs_line = book_line + adjustment
    return round(dfs_line * 2) / 2  # DFS lines use .5 increments


def get_sharper_book_line(player_id: str, game_id: str, prop_type: str) -> Optional[Dict]:
    """
    Return the latest line from the prioritized sharper books list.
    """
    try:
        for book in SHARPER_BOOKS:
            props = (
                supabase.table("player_prop_odds")
                .select("line, over_price, under_price, book")
                .eq("player_id", player_id)
                .eq("game_id", game_id)
                .eq("prop_type", prop_type)
                .eq("book", book)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if props.data and props.data[0].get("line") is not None:
                return {
                    "line": props.data[0]["line"],
                    "over_price": props.data[0].get("over_price"),
                    "under_price": props.data[0].get("under_price"),
                    "book": book,
                }
        props = (
            supabase.table("player_prop_odds")
            .select("line, over_price, under_price, book")
            .eq("player_id", player_id)
            .eq("game_id", game_id)
            .eq("prop_type", prop_type)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if props.data and props.data[0].get("line") is not None:
            return {
                "line": props.data[0]["line"],
                "over_price": props.data[0].get("over_price"),
                "under_price": props.data[0].get("under_price"),
                "book": props.data[0].get("book", "Unknown"),
            }
    except Exception:
        pass
    return None

