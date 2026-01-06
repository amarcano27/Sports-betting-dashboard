# Custom Projections & Line Shopping System

## 🎯 What This Does

**Generates our own player prop lines for FREE** using:
- ✅ Player historical data (free NBA Stats API)
- ✅ Matchup performance (vs specific opponents)
- ✅ Injury reports (free from NBA Stats API/ESPN)
- ✅ Opponent defense ratings (calculated from game data)
- ✅ Home/away splits
- ✅ Rest days and back-to-back games
- ✅ Recent form trends

**Then compares our lines to ALL book lines** to find the best value.

## 🚀 Quick Start

### 1. Enable Projections (Already On!)

On the **Home** page, "Show Our Projections" is enabled by default. You'll see:
- **Our Projected Line** next to each prop
- **Confidence score** (0-100%)
- **Comparison** to book lines

### 2. Use Line Shopping Tool

Go to **🛒 Line Shopping** page:
1. Select game, player, prop type
2. See our projection with full breakdown
3. Compare ALL book lines side-by-side
4. Get recommendations for best value

### 3. Keep Data Fresh (Daily)

Run these workers daily (automate with Task Scheduler):

```bash
# Fetch injuries (free from NBA Stats API/ESPN)
python workers/fetch_injuries.py

# Fetch player stats (free from NBA Stats API)
python workers/fetch_player_stats.py --all

# Fetch book lines (from The Odds API - you already have this)
python workers/fetch_player_prop_odds.py
```

## 📊 How It Works

### Our Projection Formula

```
Our Line = Baseline × Defense × Matchup × Home/Away × Injury × Rest × Pace
```

**Baseline:**
- Bovada line (if available - considered "sharp")
- OR player's recent weighted average

**Adjustments:**
- **Defense**: How opponent defends this stat (weak defense = +15%, strong = -15%)
- **Matchup**: Player's history vs this opponent
- **Home/Away**: Player performs better at home or away?
- **Injury**: Current injury impact (0-100% reduction)
- **Rest**: Back-to-back = -5%, 3+ days rest = +2%
- **Pace**: Game pace impact (future)

### Value Finding

When our line differs from book lines:
- **Our line 0.5+ higher** → Over has value
- **Our line 0.5+ lower** → Under has value
- **Large differences** → Big value opportunities

## 🛒 Line Shopping Features

### Compare All Books
- See every book's line for the same prop
- Sort by value (best opportunities first)
- See odds for both over and under

### Get Recommendations
- System highlights which side has value
- Shows best book for over
- Shows best book for under
- Calculates edge for each option

### Full Breakdown
- See all projection factors
- Understand why our line differs
- Check confidence level
- Review injury status

## 💡 Key Benefits

### ✅ 100% Free
- No paid APIs for projections
- Uses free NBA Stats API
- Uses free ESPN injury data
- Only The Odds API (you already pay for this)

### ✅ No Manual Input
- Everything automated
- Just run workers daily
- Data updates automatically

### ✅ Comprehensive
- Multiple factors considered
- Transparent calculations
- Confidence scores provided

### ✅ Line Shopping
- Compare all books at once
- Find best value automatically
- Get specific recommendations

## 📈 Example Workflow

**Morning:**
```bash
python workers/fetch_injuries.py  # Get latest injuries
```

**Afternoon:**
```bash
python workers/fetch_player_prop_odds.py  # Get book lines
```

**Evening:**
- Open **🛒 Line Shopping** page
- Find props where our line differs significantly
- Identify value opportunities

**Before Games:**
- Generate slips using our projections
- System prioritizes +EV plays
- Use line shopping to find best books

## 🎯 Tips for Best Results

1. **Keep Data Fresh**: Run workers daily
2. **Check Confidence**: Higher = more reliable
3. **Look for Differences**: 0.5+ difference = value
4. **Compare Books**: Line shopping finds best odds
5. **Review Factors**: Understand why our line differs

## 🔧 Technical Details

### Data Sources
- **NBA Stats API**: Player stats, injuries (free, public)
- **ESPN**: Injury reports (free, public)
- **The Odds API**: Book lines (you already have this)

### Database Tables
- `players` - Player info
- `player_game_stats` - Historical performance
- `player_prop_odds` - Book lines
- `player_injuries` - Injury status
- `games` - Game info

### Key Functions
- `calculate_projection()` - Main calculation
- `calculate_opponent_defense_rating()` - Defense adjustment
- `get_injury_status()` - Injury impact
- `load_all_book_lines()` - Line shopping

## 🚀 Future Enhancements

- Pace adjustment (team pace stats)
- Line movement tracking
- Historical accuracy tracking
- Weather factors (outdoor sports)
- Referee tendencies

## ❓ FAQ

**Q: Are projections accurate?**
A: They're based on comprehensive data and multiple factors. Confidence scores show reliability.

**Q: How often should I update data?**
A: Daily for injuries, daily for book lines, weekly for player stats.

**Q: Can I trust our projections?**
A: They're data-driven and transparent. Review the factors to understand each projection.

**Q: What if I don't have injury data?**
A: System still works, just without injury adjustments. Run `fetch_injuries.py` to get it.

**Q: How do I find the best value?**
A: Use the Line Shopping page - it compares our projections to all books and highlights value.

