# Dashboard User Guide

## 🎯 Overview

The Sports Betting Analytics Dashboard is a comprehensive tool for analyzing betting odds, building custom parlays, and discovering profitable betting opportunities.

## 🚀 Quick Start

1. **Start the Dashboard:**
   ```bash
   cd sports-betting-dashboard
   .\venv\Scripts\Activate.ps1
   streamlit run dashboard/app.py
   ```

2. **The dashboard will open in your browser** (usually at http://localhost:8501)

## 📊 Dashboard Features

### 1. Overview Tab
- **Key Metrics**: See at-a-glance statistics about upcoming games and available odds
- **Game Cards**: Browse all upcoming games with expandable odds details
- **Organized by Market**: View Moneyline, Spreads, and Totals separately for each game

### 2. Parlay Builder Tab
- **Build Custom Parlays**: Select bets from available games to create your own parlay
- **Real-time Calculations**: See combined odds, implied probability, and potential payouts
- **Payout Calculator**: Enter your bet amount to see potential profit
- **Easy Management**: Add/remove legs with one click

### 3. Smart Suggestions Tab
- **Value Bets**: Automatically identifies positive Expected Value (EV) bets
- **Pairing Suggestions**: AI-powered recommendations for 2-leg and 3-leg parlays
- **EV Rankings**: Bets sorted by expected value to help you find the best opportunities

### 4. Analysis Tab
- **Data Visualizations**: Charts showing odds distribution and bookmaker coverage
- **Best Odds Finder**: Compare odds across bookmakers to find the best lines
- **Market Analysis**: Deep dive into specific games and markets

## 🎲 How to Build a Parlay

1. Navigate to the **Parlay Builder** tab
2. Browse available games and expand the game you're interested in
3. Click **"➕ Add"** next to any bet you want to include
4. Your parlay will appear in the right sidebar
5. See real-time calculations for:
   - Combined odds (American and Decimal)
   - Implied probability
   - Potential payout and profit
6. Use the payout calculator to see returns for different bet amounts

## 💡 Understanding Smart Suggestions

### Expected Value (EV)
- **Positive EV**: The bet is mathematically profitable over time
- **EV Score**: Higher is better (e.g., 0.05 = 5% edge)
- **Color Coding**: 
  - 🟢 Green = High EV (>10%)
  - 🟡 Yellow = Moderate EV (0-10%)

### Pairing Suggestions
- Combines multiple positive EV bets
- Calculates combined EV for the parlay
- Shows top 5 recommended combinations
- Sorted by highest combined EV

## 📈 Tips for Best Results

1. **Keep Data Fresh**: Run `python workers/fetch_odds.py` regularly to get latest odds
2. **Compare Books**: Use the Best Odds Finder to shop for the best lines
3. **Focus on Positive EV**: Smart Suggestions tab highlights value bets
4. **Start Small**: Test your parlays with small bet amounts first
5. **Review Analysis**: Check the Analysis tab to understand market trends

## 🔄 Data Refresh

The dashboard caches data for 5 minutes to improve performance. To refresh:
- Click the **"🔄 Refresh Data"** button in the sidebar
- Or wait 5 minutes for automatic refresh

## 🎨 Customization

### Filters Available:
- **Sport Selection**: Choose NBA or NFL
- **Date Range**: Show games up to 14 days ahead
- **Market Types**: Filter by Moneyline, Spreads, or Totals
- **Bookmakers**: Show all books or filter by specific ones

## 📝 Notes

- The dashboard reads from your Supabase database (no new API calls)
- All calculations are done client-side for fast performance
- Player stats structure is ready for future expansion
- Data is cached to reduce database queries

## 🆘 Troubleshooting

**No games showing?**
- Make sure you've run `python workers/fetch_odds.py` to fetch data
- Check your date range filter
- Verify your sport selection

**No odds available?**
- Odds may not be available for all games
- Try refreshing the data
- Check if games are too far in the future

**Suggestions not showing?**
- Need positive EV bets in the database
- Try fetching fresh odds data
- Some markets may have limited value opportunities

## 🚀 Next Steps

1. **Fetch Fresh Data**: Run the odds fetcher regularly
2. **Explore Suggestions**: Check the Smart Suggestions tab
3. **Build Test Parlays**: Practice with the Parlay Builder
4. **Analyze Trends**: Use the Analysis tab to understand patterns

Enjoy your enhanced betting analytics dashboard! 🎯

