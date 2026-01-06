"""
Prop Insights Component - Detailed analysis for each prop
"""
import streamlit as st
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from services.db import supabase
from services.projections import calculate_projection
from services.projections import get_prop_value_from_stat
from services.context_analysis import get_game_context
from dashboard.ui_components import render_metric_card


def calculate_historical_hit_rate(player_id: str, prop_type: str, line: float, games_limit: int = 50) -> Dict:
    """
    Calculate historical hit rate for over/under a specific line
    
    Returns:
        {
            "total_games": int,
            "over_count": int,
            "under_count": int,
            "over_pct": float,
            "under_pct": float,
            "push_count": int,
            "avg_value": float,
            "recent_games": List[Dict]  # Last 10 games with over/under result
        }
    """
    try:
        # Get player's recent game stats
        # IMPORTANT: Order by date DESC to get most recent first
        # We filter out games with no minutes in the processing loop for better control
        try:
            stats = (
                supabase.table("player_game_stats")
                .select("*")
                .eq("player_id", player_id)
                .order("date", desc=True)  # Most recent first - CRITICAL
                .limit(games_limit * 2)  # Get more to account for filtering
                .execute()
                .data
            )
        except Exception as e:
            print(f"Error fetching stats for player {player_id}: {e}")
            stats = []
        
        # Additional validation: ensure dates are valid and stats are recent
        # Filter out any stats with invalid dates or very old dates
        valid_stats = []
        cutoff_date = datetime.now().date() - timedelta(days=730)  # Last 2 years (more lenient)
        
        for stat in stats:
            stat_date = stat.get("date")
            if stat_date:
                # Parse date if it's a string
                if isinstance(stat_date, str):
                    try:
                        # Handle different date formats
                        if 'T' in stat_date:
                            stat_date = datetime.fromisoformat(stat_date.split('T')[0]).date()
                        else:
                            stat_date = datetime.fromisoformat(stat_date).date()
                    except:
                        # Try alternative parsing
                        try:
                            stat_date = datetime.strptime(stat_date, "%Y-%m-%d").date()
                        except:
                            continue
                elif hasattr(stat_date, 'date'):
                    stat_date = stat_date.date()
                
                # Only include recent stats (within last 2 years)
                # Don't filter by opponent here - include all valid stats
                if stat_date and stat_date >= cutoff_date:
                    valid_stats.append(stat)
        
        stats = valid_stats
        
        if not stats:
            return {
                "total_games": 0,
                "over_count": 0,
                "under_count": 0,
                "over_pct": 0.0,
                "under_pct": 0.0,
                "push_count": 0,
                "avg_value": 0.0,
                "recent_games": []
            }
        
        # Count all games first (for accurate totals)
        all_over = 0
        all_under = 0
        all_push = 0
        total_value = 0.0
        valid_games = 0
        recent_games = []
        
        # Process all stats to get accurate counts
        for stat in stats:
            # First, validate the stat record
            minutes = stat.get("minutes_played")
            if minutes is None:
                continue  # Skip if no minutes data
            
            # Convert to float/int for comparison
            try:
                minutes = float(minutes) if minutes else 0
            except:
                minutes = 0
            
            # Skip games where player didn't play (0 minutes = DNP)
            if minutes == 0:
                continue
            
            # Get prop value
            value = get_prop_value_from_stat(stat, prop_type)
            if value is None:
                continue  # Skip if we can't get the prop value
            
            # Validate line
            if line is None or line == 0:
                continue  # Can't calculate hit rate without a valid line
            
            total_value += value
            valid_games += 1
            
            # Compare to line (strict comparison - 3.5 means > 3.5 for over, < 3.5 for under)
            if value > line:
                all_over += 1
                result = "OVER"
            elif value < line:
                all_under += 1
                result = "UNDER"
            else:
                # Exact match (push)
                all_push += 1
                result = "PUSH"
            
            # Add to recent games (last 10, most recent first)
            # Format date for display
            stat_date = stat.get("date")
            if isinstance(stat_date, str):
                try:
                    # Parse and format date
                    if 'T' in stat_date:
                        date_obj = datetime.fromisoformat(stat_date.split('T')[0]).date()
                    else:
                        date_obj = datetime.fromisoformat(stat_date).date()
                    formatted_date = date_obj.strftime("%m/%d/%Y")
                except:
                    try:
                        formatted_date = datetime.strptime(stat_date, "%Y-%m-%d").strftime("%m/%d/%Y")
                    except:
                        formatted_date = stat_date
            else:
                formatted_date = stat_date.strftime("%m/%d/%Y") if hasattr(stat_date, 'strftime') else str(stat_date)
            
            # Get opponent - ensure it's not None or empty
            # Try to get from game if opponent is missing
            opponent = stat.get("opponent")
            if not opponent or opponent == "" or opponent is None:
                # Try to get opponent from game_id if available
                game_id = stat.get("game_id")
                if game_id:
                    try:
                        game = supabase.table("games").select("home_team,away_team").eq("id", game_id).limit(1).execute().data
                        if game:
                            # Determine opponent based on player's team (if we have it)
                            # For now, just use the other team
                            opponent = game[0].get("away_team") or game[0].get("home_team") or "N/A"
                    except:
                        opponent = "N/A"
                else:
                    opponent = "N/A"
            
            # Clean up opponent (remove extra spaces, etc.)
            if opponent and isinstance(opponent, str):
                opponent = opponent.strip()
            
            # Only add to recent games if we have valid data
            if len(recent_games) < 10 and opponent and opponent != "N/A":
                recent_games.append({
                    "date": formatted_date,
                    "opponent": opponent,
                    "value": value,
                    "result": result,
                    "home": stat.get("home", True)
                })
        
        # Calculate percentages based on all games
        total_games = all_over + all_under + all_push
        
        # Safety check: ensure we have valid data
        if total_games == 0:
            return {
                "total_games": 0,
                "over_count": 0,
                "under_count": 0,
                "over_pct": 0.0,
                "under_pct": 0.0,
                "push_count": 0,
                "avg_value": 0.0,
                "recent_games": []
            }
        
        # Calculate percentages (only once, correctly)
        over_pct = (all_over / total_games * 100)
        under_pct = (all_under / total_games * 100)
        push_pct = (all_push / total_games * 100)
        avg_value = total_value / valid_games if valid_games > 0 else 0.0
        
        # Reverse recent_games to show chronological order (oldest to newest)
        recent_games.reverse()
        
        # Debug: Log if percentages don't add up to ~100% (allowing for rounding)
        total_pct = over_pct + under_pct + push_pct
        if abs(total_pct - 100.0) > 1.0:  # More than 1% off
            print(f"Warning: Hit rate percentages don't add up correctly. Over: {over_pct:.1f}%, Under: {under_pct:.1f}%, Push: {push_pct:.1f}%, Total: {total_pct:.1f}%")
        
        return {
            "total_games": total_games,
            "over_count": all_over,
            "under_count": all_under,
            "over_pct": round(over_pct, 1),
            "under_pct": round(under_pct, 1),
            "push_count": all_push,
            "push_pct": round(push_pct, 1),
            "avg_value": round(avg_value, 1),
            "recent_games": recent_games
        }
    except Exception as e:
        # Log error for debugging (but don't spam)
        import traceback
        print(f"Error calculating hit rate for player {player_id}: {e}")
        # Uncomment for detailed debugging:
        # traceback.print_exc()
        return {
            "total_games": 0,
            "over_count": 0,
            "under_count": 0,
            "over_pct": 0.0,
            "under_pct": 0.0,
            "push_count": 0,
            "avg_value": 0.0,
            "recent_games": []
        }


def render_prop_insights(
    prop: Dict,
    player_info: Dict,
    game_info: Dict,
    edge_data: Optional[Dict] = None,
    projection_data: Optional[Dict] = None
):
    """
    Render detailed insights for a prop in an expander
    """
    player_id = prop.get("player_id")
    prop_type = prop.get("prop_type", "")
    line = prop.get("line")
    
    # Get player name - handle both dict and direct access
    # Decode HTML entities for proper display
    from dashboard.ui_components import decode_html_entities
    if isinstance(player_info, dict):
        player_name_raw = player_info.get("name", "Unknown Player")
        player_name = decode_html_entities(player_name_raw)
    else:
        player_name_raw = str(player_info) if player_info else "Unknown Player"
        player_name = decode_html_entities(player_name_raw)
    
    # Validate inputs
    if not player_id:
        # Try to get from player_info if it's a dict with id
        if isinstance(player_info, dict) and player_info.get("id"):
            player_id = player_info.get("id")
        else:
            # Can't calculate insights without player_id
            return
    
    # Format prop type
    if prop_type == "pra":
        prop_type_display = "PRA"
    elif prop_type == "threes":
        prop_type_display = "3PM"
    else:
        prop_type_display = prop_type.replace("_", " ").title()
    
    # Calculate historical hit rate
    # Validate inputs first
    if not player_id:
        st.warning("⚠️ No player ID available for insights")
        hit_rate = None
    elif not line or line == 0:
        st.warning("⚠️ Invalid line value for insights")
        hit_rate = None
    else:
        # Always calculate - the function handles empty results gracefully
        hit_rate = calculate_historical_hit_rate(player_id, prop_type, line)
        
        # Debug: Check if we have stats for this player
        if hit_rate and hit_rate.get("total_games", 0) == 0:
            # Try to see if player has any stats at all
            try:
                test_stats = supabase.table("player_game_stats").select("id").eq("player_id", player_id).limit(1).execute().data
                if not test_stats:
                    st.caption(f"💡 Tip: No stats found for {player_name}. Run `python workers/fetch_player_stats.py` to sync player stats.")
            except:
                pass
    
    # Determine recommended side (with threshold to avoid noise)
    recommended_side = None
    if hit_rate and hit_rate["total_games"] > 0:
        over_pct = hit_rate.get("over_pct", 0)
        under_pct = hit_rate.get("under_pct", 0)
        # Only recommend if there's a meaningful difference (at least 5%)
        if over_pct > under_pct + 5:
            recommended_side = "OVER"
        elif under_pct > over_pct + 5:
            recommended_side = "UNDER"
    
    # Create expander
    with st.expander(f"📊 ANALYSIS: {player_name} {prop_type_display} {line}", expanded=False):
        
        # Game Context Analysis (NEW!)
        game_id = prop.get("game_id")
        if game_id:
            context = get_game_context(player_id, game_id, prop_type)
            
            if context and context.get("context_summary") != "No significant context":
                st.markdown("#### 🎯 Today's Context")
                
                # Show context summary
                st.info(context["context_summary"])
                
                # Show usage prediction details
                usage_pred = context.get("usage_prediction")
                if usage_pred and usage_pred.get("adjustment_pct", 0) != 0:
                    with st.expander("📊 Usage Rate Analysis", expanded=False):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            render_metric_card("Historical Avg", f"{usage_pred['baseline_avg']:.1f}")
                        with col2:
                            render_metric_card(
                                "Adjusted Projection",
                                f"{usage_pred['adjusted_avg']:.1f}",
                                delta=f"{usage_pred['adjustment_pct']:+.1f}%"
                            )
                        with col3:
                            confidence_emoji = {"high": "🟢", "medium": "🟡", "low": "⚪"}
                            render_metric_card("Confidence", f"{confidence_emoji.get(usage_pred['confidence'], '⚪')} {usage_pred['confidence'].upper()}")
                        
                        if usage_pred.get("reasoning"):
                            st.caption(f"**Analysis:** {usage_pred['reasoning']}")
                
                st.markdown("---")
        
        # Historical Performance
        if hit_rate and hit_rate["total_games"] > 0:
            # Extract and validate values
            total_games = hit_rate.get("total_games", 0)
            over_count = hit_rate.get("over_count", 0)
            under_count = hit_rate.get("under_count", 0)
            push_count = hit_rate.get("push_count", 0)
            avg_value = hit_rate.get("avg_value", 0)
            
            # Recalculate percentages to ensure accuracy
            if total_games > 0:
                over_pct = round((over_count / total_games) * 100, 1)
                under_pct = round((under_count / total_games) * 100, 1)
                push_pct = round((push_count / total_games) * 100, 1)
            else:
                over_pct = 0.0
                under_pct = 0.0
                push_pct = 0.0
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                render_metric_card("Total Games", total_games)
            
            with col2:
                over_color = "success" if over_pct > under_pct else "neutral"
                render_metric_card("Over Hit Rate", f"{over_pct:.1f}%", delta=f"{over_count} games", color=over_color)
            
            with col3:
                under_color = "success" if under_pct > over_pct else "neutral"
                render_metric_card("Under Hit Rate", f"{under_pct:.1f}%", delta=f"{under_count} games", color=under_color)
            
            # Check for unusual line deviation and explain it with context
            line_deviation_warning = False
            context_explains_deviation = False
            
            if avg_value and line:
                deviation_pct = abs((line - avg_value) / avg_value) * 100 if avg_value != 0 else 0
                
                # Check if we have context that explains the deviation
                if game_id and deviation_pct > 15:
                    context = get_game_context(player_id, game_id, prop_type)
                    usage_pred = context.get("usage_prediction") if context else None
                    
                    if usage_pred and abs(usage_pred.get("adjustment_pct", 0)) > 10:
                        # Context explains the line deviation!
                        context_explains_deviation = True
                        adjusted_proj = usage_pred["adjusted_avg"]
                        
                        st.info(
                            f"📊 **Line Context Explained**: Book line ({line:.1f}) differs from historical avg ({avg_value:.1f}) "
                            f"by {deviation_pct:.0f}%. Our context-aware projection: **{adjusted_proj:.1f}**"
                        )
                        st.caption(f"💡 {usage_pred.get('reasoning', 'See usage analysis above for details')}")
                    else:
                        # Deviation not explained by our context analysis
                        line_deviation_warning = True
                        st.warning(
                            f"⚠️ **Line Alert**: Book line ({line:.1f}) is {deviation_pct:.0f}% "
                            f"{'higher' if line > avg_value else 'lower'} than historical avg ({avg_value:.1f}). "
                            f"**Unable to explain with injury/lineup data.** May be matchup, minutes restriction, or other factors."
                        )
            
            # Context-Aware Recommendation
            if recommended_side:
                hit_pct = over_pct if recommended_side == "OVER" else under_pct
                hit_count = over_count if recommended_side == "OVER" else under_count
                miss_count = under_count if recommended_side == "OVER" else over_count
                
                # Check if context changes the recommendation
                if game_id and context_explains_deviation:
                    usage_pred = get_game_context(player_id, game_id, prop_type).get("usage_prediction")
                    if usage_pred:
                        adjusted_proj = usage_pred["adjusted_avg"]
                        
                        # Compare adjusted projection to line
                        context_side = "OVER" if adjusted_proj > line else "UNDER"
                        
                        if context_side != recommended_side:
                            # Context suggests different side!
                            st.warning(
                                f"⚠️ **Context Override**: Historical data suggests {recommended_side} ({hit_pct:.1f}%), "
                                f"BUT context analysis suggests **{context_side}** (Adjusted: {adjusted_proj:.1f} vs Line: {line:.1f})"
                            )
                            st.caption(f"📊 Historical: {hit_count} {recommended_side} out of {total_games} games")
                        else:
                            # Context confirms historical recommendation
                            st.success(
                                f"✅ **Strong {recommended_side}**: Both historical ({hit_pct:.1f}%) and context analysis "
                                f"(Adjusted: {adjusted_proj:.1f}) agree"
                            )
                            st.caption(f"📊 Breakdown: {hit_count} {recommended_side} | {miss_count} {('UNDER' if recommended_side == 'OVER' else 'OVER')} | {push_count} Push")
                else:
                    # Standard historical recommendation
                    st.success(f"✅ **Recommended: {recommended_side}** - {recommended_side} has hit **{hit_count} out of {total_games} games** ({hit_pct:.1f}%)")
                    st.caption(f"📊 Breakdown: {hit_count} {recommended_side} | {miss_count} {('UNDER' if recommended_side == 'OVER' else 'OVER')} | {push_count} Push")
                    
                    # Warn if there's unexplained deviation
                    if line_deviation_warning:
                        st.caption("⚠️ **Note**: Line significantly differs from history but we couldn't identify the cause. Proceed with caution.")
            else:
                st.info("⚖️ **Even Split** - Over and Under have similar hit rates")
                st.caption(f"📊 Breakdown: {over_count} Over ({over_pct:.1f}%) | {under_count} Under ({under_pct:.1f}%) | {push_count} Push ({push_pct:.1f}%)")
            
            # Average value
            render_metric_card("Average Performance", f"{avg_value:.1f}", delta=f"vs Line: {line:.1f}")
            
            # Recent Games Table
            if hit_rate["recent_games"]:
                st.markdown("#### Recent Games vs This Line")
                recent_data = []
                for game in hit_rate["recent_games"]:
                    value = game.get('value', 0)
                    result_emoji = "✅" if game.get("result") == "OVER" else ("❌" if game.get("result") == "UNDER" else "➖")
                    # Show value vs line comparison
                    comparison_text = f"{value:.1f} vs {line:.1f}"
                    recent_data.append({
                        "Date": game.get("date", "N/A"),
                        "Opponent": game.get("opponent", "N/A"),
                        "Value": f"{value:.1f}",
                        f"vs Line ({line:.1f})": comparison_text,
                        "Result": f"{result_emoji} {game.get('result', 'N/A')}",
                        "Home/Away": "🏠 Home" if game.get("home", True) else "✈️ Away"
                    })
                if recent_data:
                    st.dataframe(recent_data, use_container_width=True, hide_index=True)
                else:
                    st.info("No recent games data available")
        else:
            st.warning("⚠️ No historical data available for this player/prop type")
        
        # Our Projections
        st.markdown("---")
        st.markdown("#### 🎯 Our Projections")
        
        if projection_data and projection_data.get("projected_line") is not None:
            proj_line = projection_data.get("projected_line")
            baseline_source = projection_data.get("baseline_source", "unknown")
            confidence = projection_data.get("confidence", 0) * 100
            factors = projection_data.get("factors", {})
            
            col1, col2 = st.columns(2)
            
            with col1:
                render_metric_card("Projected Line", f"{proj_line:.1f}", delta=f"vs Book: {line}")
            
            with col2:
                render_metric_card("Confidence", f"{confidence:.0f}%", delta=f"Baseline: {baseline_source.title()}")
            
            # Projection factors
            if factors:
                st.markdown("**Adjustment Factors:**")
                factor_cols = st.columns(4)
                
                with factor_cols[0]:
                    st.caption(f"Defense: {factors.get('defense_adjustment', 1.0):.2f}x")
                with factor_cols[1]:
                    st.caption(f"Matchup: {factors.get('matchup_adjustment', 1.0):.2f}x")
                with factor_cols[2]:
                    st.caption(f"Home/Away: {factors.get('home_away_adjustment', 1.0):.2f}x")
                with factor_cols[3]:
                    st.caption(f"Injury: {factors.get('injury_adjustment', 1.0):.2f}x")
            
            # Comparison to book line
            comparison = projection_data.get("comparison", {})
            if comparison:
                diff = comparison.get("difference", 0)
                pct_diff = comparison.get("percent_difference", 0)
                
                if diff > 0:
                    st.success(f"📈 Our projection is **{diff:+.1f}** ({pct_diff:+.1f}%) higher than the book line")
                elif diff < 0:
                    st.warning(f"📉 Our projection is **{diff:.1f}** ({pct_diff:.1f}%) lower than the book line")
                else:
                    st.info("🎯 Our projection matches the book line")
        else:
            st.info("💡 Projections not available. Enable 'Show Our Projections' in the sidebar.")
        
        # Edge Analysis
        if edge_data:
            st.markdown("---")
            st.markdown("#### 💰 Expected Value Analysis")
            
            edge = edge_data.get("edge", 0) * 100
            prob = edge_data.get("prob", 0) * 100
            side = edge_data.get("side", "over").upper()
            odds = edge_data.get("odds", 0)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                edge_color = "success" if edge > 0 else "danger"
                render_metric_card("Expected Value", f"{edge:+.1f}%", delta=f"{side} recommended", color=edge_color)
            
            with col2:
                render_metric_card("Win Probability", f"{prob:.1f}%")
            
            with col3:
                render_metric_card("Odds", f"{odds:+d}")
            
            if edge > 0:
                st.success(f"✅ **+EV Play** - {side} has {prob:.1f}% win probability with {edge:+.1f}% expected value")
            else:
                st.warning(f"⚠️ **Negative EV** - This bet has a negative expected value")
        
        # Game Context
        st.markdown("---")
        st.markdown("#### 🏀 Game Context")
        
        if isinstance(game_info, dict):
            home_team = game_info.get("home_team", "N/A")
            away_team = game_info.get("away_team", "N/A")
            start_time = game_info.get("start_time")
            
            # Get player team - ensure it's correct
            player_team = player_info.get("team", "N/A") if isinstance(player_info, dict) else "N/A"
            
            # If team is missing or wrong, try to fetch from database
            if player_id and (not player_team or player_team == "WAS" or player_team == "N/A"):
                try:
                    player_resp = supabase.table("players").select("team").eq("id", player_id).limit(1).execute()
                    if player_resp.data and player_resp.data[0].get("team"):
                        player_team = player_resp.data[0]["team"]
                except:
                    pass
            
            is_home = player_team == home_team if player_team != "N/A" else False
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Matchup:** {away_team} @ {home_team}")
                st.write(f"**Player Team:** {player_team} ({'🏠 Home' if is_home else '✈️ Away'})")
            
            with col2:
                if start_time:
                    from dashboard.ui_components import format_game_time
                    st.write(f"**Game Time:** {format_game_time(start_time)}")
                
                # Rest days if available
                if projection_data:
                    factors = projection_data.get("factors", {})
                    rest_days = factors.get("rest_days")
                    if rest_days is not None:
                        if rest_days == 0:
                            st.write("**Rest:** 🔁 Back-to-Back")
                        elif rest_days >= 3:
                            st.write(f"**Rest:** 💤 {rest_days} days")
                        else:
                            st.write(f"**Rest:** {rest_days} days")
