# Custom Projections & Line Shopping System

## 🎯 Overview

This system generates **our own custom player prop lines** using free data sources and compares them to all book lines to find the best value. **No paid APIs, no manual input required.**

## 📊 How Our Projections Work

### Data Sources (All Free)

1. **Player Statistics** - From NBA Stats API (free, public)
2. **Matchup Performance** - Historical player stats vs specific opponents
3. **Injury Reports** - From NBA Stats API and ESPN (free, public)
4. **Book Lines** - From The Odds API (you already have this)
5. **Opponent Defense** - Calculated from historical game data
6. **Home/Away Splits** - Player performance at home vs away
7. **Rest Days** - Days between games (back-to-back impact)

### Projection Calculation

Our projections use a **multi-factor model**:

```
Our Line = Baseline × Defense Adj × Matchup Adj × Home/Away Adj × Injury Adj × Rest Adj × Pace Adj
```

**Baseline Options:**
- Bovada line (if available) - considered a "sharp" book
- Player's recent weighted average (if no Bovada line)

**Adjustments:**
- **Defense Adjustment**: How opponent typically defends this stat type
- **Matchup Adjustment**: Player's historical performance vs this specific opponent
- **Home/Away Adjustment**: Player's home vs away performance
- **Injury Adjustment**: Impact of current injuries (0-100% reduction)
- **Rest Adjustment**: Back-to-back games (-5%), 3+ days rest (+2%)
- **Pace Adjustment**: Game pace impact (future enhancement)

### Confidence Score

Each projection includes a confidence score (0-100%) based on:
- Sample size (more games = higher confidence)
- Data consistency (lower variance = higher confidence)
- Data freshness (recent data weighted more)

## 🛒 Line Shopping Tool

The **Line Shopping** page compares our projections to all available book lines:

1. **Select Game & Player** - Choose the matchup
2. **View Our Projection** - See our calculated line with confidence
3. **Compare All Books** - See every book's line for that prop
4. **Find Best Value** - System highlights which side (over/under) has value
5. **Get Recommendations** - See which book offers the best odds

### Value Calculation

When our line differs significantly from a book line:
- **Our line higher** → Over has value (bet over)
- **Our line lower** → Under has value (bet under)
- **Difference > 0.5** → Significant value opportunity

## 🔄 Keeping Data Fresh

### Daily Tasks (Automate with Cron/Task Scheduler)

1. **Fetch Injuries** (Run daily):
   ```bash
   python workers/fetch_injuries.py
   ```
   - Fetches from NBA Stats API and ESPN (free)
   - Updates `player_injuries` table

2. **Fetch Player Stats** (Run daily or weekly):
   ```bash
   python workers/fetch_player_stats.py --all
   ```
   - Updates `player_game_stats` table
   - Provides historical data for projections

3. **Fetch Book Lines** (Run multiple times daily):
   ```bash
   python workers/fetch_player_prop_odds.py
   ```
   - Updates `player_prop_odds` table
   - Provides lines from all books for comparison

## 📈 Using the System

### On Home Page

1. **Enable "Show Our Projections"** in sidebar
2. See our projected line next to each prop
3. Compare to book lines
4. Look for props where our line differs significantly

### On Line Shopping Page

1. Select game, player, and prop type
2. See our projection with full breakdown
3. View all book lines side-by-side
4. Get recommendations for best value

### In Slip Generator

- Our projections are automatically used when generating slips
- System prioritizes props where our line suggests value
- DFS adjustments can be applied on top of our projections

## 🎯 Key Features

### ✅ Free Data Sources
- NBA Stats API (public, free)
- ESPN injury data (public, free)
- The Odds API (you already pay for this)

### ✅ No Manual Input
- Everything automated
- Just run the workers daily

### ✅ Comprehensive Model
- Multiple factors considered
- Confidence scores provided
- Transparent calculations

### ✅ Line Shopping
- Compare all books at once
- Find best value automatically
- Get specific recommendations

## 🔧 Technical Details

### Database Tables Used

- `players` - Player information
- `player_game_stats` - Historical performance
- `player_prop_odds` - Book lines
- `player_injuries` - Injury status
- `games` - Game information

### Key Functions

- `calculate_projection()` - Main projection calculation
- `calculate_opponent_defense_rating()` - Defense adjustment
- `calculate_opponent_adjustment()` - Matchup adjustment
- `get_injury_status()` - Injury impact
- `get_player_rest_days()` - Rest calculation

## 📊 Example Workflow

1. **Morning**: Run `fetch_injuries.py` to get latest injury reports
2. **Afternoon**: Run `fetch_player_prop_odds.py` to get book lines
3. **Evening**: Use Line Shopping tool to find value plays
4. **Before Games**: Generate slips using our projections

## 💡 Tips

- **Higher confidence** = More reliable projection
- **Larger differences** = More value opportunity
- **Multiple books** = Better line shopping
- **Fresh data** = More accurate projections

## 🚀 Future Enhancements

- Pace adjustment (team pace stats)
- Weather factors (for outdoor sports)
- Referee tendencies
- Line movement tracking
- Historical accuracy tracking

