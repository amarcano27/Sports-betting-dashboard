"""
Check database connectivity and show what's available
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("="*70)
print("DATABASE CONNECTIVITY CHECK")
print("="*70)

# Check environment
print("\n[1] Checking environment variables...")
try:
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if supabase_url:
        print(f"   [OK] SUPABASE_URL found: {supabase_url[:30]}...")
    else:
        print("   [ERROR] SUPABASE_URL not found")
    
    if supabase_key:
        print(f"   [OK] SUPABASE_KEY found: {supabase_key[:20]}...")
    else:
        print("   [ERROR] SUPABASE_KEY not found")
except Exception as e:
    print(f"   [ERROR] Error loading env: {e}")

# Check database connection
print("\n[2] Testing database connection...")
try:
    from services.db import supabase
    
    # Try a simple query
    result = supabase.table("players").select("id").limit(1).execute()
    print(f"   [OK] Database connection successful!")
    print(f"   [OK] Found {len(result.data)} test record(s)")
    
    # Check tables
    print("\n[3] Checking available data...")
    tables = ["games", "players", "player_prop_odds", "prop_feed_snapshots", "odds_snapshots"]
    
    for table in tables:
        try:
            count = supabase.table(table).select("id", count="exact").limit(0).execute()
            print(f"   [OK] {table}: {count.count if hasattr(count, 'count') else 'N/A'} records")
        except Exception as e:
            print(f"   [ERROR] {table}: Error - {e}")
    
    # Check for images
    print("\n[4] Checking player images...")
    players_with_images = supabase.table("players").select("id,name,external_id,image_url").eq("sport", "NBA").limit(10).execute()
    if players_with_images.data:
        print(f"   [OK] Found {len(players_with_images.data)} NBA players")
        with_images = sum(1 for p in players_with_images.data if p.get("external_id") or p.get("image_url"))
        print(f"   [OK] {with_images} players have image data")
        
        # Show sample
        print("\n   Sample players:")
        for p in players_with_images.data[:5]:
            img_info = f"external_id: {p.get('external_id')}" if p.get('external_id') else "no image"
            print(f"     - {p.get('name')}: {img_info}")
    
except Exception as e:
    print(f"   [ERROR] Database connection failed: {e}")
    print(f"   Error type: {type(e).__name__}")
    
    if "getaddrinfo failed" in str(e):
        print("\n   [WARNING] NETWORK ERROR: Cannot resolve database hostname")
        print("   Possible causes:")
        print("     - No internet connection")
        print("     - DNS resolution issue")
        print("     - Firewall blocking connection")
        print("     - VPN required")
        print("\n   Dashboard will use demo data until connection is restored.")
    elif "401" in str(e) or "403" in str(e):
        print("\n   [WARNING] AUTHENTICATION ERROR: Invalid credentials")
        print("   Check your SUPABASE_KEY in .env file")
    elif "404" in str(e):
        print("\n   [WARNING] NOT FOUND ERROR: Invalid SUPABASE_URL")
        print("   Check your SUPABASE_URL in .env file")

print("\n" + "="*70)
print("CHECK COMPLETE")
print("="*70)
print("\nIf database is unavailable, the dashboard will use demo data.")
print("To restore full functionality, fix the database connection issue above.")

