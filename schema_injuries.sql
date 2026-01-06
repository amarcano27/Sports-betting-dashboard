-- Injury tracking table
create table if not exists player_injuries (
  id uuid primary key default gen_random_uuid(),
  player_id uuid references players(id) on delete cascade,
  injury_type text, -- 'ankle', 'knee', 'shoulder', 'illness', etc.
  severity text, -- 'questionable', 'probable', 'doubtful', 'out'
  impact_percentage numeric, -- 0-100, how much it affects performance
  status text, -- 'active', 'resolved'
  reported_date date,
  expected_return_date date,
  notes text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_player_injuries_player on player_injuries(player_id);
create index if not exists idx_player_injuries_status on player_injuries(status);

