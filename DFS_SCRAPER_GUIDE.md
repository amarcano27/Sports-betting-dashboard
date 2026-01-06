# DFS Lines Scraper Guide (PrizePicks & Underdog)

## ⚠️ Important Warnings

**Before using this scraper, please read:**

1. **Terms of Service**: Web scraping may violate PrizePicks/Underdog's Terms of Service. Use at your own risk.
2. **Rate Limiting**: The scraper includes delays and rate limiting to avoid bans, but there's no guarantee.
3. **Legal Risks**: Scraping may have legal implications. Consult legal counsel if unsure.
4. **Fragile**: Website structure changes will break the scraper. It needs regular maintenance.

## 🛡️ Safety Features

The scraper includes:
- **User-agent rotation** to avoid detection
- **Random delays** between requests (5-10 seconds)
- **Anti-detection Chrome options** (removes webdriver flags)
- **Error handling** to prevent crashes
- **Rate limiting** to avoid overwhelming servers

## 📋 Prerequisites

1. **Install Selenium and ChromeDriver:**
   ```bash
   pip install selenium
   ```

2. **Install ChromeDriver:**
   - Download from: https://chromedriver.chromium.org/
   - Or use: `pip install webdriver-manager` (auto-downloads)

3. **Create database table:**
   ```sql
   -- Run schema_dfs_lines.sql in Supabase SQL Editor
   ```

## 🔐 Setup Credentials

Add to your `.env` file:

```env
PRIZEPICKS_EMAIL=your_email@example.com
PRIZEPICKS_PASSWORD=your_password
UNDERDOG_EMAIL=your_email@example.com
UNDERDOG_PASSWORD=your_password
```

**⚠️ Security Note:** Never commit `.env` to version control!

## 🚀 Usage

### Basic Usage

```bash
cd sports-betting-dashboard
.\venv\Scripts\activate
python workers/scrape_dfs_lines.py
```

### What It Does

1. Opens Chrome browser (visible, for login)
2. Logs into PrizePicks (if credentials provided)
3. Scrapes player props (player name, prop type, line)
4. Logs into Underdog (if credentials provided)
5. Scrapes player props
6. Matches players to database
7. Stores lines in `dfs_lines` table

### Expected Output

```
Navigating to PrizePicks...
Looking for player props...
Scraped 45 props from PrizePicks
Loading players for matching...
Stored 42 DFS lines, skipped 3 (player not found)

Navigating to Underdog Fantasy...
Looking for player props...
Scraped 38 props from Underdog
Stored 35 DFS lines, skipped 3 (player not found)

Total props scraped: 83
```

## 🔧 Customization

### Adjust Scraping Selectors

The scraper uses CSS selectors to find elements. If PrizePicks/Underdog change their HTML structure, update these in `scrape_dfs_lines.py`:

```python
# PrizePicks selectors (adjust as needed)
prop_cards = driver.find_elements(By.CSS_SELECTOR, "[class*='prop']")
player_name = card.find_element(By.CSS_SELECTOR, "[class*='player']").text
```

### Adjust Rate Limiting

Modify delays in the scraper:

```python
time.sleep(random.uniform(5, 10))  # Random delay between 5-10 seconds
```

### Headless Mode

Change `headless=False` to `headless=True` to run in background (but login may be harder):

```python
driver = setup_driver(headless=True)
```

## 📊 Using Scraped Data

Once scraped, DFS lines are stored in the `dfs_lines` table. You can:

1. **Query in dashboard:**
   ```python
   from services.db import supabase
   dfs_lines = supabase.table("dfs_lines").select("*").eq("source", "prizepicks").execute().data
   ```

2. **Compare to book lines:**
   - Book line: 4.5 rebounds
   - PrizePicks line: 5.5 rebounds
   - Difference: +1.0

3. **Display in slip generator:**
   - The slip generator already uses DFS-adjusted lines
   - Scraped lines can replace heuristic adjustments

## 🐛 Troubleshooting

### "ChromeDriver not found"
- Install ChromeDriver: https://chromedriver.chromium.org/
- Or use `webdriver-manager`: `pip install webdriver-manager`

### "Login failed"
- Check credentials in `.env`
- Try logging in manually first to ensure account works
- Check for CAPTCHA (may need manual intervention)

### "No props found"
- Website structure may have changed
- Inspect HTML and update selectors
- Check if site requires JavaScript (Selenium handles this)

### "Player not found"
- Ensure players are synced: `python workers/fetch_player_stats.py --sync-players`
- Check player name matching (fuzzy matching threshold is 85%)

## 🔄 Automation

### Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (e.g., daily at 9 AM)
4. Action: Start a program
5. Program: `python`
6. Arguments: `workers/scrape_dfs_lines.py`
7. Start in: `D:\Model2025\sports-betting-dashboard`

### Cron (Linux/Mac)

```bash
# Run daily at 9 AM
0 9 * * * cd /path/to/sports-betting-dashboard && /path/to/venv/bin/python workers/scrape_dfs_lines.py
```

## 📝 Notes

- **First run:** May need to manually complete login/CAPTCHA
- **Subsequent runs:** May stay logged in (cookies)
- **Rate limiting:** Don't run too frequently (once per day recommended)
- **Maintenance:** Check selectors monthly or when site changes

## 🎯 Alternative: Official APIs

Consider checking if PrizePicks/Underdog offer:
- Partner APIs
- Affiliate programs
- Official data feeds

These would be more reliable and legal than scraping.

