"""
Create high-quality sample data for portfolio demonstration
This creates realistic data that showcases all platform capabilities
"""
import sys
from pathlib import Path
import json
from datetime import datetime, timedelta
import random

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase

def create_sample_nba_games():
    """Create sample NBA games"""
    print("\nCreating sample NBA games...")
    
    teams = [
        ("Los Angeles Lakers", "Boston Celtics"),
        ("Golden State Warriors", "Phoenix Suns"),
        ("Milwaukee Bucks", "Miami Heat"),
        ("Denver Nuggets", "Dallas Mavericks"),
        ("Philadelphia 76ers", "Brooklyn Nets"),
    ]
    
    games_created = 0
    now = datetime.now()
    
    for i, (away, home) in enumerate(teams):
        start_time = now + timedelta(hours=i*3 + 2)
        game_data = {
            "sport": "NBA",
            "external_id": f"sample_nba_{i}",
            "home_team": home,
            "away_team": away,
            "start_time": start_time.isoformat(),
            "status": "scheduled"
        }
        
        try:
            result = supabase.table("games").upsert(game_data, on_conflict="external_id").execute()
            if result.data:
                games_created += 1
                print(f"  Created: {away} @ {home}")
        except Exception as e:
            print(f"  Error: {e}")
    
    print(f"Created {games_created} games")
    return games_created

def create_sample_players():
    """Create sample NBA players"""
    print("\nCreating sample NBA players...")
    
    players = [
        {"name": "LeBron James", "team": "Los Angeles Lakers", "position": "F"},
        {"name": "Anthony Davis", "team": "Los Angeles Lakers", "position": "F-C"},
        {"name": "Jayson Tatum", "team": "Boston Celtics", "position": "F"},
        {"name": "Jaylen Brown", "team": "Boston Celtics", "position": "G-F"},
        {"name": "Stephen Curry", "team": "Golden State Warriors", "position": "G"},
        {"name": "Klay Thompson", "team": "Golden State Warriors", "position": "G"},
        {"name": "Kevin Durant", "team": "Phoenix Suns", "position": "F"},
        {"name": "Devin Booker", "team": "Phoenix Suns", "position": "G"},
        {"name": "Giannis Antetokounmpo", "team": "Milwaukee Bucks", "position": "F"},
        {"name": "Damian Lillard", "team": "Milwaukee Bucks", "position": "G"},
        {"name": "Jimmy Butler", "team": "Miami Heat", "position": "F"},
        {"name": "Bam Adebayo", "team": "Miami Heat", "position": "C"},
        {"name": "Nikola Jokic", "team": "Denver Nuggets", "position": "C"},
        {"name": "Jamal Murray", "team": "Denver Nuggets", "position": "G"},
        {"name": "Luka Doncic", "team": "Dallas Mavericks", "position": "G-F"},
        {"name": "Kyrie Irving", "team": "Dallas Mavericks", "position": "G"},
        {"name": "Joel Embiid", "team": "Philadelphia 76ers", "position": "C"},
        {"name": "Tyrese Maxey", "team": "Philadelphia 76ers", "position": "G"},
        {"name": "Mikal Bridges", "team": "Brooklyn Nets", "position": "F"},
        {"name": "Cam Thomas", "team": "Brooklyn Nets", "position": "G"},
    ]
    
    players_created = 0
    for p in players:
        player_data = {
            "name": p["name"],
            "team": p["team"],
            "sport": "NBA",
            "position": p["position"],
            "external_id": f"sample_{p['name'].lower().replace(' ', '_')}"
        }
        
        try:
            result = supabase.table("players").upsert(player_data, on_conflict="external_id").execute()
            if result.data:
                players_created += 1
        except Exception as e:
            print(f"  Error creating {p['name']}: {e}")
    
    print(f"Created {players_created} players")
    return players_created

def create_sample_odds():
    """Create sample odds for games"""
    print("\nCreating sample odds...")
    
    # Get games
    games = supabase.table("games").select("*").eq("sport", "NBA").limit(10).execute().data
    
    if not games:
        print("  No games found")
        return 0
    
    books = ["draftkings", "fanduel", "betmgm", "caesars", "bet365"]
    odds_created = 0
    
    for game in games:
        # Moneyline odds
        home_ml = random.randint(-200, -110)
        away_ml = random.randint(110, 190)
        
        # Spread
        spread = random.choice([-7.5, -6.5, -5.5, -4.5, -3.5, -2.5])
        
        # Total
        total = random.choice([215.5, 217.5, 219.5, 221.5, 223.5])
        
        for book in books:
            # Moneyline
            for team, odds in [(game["home_team"], home_ml), (game["away_team"], away_ml)]:
                odds_data = {
                    "game_id": game["id"],
                    "book": book,
                    "market_type": "h2h",
                    "market_label": team,
                    "price": odds + random.randint(-5, 5)
                }
                try:
                    supabase.table("odds_snapshots").insert(odds_data).execute()
                    odds_created += 1
                except:
                    pass
            
            # Spreads
            for team, line in [(game["home_team"], spread), (game["away_team"], -spread)]:
                odds_data = {
                    "game_id": game["id"],
                    "book": book,
                    "market_type": "spreads",
                    "market_label": team,
                    "price": -110 + random.randint(-5, 5),
                    "line": line
                }
                try:
                    supabase.table("odds_snapshots").insert(odds_data).execute()
                    odds_created += 1
                except:
                    pass
            
            # Totals
            for side, line in [("Over", total), ("Under", total)]:
                odds_data = {
                    "game_id": game["id"],
                    "book": book,
                    "market_type": "totals",
                    "market_label": side,
                    "price": -110 + random.randint(-5, 5),
                    "line": line
                }
                try:
                    supabase.table("odds_snapshots").insert(odds_data).execute()
                    odds_created += 1
                except:
                    pass
    
    print(f"Created {odds_created} odds records")
    return odds_created

def create_sample_player_props():
    """Create sample player props"""
    print("\nCreating sample player props...")
    
    # Get players and games
    players = supabase.table("players").select("*").eq("sport", "NBA").limit(20).execute().data
    games = supabase.table("games").select("*").eq("sport", "NBA").limit(10).execute().data
    
    if not players or not games:
        print("  No players or games found")
        return 0
    
    props_created = 0
    books = ["draftkings", "fanduel", "betmgm"]
    
    # Create props for each player
    for player in players[:15]:  # Top 15 players
        # Find their game
        game = next((g for g in games if player["team"] in [g["home_team"], g["away_team"]]), None)
        if not game:
            continue
        
        # Points prop
        points_line = random.choice([22.5, 24.5, 26.5, 28.5, 30.5])
        over_odds = random.randint(-125, -105)
        under_odds = random.randint(-125, -105)
        
        # Calculate edge (some positive, some negative)
        edge = random.uniform(-0.05, 0.15)
        
        for book in books:
            prop_data = {
                "game_id": game["id"],
                "player_id": player["id"],
                "player_name": player["name"],
                "team": player["team"],
                "prop_type": "points",
                "line": points_line + random.choice([-0.5, 0, 0.5]),
                "over_price": over_odds + random.randint(-5, 5),
                "under_price": under_odds + random.randint(-5, 5),
                "book": book,
                "sport": "NBA",
                "opponent": game["away_team"] if player["team"] == game["home_team"] else game["home_team"],
                "is_home": player["team"] == game["home_team"]
            }
            
            try:
                supabase.table("player_prop_odds").insert(prop_data).execute()
                props_created += 1
            except:
                pass
        
        # Rebounds prop (for forwards/centers)
        if player.get("position") in ["F", "C", "F-C"]:
            rebounds_line = random.choice([8.5, 9.5, 10.5, 11.5])
            for book in books:
                prop_data = {
                    "game_id": game["id"],
                    "player_id": player["id"],
                    "player_name": player["name"],
                    "team": player["team"],
                    "prop_type": "rebounds",
                    "line": rebounds_line,
                    "over_price": random.randint(-125, -105),
                    "under_price": random.randint(-125, -105),
                    "book": book,
                    "sport": "NBA",
                    "opponent": game["away_team"] if player["team"] == game["home_team"] else game["home_team"],
                    "is_home": player["team"] == game["home_team"]
                }
                try:
                    supabase.table("player_prop_odds").insert(prop_data).execute()
                    props_created += 1
                except:
                    pass
        
        # Assists prop (for guards)
        if "G" in player.get("position", ""):
            assists_line = random.choice([5.5, 6.5, 7.5, 8.5])
            for book in books:
                prop_data = {
                    "game_id": game["id"],
                    "player_id": player["id"],
                    "player_name": player["name"],
                    "team": player["team"],
                    "prop_type": "assists",
                    "line": assists_line,
                    "over_price": random.randint(-125, -105),
                    "under_price": random.randint(-125, -105),
                    "book": book,
                    "sport": "NBA",
                    "opponent": game["away_team"] if player["team"] == game["home_team"] else game["home_team"],
                    "is_home": player["team"] == game["home_team"]
                }
                try:
                    supabase.table("player_prop_odds").insert(prop_data).execute()
                    props_created += 1
                except:
                    pass
    
    print(f"Created {props_created} player props")
    return props_created

def create_prop_feed_snapshots():
    """Create prop feed snapshots with edge calculations"""
    print("\nCreating prop feed snapshots...")
    
    # Get player props
    props = supabase.table("player_prop_odds").select("*").limit(100).execute().data
    
    if not props:
        print("  No props found")
        return 0
    
    snapshots_created = 0
    
    for prop in props:
        # Calculate edge
        edge = random.uniform(-0.08, 0.18)  # -8% to +18% edge
        edge_side = "over" if edge > 0 else "under"
        
        # Create snapshot
        snapshot_data = {
            "prop_id": prop["id"],
            "game_id": prop["game_id"],
            "player_id": prop["player_id"],
            "player_name": prop["player_name"],
            "team": prop["team"],
            "opponent": prop.get("opponent"),
            "prop_type": prop["prop_type"],
            "line": prop["line"],
            "over_price": prop["over_price"],
            "under_price": prop["under_price"],
            "book": prop["book"],
            "sport": prop["sport"],
            "edge": edge,
            "edge_side": edge_side,
            "projection_line": prop["line"] + random.uniform(-2, 2),
            "projection_confidence": random.choice(["High", "Medium", "Low"]),
            "snapshot_at": datetime.now().isoformat()
        }
        
        try:
            supabase.table("prop_feed_snapshots").insert(snapshot_data).execute()
            snapshots_created += 1
        except:
            pass
    
    print(f"Created {snapshots_created} prop feed snapshots")
    return snapshots_created

def main():
    print("="*60)
    print("CREATING SAMPLE DATA FOR PORTFOLIO")
    print("="*60)
    
    try:
        create_sample_nba_games()
        create_sample_players()
        create_sample_odds()
        create_sample_player_props()
        create_prop_feed_snapshots()
        
        print("\n" + "="*60)
        print("SAMPLE DATA CREATION COMPLETE")
        print("="*60)
        print("\nYou can now view the dashboard with sample data!")
        print("Run: streamlit run dashboard/main.py")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())


