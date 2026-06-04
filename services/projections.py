"""
Projection Service - Calculate custom player prop lines based on:
- Bovada lines as baseline
- Historical performance
- Opponent defense stats
- Matchup analysis (vs teams, positions)
- Recent form
- Injuries
- Pace factors
- Home/away splits
- Rest days and back-to-back games
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from services.db import supabase
BOOK_WEIGHTS = {
    "Pinnacle": 1.35,
    "Bovada": 1.2,
    "DraftKings": 1.1,
    "FanDuel": 1.1,
    "BetMGM": 1.0,
    "Caesars": 1.0,
    "bet365": 1.0,
}


def get_market_consensus_line(player_id: str, game_id: str, prop_type: str) -> Dict:
    """
    Build a weighted market consensus line from all available books.

    Returns:
        {
            "line": float | None,
            "books": int,
            "book_list": [str],
            "dispersion": float | None
        }
    """
    try:
        rows = (
            supabase.table("player_prop_odds")
            .select("line, book")
            .eq("player_id", player_id)
            .eq("game_id", game_id)
            .eq("prop_type", prop_type)
            .order("created_at", desc=True)
            .limit(200)
            .execute()
            .data
            or []
        )
    except Exception:
        rows = []

    by_book = {}
    for r in rows:
        line = r.get("line")
        book = r.get("book")
        if line is None or not book:
            continue
        if book not in by_book:
            by_book[book] = float(line)

    if not by_book:
        return {"line": None, "books": 0, "book_list": [], "dispersion": None}

    weighted_sum = 0.0
    total_weight = 0.0
    lines = []
    for book, line in by_book.items():
        weight = BOOK_WEIGHTS.get(book, 0.9)
        weighted_sum += line * weight
        total_weight += weight
        lines.append(line)

    consensus = weighted_sum / total_weight if total_weight > 0 else sum(lines) / len(lines)
    dispersion = (max(lines) - min(lines)) if len(lines) > 1 else 0.0
    return {
        "line": round(consensus, 2),
        "books": len(by_book),
        "book_list": sorted(by_book.keys()),
        "dispersion": round(dispersion, 2),
    }




def get_prop_value_from_stat(stat: Dict, prop_type: str) -> Optional[float]:
    """Extract prop value from a game stat record"""
    if prop_type == "points":
        return stat.get("points")
    elif prop_type == "rebounds":
        return stat.get("rebounds")
    elif prop_type == "assists":
        return stat.get("assists")
    elif prop_type == "pra":
        return (
            (stat.get("points") or 0) +
            (stat.get("rebounds") or 0) +
            (stat.get("assists") or 0)
        )
    elif prop_type == "threes":
        return stat.get("three_pointers_made")
    elif prop_type == "steals":
        return stat.get("steals")
    elif prop_type == "blocks":
        return stat.get("blocks")
    elif prop_type == "turnovers":
        return stat.get("turnovers")
    # Esports props (mapped to NBA stat fields)
    elif prop_type == "kills":
        # For esports, kills are stored in points field
        return stat.get("points")
    elif prop_type == "deaths":
        # For esports, deaths are stored in rebounds field
        return stat.get("rebounds")
    elif prop_type == "headshots":
        return stat.get("headshots")
    elif prop_type == "first_kills":
        return stat.get("first_kills")
    # NFL props
    elif prop_type == "pass_yds":
        return stat.get("passing_yards")
    elif prop_type == "rush_yds":
        return stat.get("rushing_yards")
    elif prop_type == "receptions":
        return stat.get("receptions")
    elif prop_type == "reception_yds":
        return stat.get("receiving_yards")
    elif prop_type == "pass_tds":
        return stat.get("passing_touchdowns")
    elif prop_type == "rush_tds":
        return stat.get("rushing_touchdowns")
    return None


def load_player_recent_stats(player_id: str, prop_type: str, games: int = 15) -> List[Dict]:
    """Load recent player game stats"""
    try:
        stats = (
            supabase.table("player_game_stats")
            .select("*")
            .eq("player_id", player_id)
            .order("date", desc=True)
            .limit(games)
            .execute()
            .data
        )
        return stats or []
    except Exception as e:
        # Silently fail - don't print to avoid spam
        return []


def load_matchup_stats(player_id: str, opponent_team: str, prop_type: str) -> List[Dict]:
    """Load player stats vs specific opponent team"""
    try:
        stats = (
            supabase.table("player_game_stats")
            .select("*")
            .eq("player_id", player_id)
            .eq("opponent", opponent_team)
            .order("date", desc=True)
            .limit(10)
            .execute()
            .data
        )
        return stats or []
    except Exception as e:
        # Silently fail - don't print to avoid spam
        return []


def load_home_away_stats(player_id: str, prop_type: str, home: bool) -> List[Dict]:
    """Load player stats for home or away games"""
    try:
        stats = (
            supabase.table("player_game_stats")
            .select("*")
            .eq("player_id", player_id)
            .eq("home", home)
            .order("date", desc=True)
            .limit(15)
            .execute()
            .data
        )
        return stats or []
    except Exception as e:
        # Silently fail - don't print to avoid spam
        return []


def calculate_weighted_average(stats: List[Dict], prop_type: str, recency_weight: float = 0.1) -> Optional[float]:
    """
    Calculate weighted average with more weight on recent games
    
    Args:
        stats: List of game stat records
        prop_type: Type of prop to calculate
        recency_weight: Weight multiplier for recent games (0.1 = 10% more weight per game back)
    
    Returns:
        Weighted average or None if no data
    """
    if not stats:
        return None
    
    total_weighted_value = 0
    total_weight = 0
    
    for i, stat in enumerate(stats):
        value = get_prop_value_from_stat(stat, prop_type)
        if value is not None:
            # More recent games get higher weight
            weight = 1.0 + (len(stats) - i) * recency_weight
            total_weighted_value += value * weight
            total_weight += weight
    
    if total_weight == 0:
        return None
    
    return total_weighted_value / total_weight


def calculate_opponent_adjustment(player_id: str, opponent_team: str, prop_type: str) -> float:
    """
    Calculate adjustment factor based on player's historical performance vs opponent
    
    Returns:
        Multiplier (1.0 = no adjustment, >1.0 = performs better, <1.0 = performs worse)
    """
    # Get overall average
    all_stats = load_player_recent_stats(player_id, prop_type, 20)
    overall_avg = calculate_weighted_average(all_stats, prop_type)
    
    if not overall_avg or overall_avg == 0:
        return 1.0
    
    # Get vs opponent average
    matchup_stats = load_matchup_stats(player_id, opponent_team, prop_type)
    matchup_avg = calculate_weighted_average(matchup_stats, prop_type)
    
    if not matchup_avg:
        return 1.0
    
    # Calculate adjustment factor
    adjustment = matchup_avg / overall_avg
    return adjustment


def calculate_home_away_adjustment(player_id: str, prop_type: str, is_home: bool) -> float:
    """
    Calculate adjustment based on home/away performance
    
    Returns:
        Multiplier for home/away adjustment
    """
    home_stats = load_home_away_stats(player_id, prop_type, home=True)
    away_stats = load_home_away_stats(player_id, prop_type, home=False)
    
    home_avg = calculate_weighted_average(home_stats, prop_type)
    away_avg = calculate_weighted_average(away_stats, prop_type)
    
    if not home_avg or not away_avg:
        return 1.0
    
    overall_avg = (home_avg + away_avg) / 2
    if overall_avg == 0:
        return 1.0
    
    # Return adjustment based on whether playing home or away
    if is_home:
        return home_avg / overall_avg
    else:
        return away_avg / overall_avg


def get_injury_status(player_id: str) -> Dict:
    """
    Get player injury status and impact
    
    Returns:
        Dict with 'status', 'severity', 'impact_multiplier'
    """
    try:
        # Check for active injuries
        injuries = (
            supabase.table("player_injuries")
            .select("*")
            .eq("player_id", player_id)
            .eq("status", "active")
            .order("reported_date", desc=True)
            .limit(1)
            .execute()
            .data
        )
        
        if not injuries:
            return {
                "status": "healthy",
                "severity": None,
                "impact_multiplier": 1.0
            }
        
        injury = injuries[0]
        severity = injury.get("severity", "").lower()
        impact_pct = injury.get("impact_percentage", 0) or 0
        
        # Map severity to impact if impact_percentage not set
        if impact_pct == 0:
            if severity == "out":
                impact_pct = 100  # 100% impact = can't play
            elif severity == "doubtful":
                impact_pct = 50  # 50% impact
            elif severity == "questionable":
                impact_pct = 25  # 25% impact
            elif severity == "probable":
                impact_pct = 10  # 10% impact
        
        # Convert impact percentage to multiplier (0% = 1.0, 100% = 0.0)
        impact_multiplier = 1.0 - (impact_pct / 100.0)
        impact_multiplier = max(0.0, min(1.0, impact_multiplier))  # Clamp between 0 and 1
        
        return {
            "status": severity or "injured",
            "severity": severity,
            "impact_multiplier": impact_multiplier,
            "injury_type": injury.get("injury_type"),
            "notes": injury.get("notes")
        }
    except:
        # If injuries table doesn't exist or error, return healthy
        return {
            "status": "healthy",
            "severity": None,
            "impact_multiplier": 1.0
        }


def get_bovada_line(player_id: str, game_id: str, prop_type: str) -> Optional[float]:
    """
    Get Bovada line for a specific prop to use as baseline
    
    Returns:
        Bovada line value or None if not found
    """
    try:
        props = (
            supabase.table("player_prop_odds")
            .select("line")
            .eq("player_id", player_id)
            .eq("game_id", game_id)
            .eq("prop_type", prop_type)
            .eq("book", "Bovada")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
        )
        
        if props and props[0].get("line") is not None:
            return props[0]["line"]
        return None
    except:
        return None


def calculate_opponent_defense_rating(opponent_team: str, prop_type: str) -> float:
    """
    Calculate opponent's defensive rating for a specific stat type.
    Currently disabled (returns 1.0) until dynamic league averages are implemented.
    """
    return 1.0


def get_player_rest_days(player_id: str, game_date: datetime) -> int:
    """
    Calculate days of rest before this game
    
    Returns:
        Number of rest days (0 = back-to-back, 1 = 1 day rest, etc.)
    """
    try:
        # Get player's last game
        last_game = (
            supabase.table("player_game_stats")
            .select("date")
            .eq("player_id", player_id)
            .lt("date", game_date.date() if isinstance(game_date, datetime) else game_date)
            .order("date", desc=True)
            .limit(1)
            .execute()
            .data
        )
        
        if not last_game:
            return 2  # Assume normal rest if no previous game
        
        last_game_date = last_game[0]["date"]
        if isinstance(last_game_date, str):
            last_game_date = datetime.fromisoformat(last_game_date).date()
        
        game_date_only = game_date.date() if isinstance(game_date, datetime) else game_date
        
        rest_days = (game_date_only - last_game_date).days
        return max(0, rest_days)
    except:
        return 2  # Default to normal rest


def calculate_rest_adjustment(rest_days: int) -> float:
    """
    Calculate adjustment based on rest days
    
    Returns:
        Multiplier for rest (more rest = slight boost, back-to-back = slight decrease)
    """
    if rest_days == 0:
        return 0.95  # Back-to-back: 5% decrease
    elif rest_days == 1:
        return 0.98  # 1 day rest: 2% decrease
    elif rest_days >= 3:
        return 1.02  # 3+ days rest: 2% increase
    else:
        return 1.0  # 2 days rest: neutral


def calculate_pace_adjustment(game_id: str, prop_type: str) -> float:
    """
    Calculate pace adjustment based on team pace
    
    Returns:
        Multiplier for pace (faster pace = higher multiplier)
    """
    # Currently a stub. In a full implementation, this would query team pace stats.
    return 1.0


def calculate_projection(
    player_id: str,
    prop_type: str,
    opponent_team: Optional[str] = None,
    is_home: bool = True,
    game_id: Optional[str] = None,
    bovada_line: Optional[float] = None
) -> Dict:
    """
    Calculate custom projection for a player prop
    
    Args:
        player_id: Player UUID
        prop_type: Type of prop (points, rebounds, etc.)
        opponent_team: Opponent team name
        is_home: Whether player is at home
        game_id: Game ID for additional context
    
    Returns:
        Dict with projection details:
        {
            "projected_line": float,
            "confidence": float (0-1),
            "factors": {
                "base_average": float,
                "recent_form": float,
                "matchup_adjustment": float,
                "home_away_adjustment": float,
                "injury_adjustment": float,
                "pace_adjustment": float
            },
            "sample_size": int
        }
        
    Returns empty dict on error to allow graceful degradation
    """
    try:
        # Get market consensus and Bovada line baselines
        market_consensus = {"line": None, "books": 0, "book_list": [], "dispersion": None}
        if game_id:
            market_consensus = get_market_consensus_line(player_id, game_id, prop_type)

        # Get Bovada line as baseline (if not provided, try to fetch it)
        if bovada_line is None and game_id:
            bovada_line = get_bovada_line(player_id, game_id, prop_type)
        
        # Load recent stats
        recent_stats = load_player_recent_stats(player_id, prop_type, 15)
        
        # Calculate player's recent/season averages
        player_avg = calculate_weighted_average(recent_stats, prop_type, recency_weight=0.15) if recent_stats else None
        season_stats = load_player_recent_stats(player_id, prop_type, 40)
        season_avg = calculate_weighted_average(season_stats, prop_type, recency_weight=0.03) if season_stats else None
        
        # Build blended projection from multiple legit sources.
        market_line = market_consensus.get("line")
        if market_line is not None and player_avg is not None and season_avg is not None:
            base_projection = (0.45 * player_avg) + (0.30 * season_avg) + (0.25 * float(market_line))
            baseline_source = "blended_recent_season_market"
        elif market_line is not None and player_avg is not None:
            base_projection = (0.65 * player_avg) + (0.35 * float(market_line))
            baseline_source = "blended_recent_market"
        elif player_avg is not None and season_avg is not None:
            base_projection = (0.70 * player_avg) + (0.30 * season_avg)
            baseline_source = "blended_recent_season"
        elif market_line is not None:
            base_projection = float(market_line)
            baseline_source = "market_consensus"
        elif bovada_line is not None:
            base_projection = float(bovada_line)
            baseline_source = "bovada"
        elif player_avg is not None:
            base_projection = float(player_avg)
            baseline_source = "recent_avg"
        else:
            return {
                "projected_line": None,
                "confidence": 0.0,
                "factors": {},
                "sample_size": 0
            }
        
        # Apply adjustments
        factors = {
            "baseline": base_projection,
            "baseline_source": baseline_source,
            "player_avg": player_avg or 0,
            "season_avg": season_avg or 0,
            "market_consensus_line": market_line,
            "market_books": market_consensus.get("books"),
            "market_book_list": market_consensus.get("book_list"),
            "market_dispersion": market_consensus.get("dispersion"),
            "defense_adjustment": 1.0,
            "matchup_adjustment": 1.0,
            "home_away_adjustment": 1.0,
            "injury_adjustment": 1.0,
            "rest_adjustment": 1.0,
            "pace_adjustment": 1.0
        }
        
        # Opponent defense adjustment (NEW)
        if opponent_team:
            defense_adj = calculate_opponent_defense_rating(opponent_team, prop_type)
            factors["defense_adjustment"] = defense_adj
            base_projection *= defense_adj
        
        # Matchup adjustment (player's historical performance vs this opponent)
        if opponent_team:
            matchup_adj = calculate_opponent_adjustment(player_id, opponent_team, prop_type)
            factors["matchup_adjustment"] = matchup_adj
            base_projection *= matchup_adj
        
        # Home/away adjustment
        home_away_adj = calculate_home_away_adjustment(player_id, prop_type, is_home)
        factors["home_away_adjustment"] = home_away_adj
        base_projection *= home_away_adj
        
        # Injury adjustment
        injury_status = get_injury_status(player_id)
        factors["injury_adjustment"] = injury_status["impact_multiplier"]
        base_projection *= injury_status["impact_multiplier"]
        
        # Rest days adjustment (NEW)
        if game_id:
            try:
                # Get game date
                game_resp = supabase.table("games").select("start_time").eq("id", game_id).limit(1).execute()
                if game_resp.data and game_resp.data[0].get("start_time"):
                    game_time = game_resp.data[0]["start_time"]
                    if isinstance(game_time, str):
                        game_time = datetime.fromisoformat(game_time.replace("Z", "+00:00"))
                    rest_days = get_player_rest_days(player_id, game_time)
                    rest_adj = calculate_rest_adjustment(rest_days)
                    factors["rest_adjustment"] = rest_adj
                    factors["rest_days"] = rest_days
                    base_projection *= rest_adj
            except:
                pass  # Skip if can't calculate rest
        
        # Pace adjustment
        if game_id:
            pace_adj = calculate_pace_adjustment(game_id, prop_type)
            factors["pace_adjustment"] = pace_adj
            base_projection *= pace_adj
        
        # Calculate confidence based on sample size and consistency
        sample_size = len(recent_stats)
        confidence = min(1.0, sample_size / 15.0)  # Max confidence at 15+ games
        if market_consensus.get("books", 0) >= 3:
            confidence = min(1.0, confidence + 0.08)
        if market_consensus.get("dispersion") is not None and market_consensus["dispersion"] > 3.5:
            confidence *= 0.9
        
        # Reduce confidence if stats are inconsistent (high variance)
        if sample_size >= 5:
            values = [get_prop_value_from_stat(s, prop_type) for s in recent_stats[:10]]
            values = [v for v in values if v is not None]
            if len(values) >= 3:
                avg = sum(values) / len(values)
                variance = sum((v - avg) ** 2 for v in values) / len(values)
                std_dev = variance ** 0.5
                if avg > 0:
                    cv = std_dev / avg  # Coefficient of variation
                    confidence *= max(0.5, 1.0 - cv * 0.5)  # Reduce confidence for high variance
        
        return {
            "projected_line": round(base_projection, 1),
            "confidence": round(confidence, 2),
            "factors": factors,
            "sample_size": sample_size,
            "injury_status": injury_status["status"],
            "baseline_source": baseline_source,
            "bovada_line": bovada_line,
            "market_consensus_line": market_line,
            "market_books": market_consensus.get("books"),
        }
    except Exception as e:
        # Gracefully handle errors - return empty dict so UI doesn't break
        # Don't print to avoid spam and performance issues
        return {
            "projected_line": None,
            "confidence": 0.0,
            "factors": {},
            "sample_size": 0
        }


def compare_projection_to_book_line(projection: float, book_line: float) -> Dict:
    """
    Compare our projection to book line
    
    Returns:
        Dict with comparison metrics
    """
    if not projection or not book_line:
        return {}
    
    difference = projection - book_line
    percent_diff = (difference / book_line * 100) if book_line != 0 else 0
    
    # Determine if our line is higher/lower
    if abs(difference) < 0.5:
        assessment = "aligned"
    elif difference > 0:
        assessment = "higher"  # We project higher than book
    else:
        assessment = "lower"  # We project lower than book
    
    return {
        "difference": round(difference, 1),
        "percent_difference": round(percent_diff, 1),
        "assessment": assessment,
        "value_opportunity": abs(difference) > 1.0  # Significant difference
    }

