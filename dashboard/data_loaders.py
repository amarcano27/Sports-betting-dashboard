"""
Shared data loading functions for the dashboard
"""
import streamlit as st
from datetime import datetime, timedelta, timezone
try:
    from services.db import supabase
    DB_AVAILABLE = True
except Exception as e:
    DB_AVAILABLE = False
    print(f"Database unavailable: {e}")

# Import demo data loader as fallback
from dashboard.demo_data_loader import get_demo_games, get_demo_props, get_demo_players

ESPORTS_SUB_SPORTS = ["CS2", "LoL", "Dota2", "Valorant"]

@st.cache_data(ttl=3600)
def load_all_players(sport):
    """Load all players for search"""
    if not DB_AVAILABLE:
        # Use demo data
        return get_demo_players(sport)
    
    try:
        query = supabase.table("players").select("*")
        if sport == "Esports":
            query = query.in_("sport", ESPORTS_SUB_SPORTS)
        else:
            query = query.eq("sport", sport)
            
        players = (
            query.order("name")
            .execute()
            .data
        )
        return players
    except Exception as e:
        print(f"Database error, using demo data: {e}")
        return get_demo_players(sport)

@st.cache_data(ttl=10)  # Very short cache (10 seconds) to get fresh game data
def load_tonight_games(sport):
    """Load games starting today or within next 24 hours"""
    if not DB_AVAILABLE:
        # Use demo data
        return get_demo_games(sport)
    
    try:
        now = datetime.now(timezone.utc)
        # Show games from today onwards (not just future games)
        # Broaden window to catch games that started up to 12 hours ago
        start_window = now - timedelta(hours=12)
        end_window = now + timedelta(hours=48)
        
        query = supabase.table("games").select("*")
        if sport == "Esports":
            query = query.in_("sport", ESPORTS_SUB_SPORTS)
        else:
            query = query.eq("sport", sport)
        
        games = (
            query.gte("start_time", start_window.isoformat())
            .lte("start_time", end_window.isoformat())
            .order("start_time")
            .execute()
            .data
        )
        return games
    except Exception as e:
        print(f"Database error, using demo data: {e}")
        return get_demo_games(sport)

@st.cache_data(ttl=10)
def load_prop_feed_snapshots(sport, game_ids=None):
    """Load precomputed prop feed snapshots."""
    if not DB_AVAILABLE:
        # Use demo data
        return get_demo_props(sport, game_ids)
    
    try:
        query = supabase.table("prop_feed_snapshots").select("*")
        
        if sport == "Esports":
            query = query.in_("sport", ESPORTS_SUB_SPORTS)
        else:
            query = query.eq("sport", sport)
            
        if game_ids:
            query = query.in_("game_id", game_ids)
        snapshots = query.order("snapshot_at", desc=True).execute().data
        return snapshots or []
    except Exception as exc:
        print(f"Error loading snapshot props, using demo data: {exc}")
        return get_demo_props(sport, game_ids)

