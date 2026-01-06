# Player Stats & Props Integration Guide

## 🎯 Overview

This guide explains how to integrate real player statistics and player prop odds into your dashboard.

## 📊 Database Setup

### Step 1: Update Database Schema

Run the updated `schema.sql` in your Supabase SQL editor to create the new tables:

```sql
-- This adds:
-- 1. players table
-- 2. player_game_stats table  
-- 3. player_prop_odds table
-- 4. Indexes for performance
```

**Run in Supabase:**
1. Go to SQL Editor
2. Copy contents of `schema.sql`
3. Run the query

## 🔄 Syncing Players

### Step 2: Sync NBA Players

Fetch all current NBA players:

```bash
cd sports-betting-dashboard
.\venv\Scripts\Activate.ps1
python workers/fetch_player_stats.py --sync-players
```

This will:
- Fetch all active NBA players from NBA Stats API
- Store them in the `players` table
- Update existing players if they already exist

**Expected output:**
```
Fetching NBA players...
Found 450+ players
Synced 450+ players to database
```

## 📈 Fetching Player Stats

### Step 3: Fetch Game Statistics

#### Option A: Fetch Stats for All Players
```bash
python workers/fetch_player_stats.py --all
```

**Note:** This can take a while (1 second per player for rate limiting). Consider running overnight or for specific players.

#### Option B: Fetch Stats for Specific Player
```bash
# First, get player ID from database or dashboard
python workers/fetch_player_stats.py --player-id <player_uuid>
```

#### Option C: Fetch Stats for Players in Upcoming Games
Create a script to fetch stats only for players in games you're tracking.

### What Gets Stored:
- Points, Rebounds, Assists
- Steals, Blocks, Turnovers
- Field goal stats
- Three-point stats
- Free throw stats
- Minutes played
- Opponent and home/away status

## 🎲 Fetching Player Prop Odds

### Step 4: Get Player Prop Odds

**Note:** Player props may require a paid plan from The Odds API.

```bash
python workers/fetch_player_prop_odds.py
```

This will:
- Fetch player prop odds from The Odds API
- Match players by name
- Store over/under odds for each prop type
- Link to games and players in your database

**If you get "404" or "not available":**
- Player props may not be in your API plan
- Check The Odds API documentation for your plan features
- You may need to upgrade your subscription

## 🎮 Using the Dashboard

### Step 5: Access Player Props Dashboard

```bash
streamlit run dashboard/player_props_page.py
```

### Features Now Available:

1. **Player Search**
   - Search by name (real-time search)
   - Filter by team
   - Auto-populates from database

2. **Real Stats Display**
   - Historical game stats from database
   - Hitrates calculated from real data
   - Charts show actual performance

3. **Live Prop Odds**
   - Shows odds from bookmakers (if fetched)
   - Updates with latest lines
   - Multiple bookmaker support

## 🔧 API Information

### NBA Stats API

The integration uses the public NBA Stats API (`stats.nba.com`):
- **Free**: No API key required
- **Rate Limits**: Be respectful (1 request/second recommended)
- **Endpoints Used**:
  - `commonallplayers`: Get all players
  - `playergamelog`: Get player game statistics

**Note:** The NBA Stats API may have CORS restrictions. The code includes proper headers to work around this.

### The Odds API

For player prop odds:
- Check your plan at https://the-odds-api.com/
- Player props may require a paid tier
- Free tier typically includes: moneyline, spreads, totals only

## 📝 Data Flow

```
1. Sync Players
   NBA Stats API → players table

2. Fetch Game Stats  
   NBA Stats API → player_game_stats table

3. Fetch Prop Odds
   The Odds API → player_prop_odds table

4. Dashboard Display
   Database → Player Props Dashboard
```

## 🚀 Automation

### Recommended Cron Jobs (or Task Scheduler on Windows):

```bash
# Sync players weekly (roster changes)
0 0 * * 0 /path/to/venv/bin/python /path/to/workers/fetch_player_stats.py --sync-players

# Fetch stats daily for active players
0 2 * * * /path/to/venv/bin/python /path/to/workers/fetch_player_stats.py --all

# Fetch prop odds every 15 minutes
*/15 * * * * /path/to/venv/bin/python /path/to/workers/fetch_player_prop_odds.py
```

## 🐛 Troubleshooting

### "No players found"
- Run `--sync-players` first
- Check NBA Stats API is accessible
- Verify database connection

### "No stats found for player"
- Run `--player-id <id>` to fetch stats
- Check if player has played games this season
- Verify game dates match between NBA API and your games table

### "Player props not available"
- Check your Odds API plan
- Verify player props are included
- Some books may not offer props for all players

### Rate Limiting
- NBA Stats API: Add delays between requests (1 second)
- The Odds API: Check your monthly request limit
- Use caching to reduce API calls

## 📊 Database Queries

### Check Players Count
```sql
SELECT COUNT(*) FROM players WHERE sport = 'NBA';
```

### Check Stats Count
```sql
SELECT COUNT(*) FROM player_game_stats;
```

### Find Player by Name
```sql
SELECT * FROM players WHERE name ILIKE '%josh hart%';
```

### Get Player Stats
```sql
SELECT * FROM player_game_stats 
WHERE player_id = '<player_uuid>' 
ORDER BY date DESC 
LIMIT 10;
```

## 🎯 Next Steps

1. **Run initial sync**: `--sync-players`
2. **Fetch stats for key players**: `--player-id` for players you're tracking
3. **Set up automation**: Schedule regular fetches
4. **Monitor usage**: Track API rate limits
5. **Expand coverage**: Add more players as needed

## 💡 Tips

- **Start Small**: Sync players first, then fetch stats for players you're actively tracking
- **Cache Wisely**: Dashboard caches data for 5 minutes to reduce DB queries
- **Batch Operations**: Fetch stats during off-peak hours
- **Monitor Costs**: Track API usage if using paid services

Enjoy your fully integrated player props dashboard! 🎯

