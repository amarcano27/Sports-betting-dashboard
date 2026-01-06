create extension if not exists "pgcrypto";

create table if not exists games (
  id uuid primary key default gen_random_uuid(),
  sport text,
  external_id text unique,
  home_team text,
  away_team text,
  start_time timestamptz,
  status text default 'scheduled'
);

create table if not exists odds_snapshots (
  id uuid primary key default gen_random_uuid(),
  game_id uuid references games(id) on delete cascade,
  book text,
  market_type text,
  market_label text,
  line numeric,
  price numeric,
  raw jsonb,
  created_at timestamptz default now()
);

create table if not exists ai_suggestions (
  id uuid primary key default gen_random_uuid(),
  legs jsonb,
  total_odds numeric,
  ev_score numeric,
  rationale text,
  created_at timestamptz default now()
);

-- Players table
create table if not exists players (
  id uuid primary key default gen_random_uuid(),
  external_id text unique,
  name text not null,
  position text,
  team text,
  sport text,
  jersey_number integer,
  height text,
  weight integer,
  birth_date date,
  raw_data jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Player game stats
create table if not exists player_game_stats (
  id uuid primary key default gen_random_uuid(),
  player_id uuid references players(id) on delete cascade,
  game_id uuid references games(id) on delete cascade,
  date date not null,
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
  raw_data jsonb,
  created_at timestamptz default now(),
  unique(player_id, game_id)
);

-- Player prop odds
create table if not exists player_prop_odds (
  id uuid primary key default gen_random_uuid(),
  player_id uuid references players(id) on delete cascade,
  game_id uuid references games(id) on delete cascade,
  book text,
  prop_type text, -- 'points', 'rebounds', 'assists', 'pra', etc.
  line numeric,
  over_price numeric,
  under_price numeric,
  raw jsonb,
  created_at timestamptz default now()
);

-- Indexes for performance
create index if not exists idx_players_team on players(team);
create index if not exists idx_players_sport on players(sport);
create index if not exists idx_player_stats_player_game on player_game_stats(player_id, game_id);
create index if not exists idx_player_stats_date on player_game_stats(date);
create index if not exists idx_player_prop_odds_player_game on player_prop_odds(player_id, game_id);

