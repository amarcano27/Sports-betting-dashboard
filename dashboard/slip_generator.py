"""
Slip Generator - Generate optimal betting slips based on:
- Number of legs selected
- Sharper book lines (Bovada, Pinnacle)
- DFS line adjustments (1-1.5 higher on PrizePicks/Underdog)
- +EV plays
"""
from typing import Dict, List, Optional

from services.db import supabase
from services.line_helpers import (
    adjust_for_dfs_line,
    get_scraped_dfs_line,
    get_sharper_book_line,
)
from utils.ev import ev


def calculate_prop_edge_with_sharper_line(prop: Dict, stats: List[Dict], sharper_line: Optional[Dict] = None) -> Optional[Dict]:
    """
    Calculate edge using sharper book line if available
    
    Args:
        prop: The prop from database
        stats: Player stats for edge calculation
        sharper_line: Optional sharper book line (Bovada/Pinnacle)
    
    Returns:
        Edge data dict or None
    """
    if not stats:
        return None
    
    prop_type = prop.get("prop_type")
    
    # Use sharper line if available, otherwise use prop line
    if sharper_line:
        line = sharper_line["line"]
        # Use prices from sharper book
        over_price = sharper_line.get("over_price")
        under_price = sharper_line.get("under_price")
        book = sharper_line.get("book", "Unknown")
    else:
        line = prop.get("line")
        over_price = prop.get("over_price")
        under_price = prop.get("under_price")
        book = prop.get("book", "Unknown")
    
    if line is None:
        return None
    
    # Calculate true probability from stats
    prop_values = []
    for stat in stats:
        value = None
        if prop_type == "points":
            value = stat.get("points", 0)
        elif prop_type == "rebounds":
            value = stat.get("rebounds", 0)
        elif prop_type == "assists":
            value = stat.get("assists", 0)
        elif prop_type == "pra":
            value = (
                stat.get("points", 0) +
                stat.get("rebounds", 0) +
                stat.get("assists", 0)
            )
        elif prop_type == "threes":
            value = stat.get("three_pointers_made", 0)
        
        if value is not None:
            prop_values.append(value)
    
    if not prop_values:
        return None
    
    # Calculate true probability
    hits = sum(1 for v in prop_values if v > line)
    true_prob = hits / len(prop_values) if prop_values else 0.5
    
    # Calculate EV for over
    over_ev = None
    if over_price:
        over_ev = ev(true_prob, int(over_price))
    
    # Calculate EV for under
    under_ev = None
    if under_price:
        under_ev = ev(1 - true_prob, int(under_price))
    
    # Return best edge
    if over_ev is not None and under_ev is not None:
        if over_ev > under_ev:
            return {
                "edge": over_ev,
                "side": "over",
                "odds": over_price,
                "prob": true_prob,
                "line": line,
                "book": book,
                "sharper_book": sharper_line is not None
            }
        else:
            return {
                "edge": under_ev,
                "side": "under",
                "odds": under_price,
                "prob": 1 - true_prob,
                "line": line,
                "book": book,
                "sharper_book": sharper_line is not None
            }
    elif over_ev is not None:
        return {
            "edge": over_ev,
            "side": "over",
            "odds": over_price,
            "prob": true_prob,
            "line": line,
            "book": book,
            "sharper_book": sharper_line is not None
        }
    elif under_ev is not None:
        return {
            "edge": under_ev,
            "side": "under",
            "odds": under_price,
            "prob": 1 - true_prob,
            "line": line,
            "book": book,
            "sharper_book": sharper_line is not None
        }
    
    return None


def generate_optimal_slip(
    props: List[Dict],
    num_legs: int,
    min_edge: float = 0.0,
    use_sharper_books: bool = True,
    adjust_for_dfs: bool = True
) -> List[Dict]:
    """
    Generate optimal slip with specified number of legs
    
    Args:
        props: List of all available props
        num_legs: Number of legs desired
        min_edge: Minimum edge required (default 0.0 for any +EV)
        use_sharper_books: Whether to prefer Bovada/Pinnacle lines
        adjust_for_dfs: Whether to adjust lines for DFS (add 1-1.5)
    
    Returns:
        List of selected leg dicts
    """
    # Import functions needed for edge calculation
    # Avoid circular import by importing here
    from services.db import supabase as supabase_import
    
    candidates = []
    seen_props = set()
    
    # Process all props to find best candidates
    for prop in props:
        player_id = prop.get("player_id")
        if not player_id:
            continue
        
        # Skip duplicates
        prop_key = (
            player_id,
            prop.get("game_id"),
            prop.get("prop_type"),
            prop.get("line"),
            prop.get("book")
        )
        if prop_key in seen_props:
            continue
        seen_props.add(prop_key)
        
        # Get sharper book line if requested
        sharper_line = None
        if use_sharper_books:
            sharper_line = get_sharper_book_line(
                player_id,
                prop.get("game_id"),
                prop.get("prop_type")
            )
        
        # Load player stats for edge calculation
        try:
            stats = (
                supabase_import.table("player_game_stats")
                .select("*")
                .eq("player_id", player_id)
                .order("date", desc=True)
                .limit(15)
                .execute()
                .data
            )
        except:
            stats = []
        
        # Calculate edge with sharper line
        edge_data = calculate_prop_edge_with_sharper_line(prop, stats, sharper_line)
        
        if not edge_data or edge_data.get("edge", 0) < min_edge:
            continue
        
        # Get DFS line (scraped or calculated)
        base_line = sharper_line["line"] if sharper_line else prop.get("line")
        dfs_line = None
        
        if adjust_for_dfs and base_line is not None:
            # First, try to get scraped DFS line from database
            game_id = prop.get("game_id")
            if game_id:
                # Try PrizePicks first, then Underdog
                scraped_line = get_scraped_dfs_line(player_id, game_id, prop.get("prop_type"), "prizepicks")
                if not scraped_line:
                    scraped_line = get_scraped_dfs_line(player_id, game_id, prop.get("prop_type"), "underdog")
                
                if scraped_line:
                    dfs_line = scraped_line
                else:
                    # Fallback to heuristic adjustment if no scraped line
                    dfs_line = adjust_for_dfs_line(base_line, prop.get("prop_type"))
            else:
                # No game_id, use heuristic
                dfs_line = adjust_for_dfs_line(base_line, prop.get("prop_type"))
        
        # Get player info
        player_info = prop.get("players", {})
        if not isinstance(player_info, dict) or not player_info.get("name"):
            continue
        
        leg = {
            "prop_id": prop.get("id"),
            "player_id": player_id,
            "player_name": player_info.get("name", "Unknown"),
            "prop_type": prop.get("prop_type", ""),
            "line": sharper_line["line"] if sharper_line else prop.get("line"),
            "dfs_line": dfs_line,  # Adjusted line for DFS
            "side": edge_data.get("side", "over"),
            "odds": edge_data.get("odds"),
            "book": edge_data.get("book", prop.get("book", "Unknown")),
            "edge": edge_data.get("edge", 0),
            "prob": edge_data.get("prob", 0.5),
            "game_id": prop.get("game_id"),
            "sharper_book": edge_data.get("sharper_book", False)
        }
        
        candidates.append(leg)
    
    # Sort by edge (highest first)
    candidates.sort(key=lambda x: x.get("edge", 0), reverse=True)
    
    # Select diverse props (different players, different prop types, different games)
    selected_legs = []
    selected_players = set()
    selected_prop_types = set()
    selected_games = set()
    
    for leg in candidates:
        player_id = leg.get("player_id")
        game_id = leg.get("game_id")
        prop_type = leg.get("prop_type")
        
        # Prefer diversity: avoid same player if we already have enough
        if player_id in selected_players and len(selected_legs) >= 3:
            continue
        
        # Prefer diversity: avoid same game if we already have 2 from that game
        game_count = sum(1 for l in selected_legs if l.get("game_id") == game_id)
        if game_count >= 2:
            continue
        
        selected_legs.append(leg)
        selected_players.add(player_id)
        selected_prop_types.add(prop_type)
        selected_games.add(game_id)
        
        # Stop when we have enough legs
        if len(selected_legs) >= num_legs:
            break
    
    # If we don't have enough diverse props, fill with best available
    if len(selected_legs) < num_legs:
        for leg in candidates:
            if leg not in selected_legs:
                selected_legs.append(leg)
                if len(selected_legs) >= num_legs:
                    break
    
    return selected_legs[:num_legs]

