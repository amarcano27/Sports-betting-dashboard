"""
Worker to fetch injury data from free sources and store in database
Run this daily to keep injury data updated
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.injury_data import fetch_and_store_injuries


if __name__ == "__main__":
    print("=" * 50)
    print("Fetching Injury Data from Free Sources")
    print("=" * 50)
    
    injuries = fetch_and_store_injuries()
    
    print(f"\n✅ Done! Processed {len(injuries)} injuries")
    print("\n💡 Tip: Run this daily to keep injury data fresh")
    print("   Add to cron/Task Scheduler for automation")

