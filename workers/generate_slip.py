import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.db import supabase


def get_top_edges(limit=30):
    odds = supabase.table("odds_snapshots").select("*").order("created_at", desc=True).limit(limit).execute().data
    for o in odds:
        o["edge"] = round((abs(o["price"] or 0) % 100) / 1000, 3)
    return odds


def build_slip():
    candidates = get_top_edges()
    slip = candidates[:6]
    rationale = "Auto-generated slip using latest odds (placeholder logic)."
    supabase.table("ai_suggestions").insert({
        "legs": json.dumps(slip),
        "total_odds": None,
        "ev_score": None,
        "rationale": rationale
    }).execute()


if __name__ == "__main__":
    build_slip()

