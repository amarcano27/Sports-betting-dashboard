-- Schema for storing scraped DFS lines (PrizePicks, Underdog)
create table if not exists dfs_lines (
  id uuid primary key default gen_random_uuid(),
  player_id uuid references players(id) on delete cascade,
  prop_type text not null,
  line numeric not null,
  side text, -- 'over' or 'under'
  source text not null, -- 'prizepicks' or 'underdog'
  scraped_at timestamptz default now(),
  game_id uuid references games(id) on delete cascade,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(player_id, prop_type, line, source, game_id)
);

create index if not exists idx_dfs_lines_player_id on dfs_lines(player_id);
create index if not exists idx_dfs_lines_source on dfs_lines(source);
create index if not exists idx_dfs_lines_scraped_at on dfs_lines(scraped_at desc);
create index if not exists idx_dfs_lines_game_id on dfs_lines(game_id);

