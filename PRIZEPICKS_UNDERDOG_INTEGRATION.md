# PrizePicks & Underdog Integration Guide

## Overview

PrizePicks and Underdog are Daily Fantasy Sports (DFS) platforms that offer player props, but they are **not included** in The Odds API. This guide explains options for integrating their data.

## Current Situation

**The Odds API** (what you're currently using) includes traditional sportsbooks:
- BetMGM, BetOnline.ag, BetRivers, Bovada, Caesars, DraftKings, FanDuel, Fanatics

**PrizePicks & Underdog** are DFS platforms, not sportsbooks, so they're not in standard odds APIs.

## Integration Options

### Option 1: Third-Party Aggregation APIs (Recommended)

#### OpticOdds API
- **URL**: https://opticodds.com/sportsbooks/prizepicks-api
- **Features**: Real-time PrizePicks odds, player props, alternate markets
- **Setup**: Requires separate API key and subscription
- **Cost**: Check their pricing page

#### WagerAPI
- **URL**: https://wagerapi.com
- **Features**: Aggregates data from DFS operators including PrizePicks and Underdog
- **Setup**: Enterprise-focused, requires API key
- **Cost**: Contact for pricing

**Integration Steps:**
1. Sign up for OpticOdds or WagerAPI
2. Get API key
3. Create new service file: `services/prizepicks_api.py` or `services/underdog_api.py`
4. Add worker script: `workers/fetch_prizepicks_odds.py`
5. Store data in same `player_prop_odds` table with `book="PrizePicks"` or `book="Underdog"`

### Option 2: Web Scraping (Not Recommended)

⚠️ **Legal & Ethical Concerns:**
- May violate Terms of Service
- Legal risks
- Fragile (breaks when site changes)
- Rate limiting issues

If you still want to explore:
- Use libraries like `selenium` or `beautifulsoup4`
- Handle authentication, rate limiting, and parsing
- Build robust error handling

### Option 3: Manual Entry or Partner APIs

- Check if PrizePicks/Underdog offer official partner APIs
- Some platforms provide APIs for affiliates/partners
- Contact their business development team

## Implementation Example (If Using Third-Party API)

### Step 1: Create Service File

```python
# services/prizepicks_api.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

PRIZEPICKS_API_KEY = os.getenv("PRIZEPICKS_API_KEY")
PRIZEPICKS_BASE_URL = "https://api.opticodds.com/v1"  # Example

def get_prizepicks_props(sport_key="nba"):
    """Fetch PrizePicks player props"""
    url = f"{PRIZEPICKS_BASE_URL}/prizepicks/props"
    headers = {"Authorization": f"Bearer {PRIZEPICKS_API_KEY}"}
    
    params = {
        "sport": sport_key,
        "format": "american"
    }
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Error fetching PrizePicks props: {e}")
        return []
```

### Step 2: Create Worker Script

```python
# workers/fetch_prizepicks_odds.py
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.prizepicks_api import get_prizepicks_props
from services.db import supabase
from rapidfuzz import process

def store_prizepicks_odds(sport_key="nba"):
    """Fetch and store PrizePicks player prop odds"""
    print("Fetching PrizePicks player props...")
    props_data = get_prizepicks_props(sport_key)
    
    if not props_data:
        print("No PrizePicks props available")
        return
    
    # Load players for matching
    all_players = supabase.table("players").select("id,name").eq("sport", "NBA").execute().data
    player_names = {p["name"]: p["id"] for p in all_players}
    
    props_stored = 0
    
    for prop in props_data:
        # Match player, find game, store prop
        # (Similar logic to fetch_player_prop_odds.py)
        # ...
        # Store with book="PrizePicks"
        pass
    
    print(f"Stored {props_stored} PrizePicks props")
```

### Step 3: Add to Environment

```bash
# .env
PRIZEPICKS_API_KEY=your_api_key_here
```

## Recommendation

**For now:** Continue using The Odds API with the 8+ bookmakers you have. This gives you good coverage of traditional sportsbooks.

**If you need PrizePicks/Underdog specifically:**
1. Check OpticOdds or WagerAPI pricing
2. Evaluate if the cost is worth it for your use case
3. Consider that PrizePicks/Underdog lines are often similar to sportsbook lines (just presented differently)

## Notes

- PrizePicks and Underdog use a "pick 2-6 players" format, not traditional over/under
- Their lines are often the same as sportsbooks but presented as "more/less than X"
- You may already have similar lines from your current bookmakers

## Questions?

- Check The Odds API documentation: https://the-odds-api.com/liveapi/guides/v4/
- Contact OpticOdds/WagerAPI for integration support
- Consider if you really need these specific platforms or if current bookmakers suffice

