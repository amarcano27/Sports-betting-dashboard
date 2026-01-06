# Database Setup Instructions

## ⚠️ IMPORTANT: Run This First!

Before syncing players or fetching stats, you need to update your Supabase database schema.

## Steps:

1. **Open Supabase Dashboard**
   - Go to https://supabase.com/dashboard
   - Select your project

2. **Open SQL Editor**
   - Click "SQL Editor" in the left sidebar
   - Click "New Query"

3. **Run the Schema**
   - Open `schema.sql` from this project
   - Copy the ENTIRE file contents
   - Paste into the SQL Editor
   - Click "Run" (or press Ctrl+Enter)

4. **Verify Tables Created**
   - Go to "Table Editor" in left sidebar
   - You should see these new tables:
     - `players`
     - `player_game_stats`
     - `player_prop_odds`

## What the Schema Adds:

- **players**: Stores player information (name, position, team, etc.)
- **player_game_stats**: Historical game statistics for each player
- **player_prop_odds**: Player prop betting odds from bookmakers
- **Indexes**: For fast queries

## After Running Schema:

Then you can run:
```bash
python workers/fetch_player_stats.py --sync-players
```

