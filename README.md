# Sports Betting Analytics Platform

A comprehensive, production-ready sports betting analytics platform that aggregates real-time odds, calculates expected value (EV), generates ML-powered player projections, and provides AI-driven betting insights.

## 🎯 Key Features

- **Real-Time Odds Aggregation** - Multi-sportsbook odds comparison
- **ML-Powered Projections** - Custom player performance models
- **Expected Value Analysis** - Automated edge identification
- **AI-Powered Insights** - Context-aware recommendations
- **Premium UI/UX** - Million-dollar design with animations
- **Multi-Sport Support** - NBA, NFL, MLB, NHL, NCAAB, NCAAF, Esports
- **Demo Mode** - Works without API keys for portfolio showcase

## ⚠️ API Keys Required

**This platform integrates with live APIs and requires your own API keys for full functionality.**

The platform includes a **demo mode** that works without API keys, perfect for portfolio demonstration. For production use, you'll need:

- **The Odds API** - Real-time odds aggregation from multiple sportsbooks
- **Supabase** - PostgreSQL database for data storage
- **NBA Stats API** - Player statistics and historical performance
- **PandaScore API** - Esports data (CS2, LoL, Dota2, Valorant) - optional

**Note**: This platform was originally developed with active API subscriptions. For your own use, you'll need to obtain your own API keys from the respective providers.

See `API_SETUP.md` for detailed setup instructions.

## 🎯 Portfolio Highlights

This project demonstrates:

- **Full-Stack Development**: Python backend, Streamlit frontend, PostgreSQL database
- **API Integration**: Multiple real-time data sources with error handling
- **Machine Learning**: Custom projection models and statistical analysis
- **Data Engineering**: ETL pipelines, data validation, caching strategies
- **Production Practices**: Error handling, fallback systems, demo mode
- **Modern UI/UX**: Premium design with animations and responsive layout

See `PORTFOLIO_FEATURES.md` for a comprehensive overview of features and technical highlights.

## Setup Instructions

### 1. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Edit the `.env` file with your actual API keys:

```
ODDS_API_KEY=your_theoddsapi_key_here
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_KEY=your_supabase_anon_or_service_role_key
```

### 4. Set Up Database

Run the SQL schema in your Supabase SQL editor:

```bash
# The schema is in schema.sql
```

Or execute the SQL commands from `schema.sql` in your Supabase dashboard.

### 5. Run the Dashboard

```bash
streamlit run dashboard/app.py
```

## Project Structure

```
sports-betting-dashboard/
├── .env
├── requirements.txt
├── schema.sql
├── services/
│   ├── db.py          # Supabase client setup
│   └── odds_api.py    # The Odds API integration
├── workers/
│   ├── fetch_odds.py  # Fetches and stores odds data
│   ├── calc_ev.py     # Calculates expected value
│   └── generate_slip.py # Generates betting slips
├── utils/
│   └── ev.py          # EV calculation utilities
└── dashboard/
    └── app.py         # Streamlit dashboard
```

## Cron Jobs (Optional)

To automate data fetching, set up cron jobs:

```bash
# Fetch odds every 15 minutes
*/15 * * * * /path/to/venv/bin/python /path/to/project/workers/fetch_odds.py

# Generate slips every hour
0 * * * * /path/to/venv/bin/python /path/to/project/workers/generate_slip.py
```

On Windows, use Task Scheduler instead of cron.

## Usage

1. **Fetch Odds**: Run `python workers/fetch_odds.py` to fetch and store current odds
2. **Calculate EV**: Run `python workers/calc_ev.py` to see expected value calculations
3. **Generate Slips**: Run `python workers/generate_slip.py` to create AI suggestions
4. **View Dashboard**: Run `streamlit run dashboard/app.py` to see the web interface

## Notes

- Make sure your Supabase project has the `pgcrypto` extension enabled
- The Odds API has rate limits - check your plan
- Update the `.env` file with your actual credentials before running

