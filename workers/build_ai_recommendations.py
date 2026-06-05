"""
Build AI recommendations and store in Supabase.
Run after odds fetch — generates:
  1. Math-based slips + top props (existing engine)
  2. LLM-based full analysis write-up (Claude API)
Both results stored in ai_recommendations table.
"""
import sys, json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from services.db import supabase
from utils.ai_engine import generate_recommendations
from utils.llm_analyst import generate_llm_analysis


def ensure_table():
    """Check ai_recommendations table exists (and has llm_writeup column)."""
    sql_create = """
    CREATE TABLE IF NOT EXISTS ai_recommendations (
        id           uuid DEFAULT gen_random_uuid() PRIMARY KEY,
        generated_at timestamptz NOT NULL DEFAULT now(),
        n_games      integer,
        n_plays      integer,
        slips        jsonb,
        top_props    jsonb,
        llm_analysis jsonb,
        created_at   timestamptz DEFAULT now()
    );
    -- Add llm_analysis column if upgrading from old schema
    ALTER TABLE ai_recommendations ADD COLUMN IF NOT EXISTS llm_analysis jsonb;
    """
    try:
        supabase.table("ai_recommendations").select("id").limit(1).execute()
        return True
    except Exception:
        print("ai_recommendations table may not exist — create it in Supabase SQL editor:")
        print(sql_create)
        return False


def load_raw_data():
    """Load games, odds, players from Supabase for the LLM analyst."""
    games    = supabase.table("games").select("*").execute().data or []
    all_odds = supabase.table("odds_snapshots").select("*").execute().data or []
    players  = supabase.table("players").select("*").execute().data or []

    odds_map: dict[str, list] = defaultdict(list)
    for r in all_odds:
        odds_map[r["game_id"]].append(r)

    player_ids = [p["id"] for p in players]
    logs_map: dict[str, list] = defaultdict(list)
    if player_ids:
        logs = (supabase.table("player_game_stats")
                .select("*")
                .in_("player_id", player_ids[:100])
                .order("date", desc=True)
                .execute().data or [])
        for l in logs:
            logs_map[l["player_id"]].append(l)

    return games, odds_map, players, logs_map


def build_pitcher_db(games: list[dict]) -> dict:
    """Build pitcher DB from live MLB API (reused from ai_engine logic)."""
    from dashboard.mlb_page import find_pitcher as _find_pitcher

    TEAM_ABBR = {
        "Detroit Tigers": "DET", "Tampa Bay Rays": "TB",
        "San Diego Padres": "SD", "Philadelphia Phillies": "PHI",
        "Miami Marlins": "MIA", "Washington Nationals": "WSH",
        "Baltimore Orioles": "BAL", "Boston Red Sox": "BOS",
        "Cleveland Guardians": "CLE", "New York Yankees": "NYY",
        "Kansas City Royals": "KC", "Cincinnati Reds": "CIN",
        "Toronto Blue Jays": "TOR", "Atlanta Braves": "ATL",
        "Chicago White Sox": "CHW", "Minnesota Twins": "MIN",
        "San Francisco Giants": "SF", "Milwaukee Brewers": "MIL",
        "Texas Rangers": "TEX", "St. Louis Cardinals": "STL",
        "Athletics": "OAK", "Chicago Cubs": "CHC",
        "Pittsburgh Pirates": "PIT", "Houston Astros": "HOU",
        "Colorado Rockies": "COL", "Los Angeles Angels": "LAA",
        "Los Angeles Dodgers": "LAD", "Arizona Diamondbacks": "ARI",
        "New York Mets": "NYM", "Seattle Mariners": "SEA",
    }

    pitcher_db = {}
    mlb_games = [g for g in games if g.get("sport") == "MLB"]
    for g in mlb_games:
        for team in [g["away_team"], g["home_team"]]:
            abbr = TEAM_ABBR.get(team, "")
            if not abbr:
                continue
            try:
                pname, pstats = _find_pitcher(team)
                if pname and pstats:
                    key = pname.lower().split()[-1]
                    pitcher_db[key] = {**pstats, "team": abbr}
            except Exception:
                pass
    return pitcher_db


def run():
    ts = datetime.now().strftime("%H:%M ET")
    print(f"[ai_recs] Starting — {ts}")

    if not ensure_table():
        print("[ai_recs] Table check failed — continuing anyway")

    # ── Step 1: Math-based recommendations (existing engine) ──
    print("[ai_recs] Step 1 — Math engine (Poisson/Elo)...")
    try:
        math_recs = generate_recommendations(supabase)
        print(f"[ai_recs] Math engine: {len(math_recs['slips'])} slips, "
              f"{len(math_recs['top_props'])} top props from {math_recs['n_plays']} plays")
    except Exception as e:
        print(f"[ai_recs] Math engine failed: {e}")
        math_recs = {"slips": [], "top_props": [], "n_games": 0, "n_plays": 0,
                     "generated_at": datetime.now(timezone.utc).isoformat()}

    # ── Step 2: LLM analysis (Claude API) ───────────────────
    print("[ai_recs] Step 2 — LLM analyst (Claude API)...")
    try:
        games, odds_map, players, logs_map = load_raw_data()
        pitcher_db = build_pitcher_db(games)
        llm_result = generate_llm_analysis(
            games=games,
            odds_map=odds_map,
            pitcher_db=pitcher_db,
            players=players,
            logs_map=logs_map,
        )
        if "error" in llm_result:
            print(f"[ai_recs] LLM warning: {llm_result['error']}")
        else:
            n_props = llm_result.get("n_props", 0)
            n_slips = len(llm_result.get("slips", []))
            print(f"[ai_recs] LLM analyst: {n_props} plays, {n_slips} slips ✓")
    except Exception as e:
        print(f"[ai_recs] LLM analyst failed: {e}")
        llm_result = {"error": str(e)}

    # ── Step 3: Store in Supabase ────────────────────────────
    row = {
        "generated_at": math_recs.get("generated_at",
                                       datetime.now(timezone.utc).isoformat()),
        "n_games":      math_recs.get("n_games", 0),
        "n_plays":      math_recs.get("n_plays", 0),
        "slips":        json.dumps(math_recs.get("slips", [])),
        "top_props":    json.dumps(math_recs.get("top_props", [])),
        "llm_analysis": json.dumps(llm_result),
    }

    try:
        supabase.table("ai_recommendations").insert([row]).execute()
        print("[ai_recs] Saved to Supabase ✓")
    except Exception as e:
        print(f"[ai_recs] Supabase save failed: {e}")
        out = project_root / "ai_recommendations_latest.json"
        out.write_text(json.dumps({**math_recs, "llm_analysis": llm_result}, indent=2))
        print(f"[ai_recs] Saved locally to {out}")

    return {**math_recs, "llm_analysis": llm_result}


if __name__ == "__main__":
    run()
