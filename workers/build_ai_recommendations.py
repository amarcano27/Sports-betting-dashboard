"""
Build AI recommendations and store in Supabase.
Run after odds fetch — generates 10 slips + top 20 props.
"""
import sys, json
from pathlib import Path
from datetime import datetime, timezone

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from services.db import supabase
from utils.ai_engine import generate_recommendations


def ensure_table():
    """Create ai_recommendations table if it doesn't exist yet."""
    sql = """
    CREATE TABLE IF NOT EXISTS ai_recommendations (
        id          uuid DEFAULT gen_random_uuid() PRIMARY KEY,
        generated_at timestamptz NOT NULL DEFAULT now(),
        n_games     integer,
        n_plays     integer,
        slips       jsonb,
        top_props   jsonb,
        created_at  timestamptz DEFAULT now()
    );
    """
    try:
        # Try a read — if it fails the table doesn't exist
        supabase.table("ai_recommendations").select("id").limit(1).execute()
        return True
    except Exception:
        print("ai_recommendations table may not exist — create it in Supabase SQL editor:")
        print(sql)
        return False


def run():
    print(f"[ai_recs] Starting generation — {datetime.now().strftime('%H:%M ET')}")
    if not ensure_table():
        print("[ai_recs] Table missing — attempting to continue anyway")

    recs = generate_recommendations(supabase)
    print(f"[ai_recs] Built {len(recs['slips'])} slips, {len(recs['top_props'])} top props from {recs['n_plays']} plays")

    # Store in Supabase
    try:
        supabase.table("ai_recommendations").insert([{
            "generated_at": recs["generated_at"],
            "n_games":      recs["n_games"],
            "n_plays":      recs["n_plays"],
            "slips":        json.dumps(recs["slips"]),
            "top_props":    json.dumps(recs["top_props"]),
        }]).execute()
        print("[ai_recs] Saved to Supabase ✓")
    except Exception as e:
        print(f"[ai_recs] Save failed: {e}")
        # Dump to local JSON as fallback
        out = project_root / "ai_recommendations_latest.json"
        out.write_text(json.dumps(recs, indent=2))
        print(f"[ai_recs] Saved to {out} instead")

    return recs


if __name__ == "__main__":
    run()
