# API Setup Guide

## Overview

This Sports Betting Analytics Platform integrates with multiple live APIs to provide real-time data, odds, and analytics. The platform is designed to work with your own API keys for full functionality.

## Required API Keys

### 1. The Odds API
- **Purpose**: Real-time odds aggregation from multiple sportsbooks
- **Get Your Key**: https://theoddsapi.com
- **Usage**: Fetches live odds for NBA, NFL, MLB, NHL, NCAAB, NCAAF
- **Rate Limits**: Varies by plan (check your subscription)
- **Environment Variable**: `ODDS_API_KEY`

### 2. Supabase (PostgreSQL Database)
- **Purpose**: Data storage, player profiles, historical stats, odds snapshots
- **Get Your Key**: https://supabase.com
- **Usage**: Primary database for all application data
- **Environment Variables**: 
  - `SUPABASE_URL`
  - `SUPABASE_KEY`

### 3. NBA Stats API
- **Purpose**: Player statistics, game data, historical performance
- **Get Your Key**: https://stats.nba.com (or use public endpoints)
- **Usage**: Player stats, game logs, team data
- **Note**: Some endpoints may be public, others require authentication

### 4. PandaScore API
- **Purpose**: Esports data (CS2, LoL, Dota2, Valorant)
- **Get Your Key**: https://pandascore.co
- **Usage**: Esports matches, player stats, team data
- **Environment Variable**: `PANDASCORE_API_KEY`

## Configuration

### Step 1: Create `.env` File

Create a `.env` file in the project root:

```env
# The Odds API
ODDS_API_KEY=your_theoddsapi_key_here

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_or_service_role_key

# PandaScore (Optional - for Esports)
PANDASCORE_API_KEY=your_pandascore_key_here

# NBA Stats API (if required)
NBA_STATS_API_KEY=your_nba_stats_key_here
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Set Up Database Schema

Run the SQL schema files in your Supabase SQL editor:
- `schema.sql` - Main database schema
- `schema_snapshots.sql` - Snapshot tables
- `schema_injuries.sql` - Injury tracking
- `schema_dfs_lines.sql` - DFS lines

### Step 4: Run Workers (Optional)

To fetch live data, run the worker scripts:

```bash
# Fetch odds
python workers/fetch_odds.py

# Fetch player props
python workers/fetch_player_prop_odds.py

# Build projections
python workers/build_projection_snapshots.py --sport NBA

# Build prop feed
python workers/build_prop_feed_snapshots.py --sport NBA
```

## Demo Mode

**The platform works in demo mode without API keys!**

- Uses sample data from `data_archive/demo_data.json`
- All features are fully functional
- Perfect for portfolio demonstration
- No API calls required

## Production vs Demo

| Feature | Demo Mode | Production Mode |
|---------|-----------|-----------------|
| Data Source | Static JSON file | Live API calls |
| Player Images | ✅ NBA CDN URLs | ✅ Database + CDN |
| Real-Time Odds | ❌ Sample data | ✅ Live from APIs |
| Historical Stats | ❌ Limited | ✅ Full database |
| Projections | ✅ Sample | ✅ ML-powered |
| Updates | Static | Real-time |

## API Rate Limits

Be aware of rate limits for each API:

- **The Odds API**: Varies by plan (typically 500-5000 requests/month)
- **Supabase**: Generous free tier, then usage-based
- **NBA Stats API**: Check official documentation
- **PandaScore**: Varies by plan

## Troubleshooting

### Database Connection Issues
- Verify `SUPABASE_URL` and `SUPABASE_KEY` are correct
- Check network connectivity
- Ensure Supabase project is active

### API Key Errors
- Verify keys are correctly set in `.env`
- Check API key permissions/scopes
- Verify subscription status for paid APIs

### Missing Data
- Run worker scripts to fetch data
- Check API rate limits haven't been exceeded
- Verify database schema is set up correctly

## Security Notes

- **Never commit `.env` file to version control**
- Use environment variables for all sensitive keys
- Consider using Supabase Row Level Security (RLS) for production
- Rotate API keys regularly

## Support

For issues or questions:
1. Check the main `README.md` for setup instructions
2. Review worker script logs for API errors
3. Verify database connectivity with `check_database.py`

---

**Note**: This platform was originally developed with active API subscriptions. For your own use, you'll need to obtain your own API keys from the respective providers.

