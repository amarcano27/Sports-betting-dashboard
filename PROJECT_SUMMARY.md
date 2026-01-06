# Sports Betting Dashboard - Project Summary

## Overview
A comprehensive sports betting analytics dashboard built with Streamlit, Supabase, and The Odds API. The platform helps users find +EV (positive expected value) betting opportunities, compare lines across books, and make data-driven betting decisions.

## Core Features

### ✅ Working Features

#### 1. **Multi-Page Dashboard**
- **Home Page**: Main prop marketplace feed with grid layout
- **Player Props**: Detailed player prop search and analysis
- **Moneylines**: Moneyline odds comparison and best odds finder
- **Line Shopping**: Compare lines across multiple sportsbooks
- **Analytics**: Game analysis and parlay builder
- **Manual DFS Entry**: Manual entry for PrizePicks/Underdog lines

#### 2. **Player Props System**
- **Real-time Prop Loading**: Fetches player props from The Odds API v4
- **Multi-Sport Support**: NBA, NFL, MLB, NHL, NCAAB, NCAAF
- **Prop Types**: Points, Rebounds, Assists, PRA, 3PM, Steals, Blocks, Turnovers
- **Line Comparison**: Shows lines from multiple books (Bovada, FanDuel, DraftKings, etc.)
- **Edge Calculation**: Calculates expected value (EV) for each prop based on historical performance
- **Win Probability**: Bayesian-smoothed probability calculations (avoids 0%/100% extremes)

#### 3. **Custom Projections System**
- **Baseline**: Uses Bovada lines or player averages as starting point
- **Adjustments**: 
  - Opponent defense rating
  - Player matchup history vs opponent
  - Home/away performance
  - Injury status and impact
  - Rest days (back-to-back detection)
  - Pace adjustments
- **Confidence Scoring**: Based on sample size and data consistency
- **Comparison**: Shows difference between our projection and book lines

#### 4. **Prop Insights & Analytics**
- **Historical Hit Rates**: Over/under percentages based on last 50 games
- **Recent Games Table**: Last 10 games vs the line with results
- **Recommendations**: Suggests OVER or UNDER based on historical performance
- **Expected Value Analysis**: Shows edge, win probability, and odds
- **Game Context**: Matchup info, home/away status, rest days

#### 5. **Advanced Filtering**
- **Prop Type Filter**: Points, Rebounds, Assists, PRA, 3PM
- **Team Filter**: Filter by specific teams
- **+EV Only**: Show only props with positive expected value
- **DEGEN Mode**: Higher risk/reward plays (30-50% hit rate, +EV)
- **Alt Lines Filter**: Hide alternative lines, show only standard lines
- **Sport Selection**: Switch between NBA, NFL, MLB, NHL, etc.

#### 6. **Slip Builder**
- **Add/Remove Props**: Build custom betting slips
- **Auto-Calculations**: 
  - Combined odds (parlay calculation)
  - Total expected value
  - Combined win probability
- **Export Options**: JSON and text formats
- **Floating Sidebar**: Always accessible slip builder

#### 7. **AI Slip Generator**
- **Leg Selection**: Choose 3-8 legs for your slip
- **Sharper Books**: Prefers Bovada/Pinnacle lines
- **DFS Adjustment**: Shows adjusted lines for PrizePicks/Underdog (+1-1.5 higher)
- **Diversification**: Selects different players, prop types, and games
- **Edge-Based**: Prioritizes highest +EV props

#### 8. **Data Visualization**
- **Sparkline Charts**: Last 10 games trend visualization
- **Hit Rate Metrics**: Visual over/under percentages
- **Edge Badges**: Color-coded edge indicators
- **Card-Based Layout**: Modern, responsive design

#### 9. **Search & Discovery**
- **Fuzzy Search**: Approximate string matching for player names
- **Autocomplete**: Dropdown suggestions while typing
- **Player Info Display**: Name, position, team, recent trends

#### 10. **Database Integration**
- **Supabase Backend**: PostgreSQL database via Supabase
- **Tables**:
  - `games`: Game schedules and matchups
  - `players`: Player information and teams
  - `player_prop_odds`: Prop lines from various books
  - `player_game_stats`: Historical game statistics
  - `odds_snapshots`: Moneyline and spread odds
  - `dfs_lines`: PrizePicks/Underdog lines (manual entry)
  - `player_injuries`: Injury tracking (schema created)

## Technical Stack

- **Frontend**: Streamlit (Python web framework)
- **Backend**: Supabase (PostgreSQL database)
- **API**: The Odds API v4 (sports odds and player props)
- **Libraries**:
  - `rapidfuzz`: Fuzzy string matching
  - `plotly`: Data visualization
  - `pandas`: Data manipulation
  - `httpx`: HTTP requests

## Data Flow

1. **Fetch Games**: `workers/fetch_odds.py` - Gets game schedules
2. **Fetch Player Props**: `workers/fetch_player_prop_odds.py` - Gets prop lines from API
3. **Fetch Player Stats**: `workers/fetch_player_stats.py` - Gets historical game stats
4. **Calculate Edge**: Uses historical stats to calculate true probability vs book odds
5. **Generate Projections**: Custom algorithm using multiple factors
6. **Display**: Streamlit dashboard renders everything in real-time

## Recent Fixes

- ✅ Fixed team display (was showing "WAS" for all players - now fetches from database)
- ✅ Fixed 100% win probability issue (added Bayesian smoothing)
- ✅ Improved historical data fetching (better date validation and filtering)
- ✅ Enhanced player info fetching (bypasses broken Supabase joins)
- ✅ Added helpful error messages for missing data

## Known Limitations

- **Historical Data**: Requires running `fetch_player_stats.py` to populate stats
- **Projections**: Limited to first 100 props for performance
- **DFS Lines**: Currently manual entry only (scraper available but not recommended)
- **API Credits**: The Odds API has rate limits and credit usage

## Getting Started

1. **Setup**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure**:
   - Set Supabase credentials in `.env`
   - Set The Odds API key in `.env`

3. **Run Dashboard**:
   ```bash
   streamlit run dashboard/main.py
   ```

4. **Fetch Data**:
   ```bash
   python workers/fetch_odds.py              # Get games
   python workers/fetch_player_prop_odds.py  # Get props
   python workers/fetch_player_stats.py      # Get stats
   ```

## Key Metrics Tracked

- **Expected Value (EV)**: Long-term profitability of bets
- **Win Probability**: True probability based on historical performance
- **Edge**: Difference between true probability and implied probability from odds
- **Hit Rate**: Historical over/under percentages
- **Confidence**: Projection confidence based on data quality

## Future Enhancements (Potential)

- Automated DFS line scraping (with safeguards)
- Machine learning-based projections
- Bankroll management tools
- Bet tracking and P&L analysis
- Real-time line movement alerts
- Custom projection models per sport

---

**Status**: Core features working. Dashboard is functional for finding +EV props and comparing lines across books.


