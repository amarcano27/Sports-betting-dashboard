"""
Automatic Data Refresh Scheduler
Runs data refresh workers at optimal intervals to stay within API limits.

Recommended Schedule:
- Every 4 hours during active hours (8 AM - 12 AM)
- Total: ~4 refreshes per day = ~120/month (well within free tier limits)

API Usage:
- The Odds API: ~7 calls per refresh (6 sports + Esports) = ~28 calls/day = ~840/month
- PandaScore: ~3 calls per refresh (4 esports games) = ~12 calls/day = ~360/month
- Total: Safe for free tiers
"""
import schedule
import time
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def run_refresh_worker(script_path, label, args=None):
    """Run a worker script and log results."""
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running {label}...")
        cmd = [sys.executable, script_path]
        if args:
            cmd.extend(args.split())
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout per worker
        )
        if result.returncode == 0:
            print(f"✓ {label} completed successfully")
            if result.stdout:
                print(f"  Output: {result.stdout[-200:]}")  # Last 200 chars
        else:
            print(f"✗ {label} failed: {result.stderr[:200]}")
    except subprocess.TimeoutExpired:
        print(f"✗ {label} timed out after 5 minutes")
    except Exception as e:
        print(f"✗ {label} error: {e}")

def refresh_all_data():
    """Run the full data refresh pipeline."""
    print(f"\n{'='*60}")
    print(f"STARTING SCHEDULED REFRESH - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    # Run workers in sequence
    workers = [
        ("workers/fetch_odds.py", "Fetch Odds"),
        ("workers/fetch_esports.py", "Fetch Esports"),
        ("workers/fetch_player_prop_odds.py", "Fetch Player Props"),
    ]
    
    for script, label in workers:
        run_refresh_worker(script, label)
        time.sleep(5)  # Small delay between workers
    
    # Build snapshots for main sports (these are fast)
    snapshot_workers = [
        ("workers/build_projection_snapshots.py", "NBA", "--sport NBA --hours 48"),
        ("workers/build_prop_feed_snapshots.py", "NBA", "--sport NBA --hours 48"),
        ("workers/build_projection_snapshots.py", "Esports", "--sport Esports --hours 48"),
        ("workers/build_prop_feed_snapshots.py", "Esports", "--sport Esports --hours 48"),
    ]
    
    for script, sport, args in snapshot_workers:
        run_refresh_worker(script, f"Build Snapshots ({sport})", args)
        time.sleep(2)
    
    print(f"\n{'='*60}")
    print(f"REFRESH COMPLETE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

def main():
    """Set up and run the scheduler."""
    print("="*60)
    print("SPORTS BETTING DASHBOARD - AUTO REFRESH SCHEDULER")
    print("="*60)
    print("\nSchedule:")
    print("  - Every 4 hours: 8:00 AM, 12:00 PM, 4:00 PM, 8:00 PM")
    print("  - Total: ~4 refreshes/day = ~120/month")
    print("\nStarting scheduler... (Press Ctrl+C to stop)")
    print("="*60 + "\n")
    
    # Schedule refreshes every 4 hours during active hours
    schedule.every().day.at("08:00").do(refresh_all_data)
    schedule.every().day.at("12:00").do(refresh_all_data)
    schedule.every().day.at("16:00").do(refresh_all_data)
    schedule.every().day.at("20:00").do(refresh_all_data)
    
    # Run immediately on start (optional - comment out if you don't want this)
    # refresh_all_data()
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nScheduler stopped by user.")
        sys.exit(0)

