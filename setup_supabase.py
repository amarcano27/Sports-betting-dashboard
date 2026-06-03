"""
One-time setup: creates all tables in Supabase and migrates SQLite data.
Run once: python setup_supabase.py
"""
import sys, os, json, sqlite3
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import requests
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── Schema SQL (PostgreSQL-compatible) ────────────────────────
SCHEMA = """
create table if not exists games (
  id text primary key default gen_random_uuid()::text,
  sport text,
  external_id text unique,
  home_team text,
  away_team text,
  start_time text,
  status text default 'scheduled',
  created_at text default now()::text
);

create table if not exists odds_snapshots (
  id text primary key default gen_random_uuid()::text,
  game_id text references games(id) on delete cascade,
  book text,
  market_type text,
  market_label text,
  line numeric,
  price numeric,
  raw text,
  created_at text default now()::text
);

create table if not exists players (
  id text primary key default gen_random_uuid()::text,
  external_id text unique,
  name text not null,
  position text,
  team text,
  sport text,
  jersey_number integer,
  height text,
  weight integer,
  birth_date text,
  raw_data text,
  created_at text default now()::text,
  updated_at text default now()::text
);

create table if not exists player_game_stats (
  id text primary key default gen_random_uuid()::text,
  player_id text references players(id) on delete cascade,
  game_id text references games(id) on delete cascade,
  date text not null,
  opponent text,
  home boolean default true,
  minutes_played numeric,
  points integer,
  rebounds integer,
  assists integer,
  steals integer,
  blocks integer,
  turnovers integer,
  field_goals_made integer,
  field_goals_attempted integer,
  three_pointers_made integer,
  three_pointers_attempted integer,
  free_throws_made integer,
  free_throws_attempted integer,
  raw_data text,
  created_at text default now()::text,
  unique(player_id, game_id)
);

create table if not exists player_prop_odds (
  id text primary key default gen_random_uuid()::text,
  player_id text references players(id) on delete cascade,
  game_id text references games(id) on delete cascade,
  book text,
  prop_type text,
  line numeric,
  over_price numeric,
  under_price numeric,
  raw text,
  created_at text default now()::text
);

create table if not exists ai_suggestions (
  id text primary key default gen_random_uuid()::text,
  legs text,
  total_odds numeric,
  ev_score numeric,
  rationale text,
  created_at text default now()::text
);

create table if not exists player_injuries (
  id text primary key default gen_random_uuid()::text,
  player_id text references players(id) on delete cascade,
  injury_type text,
  severity text,
  impact_percentage numeric,
  status text default 'active',
  expected_return_date text,
  updated_at text,
  created_at text default now()::text
);

create table if not exists prop_feed_snapshots (
  id text primary key default gen_random_uuid()::text,
  player_id text,
  game_id text,
  sport text,
  prop_type text,
  line numeric,
  book text,
  over_price numeric,
  under_price numeric,
  projection numeric,
  edge numeric,
  hit_rate numeric,
  metadata text,
  snapshot_at text,
  created_at text default now()::text
);

create table if not exists dfs_lines (
  id text primary key default gen_random_uuid()::text,
  player_id text,
  prop_type text,
  line numeric,
  side text,
  source text,
  game_id text,
  created_at text default now()::text
);

create index if not exists idx_games_sport on games(sport);
create index if not exists idx_odds_game on odds_snapshots(game_id);
create index if not exists idx_players_sport on players(sport);
create index if not exists idx_props_player on player_prop_odds(player_id);
create index if not exists idx_feed_sport on prop_feed_snapshots(sport);
create index if not exists idx_stats_player on player_game_stats(player_id);
"""

def run_schema():
    """Execute schema via Supabase SQL API (service role needed for DDL)."""
    print("Running schema via REST API...")
    # Use the Management API to run SQL
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    # Split schema into individual statements and run each
    stmts = [s.strip() for s in SCHEMA.split(";") if s.strip()]
    ok, fail = 0, 0
    for stmt in stmts:
        try:
            # Try via the rpc/query approach — needs service role on some projects
            r = requests.post(
                f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
                headers=headers,
                json={"query": stmt + ";"},
                timeout=15
            )
            if r.status_code in (200, 201, 204):
                ok += 1
            else:
                fail += 1
        except Exception:
            fail += 1
    print(f"Schema: {ok} OK, {fail} failed via RPC")
    print()
    print("NOTE: If tables still missing, run schema manually in Supabase SQL Editor:")
    print("  Supabase Dashboard -> SQL Editor -> New query -> paste schema.sql -> Run")


def migrate_sqlite_to_supabase():
    """Copy all data from local SQLite into Supabase."""
    sqlite_path = Path(__file__).parent / "data" / "local.db"
    if not sqlite_path.exists():
        print("No SQLite DB found — skipping migration.")
        return

    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row

    tables_ordered = [
        "games",
        "players",
        "odds_snapshots",
        "player_game_stats",
        "player_prop_odds",
        "prop_feed_snapshots",
        "ai_suggestions",
        "player_injuries",
        "dfs_lines",
    ]

    for tbl in tables_ordered:
        try:
            rows = [dict(r) for r in conn.execute(f"SELECT * FROM {tbl}").fetchall()]
        except Exception:
            continue

        if not rows:
            print(f"  {tbl}: empty, skipping")
            continue

        # Decode JSON strings back to dicts for jsonb columns
        json_cols = {"raw", "raw_data", "legs", "metadata"}
        for row in rows:
            for col in json_cols:
                if col in row and isinstance(row[col], str) and row[col]:
                    try:
                        row[col] = json.loads(row[col])
                    except Exception:
                        pass
            # Convert SQLite integers (0/1) back to bools for 'home'
            if "home" in row and row["home"] is not None:
                row["home"] = bool(row["home"])

        # Batch upsert in chunks of 500
        chunk_size = 500
        inserted = 0
        for i in range(0, len(rows), chunk_size):
            chunk = rows[i:i+chunk_size]
            try:
                sb.table(tbl).upsert(chunk, on_conflict="id").execute()
                inserted += len(chunk)
            except Exception as e:
                print(f"  {tbl} chunk error: {e}")

        print(f"  {tbl}: migrated {inserted}/{len(rows)} rows")

    conn.close()


def verify():
    """Quick check that tables have data."""
    print("\nVerification:")
    for tbl in ["games", "odds_snapshots"]:
        try:
            count = len(sb.table(tbl).select("id").limit(9999).execute().data or [])
            print(f"  {tbl}: {count} rows")
        except Exception as e:
            print(f"  {tbl}: ERROR - {e}")


if __name__ == "__main__":
    print("=== Supabase Setup + Migration ===\n")
    print(f"Target: {SUPABASE_URL}\n")

    print("Step 1: Schema")
    print("-" * 40)
    print("ACTION REQUIRED: Run schema.sql manually in Supabase SQL Editor")
    print("  1. Go to: https://supabase.com/dashboard/project/zehrpfsmgmrwlcaqatbx/sql/new")
    print("  2. Paste contents of: C:\\Users\\Dr3\\Desktop\\sports-betting-dashboard\\schema.sql")
    print("  3. Click RUN")
    print("  4. Re-run this script after schema is applied")
    print()

    print("Step 2: Migrating SQLite data -> Supabase")
    print("-" * 40)
    migrate_sqlite_to_supabase()

    verify()
    print("\nDone. Update .env and restart the dashboard.")
