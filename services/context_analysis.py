"""
Context-Aware Analysis Service
Calculates lineup impacts, teammate dependencies, and usage rate adjustments
"""
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from services.db import supabase
from datetime import datetime, timedelta


def get_active_injuries(team: str = None) -> List[Dict]:
    """
    Get active injuries, optionally filtered by team
    
    Returns:
        List of injury dicts with player info and impact
    """
    try:
        query = (
            supabase.table("player_injuries")
            .select("*, players(id, name, team, position)")
            .eq("status", "active")
        )
        
        result = query.execute()
        injuries = result.data or []
        
        # Filter by team if specified
        if team:
            injuries = [
                inj for inj in injuries
                if inj.get("players", {}).get("team") == team
            ]
        
        return injuries
    except Exception as e:
        print(f"Error fetching injuries: {e}")
        return []


def calculate_teammate_splits(player_id: str, teammate_id: str, prop_type: str, days_back: int = 180) -> Dict:
    """
    Calculate how player performs with vs without a specific teammate
    """
    try:
        cutoff_date = (datetime.now() - timedelta(days=days_back)).date().isoformat()
        
        # Get player's game stats
        stats = (
            supabase.table("player_game_stats")
            .select("*")
            .eq("player_id", player_id)
            .gte("date", cutoff_date)
            .execute()
            .data or []
        )
        
        # Get teammate's game dates (when they played)
        teammate_games = (
            supabase.table("player_game_stats")
            .select("date, game_id")
            .eq("player_id", teammate_id)
            .gte("date", cutoff_date)
            .gt("minutes_played", 0)  # Only games they actually played
            .execute()
            .data or []
        )
        
        teammate_game_dates = {g["date"] for g in teammate_games}
        
        # Split stats into with/without teammate
        with_stats = []
        without_stats = []
        
        for stat in stats:
            if stat.get("minutes_played", 0) == 0:
                continue  # Skip DNPs
            
            value = stat.get(prop_type, 0)
            if value is None:
                continue
            
            if stat["date"] in teammate_game_dates:
                with_stats.append(float(value))
            else:
                without_stats.append(float(value))
        
        # Calculate averages
        with_avg = sum(with_stats) / len(with_stats) if with_stats else 0
        without_avg = sum(without_stats) / len(without_stats) if without_stats else 0
        
        # Calculate impact percentage
        if with_avg > 0:
            impact_pct = ((without_avg - with_avg) / with_avg) * 100
        else:
            impact_pct = 0
        
        return {
            "with_teammate": {
                "avg": round(with_avg, 1),
                "games": len(with_stats),
                "values": with_stats
            },
            "without_teammate": {
                "avg": round(without_avg, 1),
                "games": len(without_stats),
                "values": without_stats
            },
            "impact_pct": round(impact_pct, 1),
            "sample_size_sufficient": len(with_stats) >= 3 and len(without_stats) >= 3
        }
    except Exception as e:
        print(f"Error calculating splits: {e}")
        return None


def identify_key_teammates(player_id: str, player_team: str) -> List[Dict]:
    """
    Identify key teammates who significantly impact a player's performance
    """
    try:
        # Get all teammates on the same team
        teammates = (
            supabase.table("players")
            .select("id, name, position")
            .eq("team", player_team)
            .neq("id", player_id)
            .execute()
            .data or []
        )
        
        impacts = []
        
        # Analyze key prop types
        for prop_type in ["points", "assists", "rebounds"]:
            for teammate in teammates:
                split = calculate_teammate_splits(player_id, teammate["id"], prop_type)
                
                if split and split["sample_size_sufficient"]:
                    # Only include if impact is significant (> 10%)
                    if abs(split["impact_pct"]) > 10:
                        impacts.append({
                            "teammate_id": teammate["id"],
                            "teammate_name": teammate["name"],
                            "teammate_position": teammate["position"],
                            "prop_type": prop_type,
                            "impact_pct": split["impact_pct"],
                            "with_avg": split["with_teammate"]["avg"],
                            "without_avg": split["without_teammate"]["avg"],
                            "sample_with": split["with_teammate"]["games"],
                            "sample_without": split["without_teammate"]["games"]
                        })
        
        # Sort by impact magnitude
        impacts.sort(key=lambda x: abs(x["impact_pct"]), reverse=True)
        
        return impacts
    except Exception as e:
        print(f"Error identifying key teammates: {e}")
        return []


def predict_usage_adjustment(player_id: str, prop_type: str, injured_teammates: List[Dict]) -> Dict:
    """
    Predict how much a player's usage will increase when teammates are injured
    """
    try:
        # Get player's recent baseline (last 10 games with full squad)
        recent_stats = (
            supabase.table("player_game_stats")
            .select(f"date, {prop_type}")
            .eq("player_id", player_id)
            .gt("minutes_played", 0)
            .order("date", desc=True)
            .limit(10)
            .execute()
            .data or []
        )
        
        if not recent_stats:
            return None
        
        baseline_values = [s[prop_type] for s in recent_stats if s.get(prop_type) is not None]
        baseline_avg = sum(baseline_values) / len(baseline_values) if baseline_values else 0
        
        # Calculate adjustment based on injured teammates
        total_adjustment = 0
        reasons = []
        
        for injured in injured_teammates:
            teammate_id = injured.get("players", {}).get("id")
            if not teammate_id:
                continue
            
            # Check if this teammate significantly impacts the player
            split = calculate_teammate_splits(player_id, teammate_id, prop_type)
            
            if split and split["sample_size_sufficient"]:
                # If player performs BETTER without teammate, add positive adjustment
                adjustment = split["impact_pct"]
                if abs(adjustment) > 5:  # Only meaningful adjustments
                    total_adjustment += adjustment
                    teammate_name = injured.get("players", {}).get("name", "Teammate")
                    reasons.append(
                        f"{teammate_name} OUT: {'+' if adjustment > 0 else ''}{adjustment:.0f}% impact"
                    )
        
        adjusted_avg = baseline_avg * (1 + total_adjustment / 100)
        
        # Determine confidence based on sample size and adjustment magnitude
        if total_adjustment == 0:
            confidence = "low"
            reasoning = "No significant historical impact from injuries"
        elif abs(total_adjustment) < 15:
            confidence = "medium"
            reasoning = "; ".join(reasons)
        else:
            confidence = "high"
            reasoning = "; ".join(reasons)
        
        return {
            "baseline_avg": round(baseline_avg, 1),
            "adjusted_avg": round(adjusted_avg, 1),
            "adjustment_pct": round(total_adjustment, 1),
            "confidence": confidence,
            "reasoning": reasoning
        }
    except Exception as e:
        print(f"Error predicting usage: {e}")
        return None


def get_matchup_history(player_id: str, opponent_team: str) -> List[Dict]:
    """
    Get player's history against a specific opponent
    """
    try:
        stats = (
            supabase.table("player_game_stats")
            .select("*")
            .eq("player_id", player_id)
            .eq("opponent", opponent_team)
            .order("date", desc=True)
            .execute()
            .data or []
        )
        return stats
    except Exception as e:
        print(f"Error fetching matchup history: {e}")
        return []

def get_home_away_splits(player_id: str, prop_type: str) -> Dict:
    """
    Calculate Home vs Away splits for a player
    """
    try:
        stats = (
            supabase.table("player_game_stats")
            .select(f"*, {prop_type}")
            .eq("player_id", player_id)
            .gt("minutes_played", 0)
            .order("date", desc=True)
            .limit(50) # Last 50 games
            .execute()
            .data or []
        )
        
        home_vals = [s[prop_type] for s in stats if s.get("home") and s.get(prop_type) is not None]
        away_vals = [s[prop_type] for s in stats if not s.get("home") and s.get(prop_type) is not None]
        
        home_avg = sum(home_vals) / len(home_vals) if home_vals else 0
        away_avg = sum(away_vals) / len(away_vals) if away_vals else 0
        
        return {
            "home": {"avg": round(home_avg, 1), "games": len(home_vals)},
            "away": {"avg": round(away_avg, 1), "games": len(away_vals)}
        }
    except Exception as e:
        print(f"Error calculating splits: {e}")
        return {"home": {"avg": 0, "games": 0}, "away": {"avg": 0, "games": 0}}

def get_game_context(player_id: str, game_id: str, prop_type: str, line: float = None) -> Dict:
    """
    Get complete context for a player in a specific game
    """
    try:
        # Get player info
        player = (
            supabase.table("players")
            .select("id, name, team, position")
            .eq("id", player_id)
            .execute()
            .data
        )
        
        if not player:
            return None
        
        player_obj = player[0]
        player_team = player_obj["team"]
        player_pos = player_obj.get("position", "N/A")
        
        # Get game info to find opponent and check spread
        game = (
            supabase.table("games")
            .select("home_team, away_team, sport")
            .eq("id", game_id)
            .single()
            .execute()
            .data
        )
        
        opponent = None
        if game:
            # Use normalize_team_name for proper team matching
            from utils.team_mapping import normalize_team_name
            player_team_norm = normalize_team_name(player_team)
            home_team_norm = normalize_team_name(game["home_team"])
            away_team_norm = normalize_team_name(game["away_team"])
            
            if player_team_norm == home_team_norm or player_team == game["home_team"]:
                opponent = game["away_team"]
            elif player_team_norm == away_team_norm or player_team == game["away_team"]:
                opponent = game["home_team"]
            else:
                # Fallback to original logic
                opponent = game["away_team"] if game["home_team"] == player_team else game["home_team"]
        
        # Get team injuries
        injuries = get_active_injuries(player_team)
        
        # Exclude the player themselves if injured
        teammate_injuries = [
            inj for inj in injuries
            if inj.get("players", {}).get("id") != player_id
        ]
        
        # Predict usage adjustment
        usage_pred = predict_usage_adjustment(player_id, prop_type, teammate_injuries)
        
        # Get key teammate impacts
        key_impacts = identify_key_teammates(player_id, player_team)
        
        # Get Matchup History
        matchup_history = []
        if opponent:
            matchup_history = get_matchup_history(player_id, opponent)
            
        # Get Splits
        splits = get_home_away_splits(player_id, prop_type)
        
        # Build context summary
        summary_parts = []
        
        if teammate_injuries:
            out_players = [
                inj.get("players", {}).get("name")
                for inj in teammate_injuries
                if inj.get("severity") == "out"
            ]
            if out_players:
                summary_parts.append(f"🚨 OUT: {', '.join(out_players)}")
        
        if usage_pred and usage_pred["adjustment_pct"] != 0:
            direction = "increase" if usage_pred["adjustment_pct"] > 0 else "decrease"
            summary_parts.append(
                f"📈 Projected {abs(usage_pred['adjustment_pct']):.0f}% {direction} "
                f"({usage_pred['baseline_avg']:.1f} → {usage_pred['adjusted_avg']:.1f})"
            )
            
        # Add matchup context
        if matchup_history:
            matchup_avg = sum(g.get(prop_type, 0) for g in matchup_history) / len(matchup_history)
            summary_parts.append(f"🆚 Avg vs {opponent}: {matchup_avg:.1f} ({len(matchup_history)} gms)")
            
        # --- NEW: Line Inflation & Injury Return ---
        line_context = None
        if line is not None:
            # Get L20 avg for context
            l20_stats = (
                supabase.table("player_game_stats")
                .select(prop_type)
                .eq("player_id", player_id)
                .order("date", desc=True)
                .limit(20)
                .execute()
                .data or []
            )
            vals = [s[prop_type] for s in l20_stats if s.get(prop_type) is not None]
            if vals:
                avg = sum(vals) / len(vals)
                # Threshold: 20% deviation
                if line > avg * 1.2:
                    line_context = f"⚠️ Line inflated: {line} (Avg: {avg:.1f})"
                    summary_parts.append(line_context)
                elif line < avg * 0.8:
                    line_context = f"✅ Line discounted: {line} (Avg: {avg:.1f})"
                    summary_parts.append(line_context)

        # Injury Return Check (Gap > 10 days)
        last_game = (
            supabase.table("player_game_stats")
            .select("date")
            .eq("player_id", player_id)
            .order("date", desc=True)
            .limit(1)
            .execute()
            .data
        )
        if last_game:
            try:
                last_date_str = last_game[0]["date"]
                # Simple string compare or proper parse
                last_dt = datetime.fromisoformat(last_date_str.replace('Z', '+00:00'))
                days_since = (datetime.now(last_dt.tzinfo) - last_dt).days
                if days_since > 10:
                    summary_parts.append(f"🚑 Returning from {days_since} days rest")
            except:
                pass
        
        # Blowout Potential Check (for NBA only, when spread is high)
        blowout_context = None
        if game and game.get("sport") == "NBA":
            # Get spread from odds_snapshots
            spread_odds = (
                supabase.table("odds_snapshots")
                .select("line, market_label")
                .eq("game_id", game_id)
                .eq("market_type", "spreads")
                .order("created_at", desc=True)
                .limit(10)
                .execute()
                .data or []
            )
            
            if spread_odds:
                # Find the spread for the player's team
                player_is_home = player_team_norm == home_team_norm or player_team == game["home_team"]
                team_spread = None
                
                for spread_odd in spread_odds:
                    market_label = spread_odd.get("market_label", "")
                    if (player_is_home and market_label == game["home_team"]) or \
                       (not player_is_home and market_label == game["away_team"]):
                        team_spread = spread_odd.get("line")
                        break
                
                # If no direct match, use the first spread (usually home team)
                if team_spread is None and spread_odds:
                    team_spread = spread_odds[0].get("line")
                
                if team_spread is not None:
                    abs_spread = abs(float(team_spread))
                    # High spread threshold: 15+ points indicates potential blowout
                    if abs_spread >= 15:
                        # In blowouts, favorites may play fewer minutes, underdogs may play more
                        is_favorite = (player_is_home and team_spread < 0) or (not player_is_home and team_spread > 0)
                        
                        if is_favorite:
                            blowout_context = f"⚠️ High spread ({abs_spread:.1f}): Favorites may rest in 4th quarter"
                            summary_parts.append(blowout_context)
                        else:
                            blowout_context = f"📊 High spread ({abs_spread:.1f}): Underdog may see extended minutes"
                            summary_parts.append(blowout_context)
        
        # Placeholder for Defense vs Position (needs rich dataset)
        # We can heuristically check if opponent allows high points to this position
        # For now, we skip to avoid inaccuracy without full data.
        
        context_summary = " | ".join(summary_parts) if summary_parts else "No significant context"
        
        return {
            "injuries": teammate_injuries,
            "usage_prediction": usage_pred,
            "key_impacts": key_impacts,
            "context_summary": context_summary,
            "matchup_history": matchup_history,
            "splits": splits,
            "line_context": line_context
        }
    except Exception as e:
        print(f"Error getting game context: {e}")
        return None
