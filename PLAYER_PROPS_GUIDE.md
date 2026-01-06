# Player Props Dashboard Guide

## 🎯 Overview

The Player Props Dashboard is a sophisticated interface designed for analyzing player prop bets, matching the style of professional sports betting analytics platforms.

## 🚀 Quick Start

### Option 1: Direct Launch
```bash
cd sports-betting-dashboard
.\venv\Scripts\Activate.ps1
streamlit run dashboard/player_props_page.py
```

### Option 2: Using Launcher
```bash
cd sports-betting-dashboard
.\venv\Scripts\Activate.ps1
python run_player_props.py
```

## 📊 Features

### 1. Player Profile Section
- **Player Avatar**: Circular avatar with player initials
- **Player Info**: Name, position, team, and game time
- **Game Selection**: Choose from upcoming games in the sidebar

### 2. Prop Categories
Four main prop types available:
- **Points**: Player point totals
- **Rebounds**: Player rebound totals  
- **Assists**: Player assist totals
- **Points Rebounds Assists (PRA)**: Combined stat

### 3. Alt Lines Selector
- Switch between different over/under lines (9.5, 10.5, 11.5, 12.5)
- View current odds for Over/Under on selected line
- Updates chart and hitrates dynamically

### 4. Game Lines Table
Displays betting lines for the selected game:
- **Spread**: Point spreads for both teams
- **Total**: Over/Under totals
- **Moneyline**: Win/loss odds

### 5. Hitrates Section
Three tabs showing historical performance:
- **Hitrates**: Overall performance across time periods
- **Home**: Performance in home games
- **Away**: Performance in away games

Time periods analyzed:
- **L3**: Last 3 games
- **L6**: Last 6 games
- **L9**: Last 9 games
- **L12**: Last 12 games
- **L15**: Last 15 games
- **L30**: Last 30 games

Each shows:
- **Average**: Mean value for the period
- **Hitrate (%)**: Percentage of games over the line

### 6. Statistics Section
- **Calculated Minutes**: Estimated playing time
- **Minutes Slider**: Adjust projected minutes (0-48)
- **Filter Tabs**: 
  - L3, L6, L9, L10, L15, L30 (time periods)
  - Home, Away (venue)
  - H2H (head-to-head vs opponent)

### 7. Player Prop Chart
Interactive bar chart showing:
- **Green Bars**: Games where player exceeded the line
- **Red Bars**: Games where player fell below the line
- **Dashed Line**: The current over/under line
- **Game Labels**: Opponent and date for each game
- **Value Labels**: Exact stat value on each bar

## 🎨 Design Features

- **Dark Theme**: Professional dark background (#0e1117)
- **Color Coding**: 
  - Green (#10b981) for positive outcomes
  - Red (#ef4444) for negative outcomes
  - Gray accents for neutral elements
- **Modern UI**: Clean, card-based layout
- **Responsive**: Adapts to different screen sizes

## 📈 How to Use

### Step 1: Select Game & Player
1. Use sidebar to choose sport (NBA/NFL)
2. Select a game from the dropdown
3. Enter player name (or use default "Josh Hart")
4. Select player position and team

### Step 2: Choose Prop Type
- Click on Points, Rebounds, Assists, or PRA
- Active prop is highlighted in green

### Step 3: Adjust Line
- Use "Alt Lines" dropdown to change the over/under line
- View current odds for Over/Under

### Step 4: Analyze Hitrates
- Check "Hitrates" tab for overall performance
- Switch to "Home" or "Away" for venue-specific stats
- Review averages and hitrates across time periods

### Step 5: Review Chart
- Chart updates based on:
  - Selected prop type
  - Selected line
  - Active statistics tab (L3, L6, Home, Away, etc.)
- Color coding shows performance vs line

## 🔧 Current Status

### ✅ Implemented
- Player profile display
- Prop category selection
- Alt lines selector
- Game lines table
- Hitrate calculations
- Statistics filtering
- Interactive prop chart
- Dark theme UI

### 🚧 Pending Integration
- **Player Stats API**: Currently using mock data
  - Structure ready for ESPN, NBA Stats API, or similar
  - See `utils/player_stats.py` for integration points
- **Real-time Odds**: Player prop odds from bookmakers
  - Currently shows placeholder odds
  - Ready to integrate with odds API

## 📝 Data Structure

### Mock Game Data Format
```python
{
    "date": "2024-10-24",
    "opponent": "DEN",
    "home": True,
    "points": 15,
    "rebounds": 11,
    "assists": 5
}
```

### Integration Points
1. **Player Stats**: Replace `mock_games` in `player_props_page.py` with API data
2. **Prop Odds**: Add player prop odds to `odds_snapshots` table
3. **Player Database**: Create player lookup table for easier selection

## 🎯 Next Steps

1. **Integrate Player Stats API**
   - Connect to NBA Stats API, ESPN, or similar
   - Populate historical game data
   - Update hitrate calculations with real data

2. **Add Player Prop Odds**
   - Extend odds fetching to include player props
   - Store in database with player_id reference
   - Display in odds section

3. **Player Search/Selection**
   - Create player database
   - Add search functionality
   - Auto-populate from game rosters

4. **Advanced Analytics**
   - Opponent-specific performance
   - Minutes-based projections
   - Injury/rest day indicators

## 💡 Tips

- **Use Hitrates**: Higher hitrates indicate better value
- **Check Home/Away**: Some players perform differently by venue
- **Review Chart**: Visual patterns can reveal trends
- **Compare Lines**: Try different alt lines to find best value
- **Filter by Period**: Recent games (L3, L6) may be more relevant

## 🆘 Troubleshooting

**No games showing?**
- Fetch odds data first: `python workers/fetch_odds.py`
- Check date range in sidebar

**Chart not updating?**
- Click on different stat tabs to refresh
- Change prop category or alt line

**Mock data only?**
- This is expected until player stats API is integrated
- Structure is ready for real data integration

Enjoy your professional player props analytics dashboard! 🎯

