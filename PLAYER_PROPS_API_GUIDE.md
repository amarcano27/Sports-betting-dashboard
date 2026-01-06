# Player Props API Guide - The Odds API v4

## Overview

This guide explains how to properly fetch player props using The Odds API v4, based on the [official documentation](https://the-odds-api.com/liveapi/guides/v4/).

## Key Changes for v4 API

### Market Structure

The v4 API uses **specific market keys** for player props, not a generic `player_props` market:

**NBA Markets:**
- `player_points` - Points props
- `player_rebounds` - Rebounds props
- `player_assists` - Assists props
- `player_threes` - Three-pointers made
- `player_steals` - Steals props
- `player_blocks` - Blocks props
- `player_turnovers` - Turnovers props
- `player_pra` - Points + Rebounds + Assists

**NFL Markets:**
- `player_pass_tds` - Passing touchdowns
- `player_pass_yds` - Passing yards
- `player_pass_completions` - Pass completions
- `player_rush_yds` - Rushing yards
- `player_rush_attempts` - Rush attempts
- `player_receptions` - Receptions
- `player_reception_yds` - Reception yards
- `player_anytime_td` - Anytime touchdown

### Response Structure

The v4 API returns outcomes in this format:

```json
{
  "name": "Over",  // or "Under"
  "description": "Anthony Davis",  // Player name
  "point": 23.5,  // The line
  "price": -110  // The odds
}
```

**Important:** 
- `name` = "Over" or "Under"
- `description` = Player name
- `point` = The line value
- `price` = The odds

## Usage

### Fetching Player Props

```bash
python workers/fetch_player_prop_odds.py
```

This will:
1. Fetch player props for NBA (or specify sport)
2. Use the correct market keys for v4 API
3. Parse outcomes correctly (player name in `description`, not `name`)
4. Store both over and under prices for each prop
5. Show API credit usage in the terminal

### API Credit Usage

According to the [v4 documentation](https://the-odds-api.com/liveapi/guides/v4/), the cost is:

```
cost = 10 × [number of unique markets returned] × [number of regions specified]
```

**Example:**
- 8 NBA player prop markets × 1 region (us) = **80 credits**

The response headers show:
- `x-requests-remaining` - Credits left
- `x-requests-used` - Credits used
- `x-requests-last` - Cost of last request

### Prerequisites

1. **Games must be in database:**
   ```bash
   python workers/fetch_odds.py
   ```

2. **Players must be synced:**
   ```bash
   python workers/fetch_player_stats.py --sync-players
   ```

3. **API Plan:**
   - Player props may require a paid plan
   - Check your plan at [The Odds API](https://the-odds-api.com/)

## Troubleshooting

### "No player prop odds available"

**Possible causes:**
1. API plan doesn't include player props
2. No games in database
3. No players synced
4. Rate limit exceeded (429 error)

**Solutions:**
1. Check API plan includes player props
2. Run `python workers/fetch_odds.py` first
3. Run `python workers/fetch_player_stats.py --sync-players`
4. Wait if rate limited, then try again

### "Player 'X' not found in database"

**Solution:**
- Sync players: `python workers/fetch_player_stats.py --sync-players`
- Player names must match between API and database (fuzzy matching helps)

### Rate Limit (429 Error)

**Solution:**
- Wait a few seconds between requests
- The API will show rate limit info in error response

## Code Structure

### Updated Files

1. **`services/odds_api.py`**
   - Updated `get_player_props()` to use correct market keys
   - Added API credit tracking
   - Better error handling

2. **`workers/fetch_player_prop_odds.py`**
   - Updated to parse v4 API structure correctly
   - Player name from `description` field
   - Handles both over/under outcomes properly

## References

- [The Odds API v4 Documentation](https://the-odds-api.com/liveapi/guides/v4/)
- [Market Keys Reference](https://the-odds-api.com/liveapi/guides/v4/#get-odds)
- [Usage Quota Costs](https://the-odds-api.com/liveapi/guides/v4/#usage-quota-costs)

