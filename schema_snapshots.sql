-- Snapshot tables for projections and prop marketplace feed
-- Run this after schema.sql to provision supporting materialized datasets

create table if not exists player_projection_snapshots (
  id uuid primary key default gen_random_uuid(),
  player_id uuid references players(id) on delete cascade,
  game_id uuid references games(id) on delete cascade,
  sport text,
  prop_type text not null,
  opponent text,
  is_home boolean,
  projected_line numeric,
  confidence numeric,
  baseline_source text,
  bovada_line numeric,
  factors jsonb,
  sample_size integer,
  injury_status text,
  rest_days integer,
  source_prop_id uuid references player_prop_odds(id) on delete cascade,
  snapshot_version text default 'v1',
  snapshot_at timestamptz default now(),
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(player_id, game_id, prop_type)
);

create index if not exists idx_projection_snapshots_player on player_projection_snapshots(player_id);
create index if not exists idx_projection_snapshots_game on player_projection_snapshots(game_id);
create index if not exists idx_projection_snapshots_prop on player_projection_snapshots(prop_type);

create table if not exists prop_feed_snapshots (
  id uuid primary key default gen_random_uuid(),
  prop_id uuid references player_prop_odds(id) on delete cascade,
  player_id uuid references players(id) on delete cascade,
  game_id uuid references games(id) on delete cascade,
  sport text,
  player_name text,
  team text,
  opponent text,
  is_home boolean,
  prop_type text not null,
  line numeric,
  over_price numeric,
  under_price numeric,
  book text,
  projection_line numeric,
  projection_confidence numeric,
  projection_baseline text,
  projection_bovada_line numeric,
  edge numeric,
  edge_side text,
  edge_prob numeric,
  ev_odds numeric,
  hitrate_over_pct numeric,
  hitrate_under_pct numeric,
  hitrate_games integer,
  dfs_line numeric,
  snapshot_at timestamptz default now(),
  source_prop_created_at timestamptz,
  metadata jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(prop_id)
);

create index if not exists idx_prop_feed_snapshots_player on prop_feed_snapshots(player_id);
create index if not exists idx_prop_feed_snapshots_game on prop_feed_snapshots(game_id);
create index if not exists idx_prop_feed_snapshots_prop_type on prop_feed_snapshots(prop_type);
create index if not exists idx_prop_feed_snapshots_sport on prop_feed_snapshots(sport);

