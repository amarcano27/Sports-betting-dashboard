# DFS Lines Integration - Implementation Plan

## 🎯 Goal
Safely get PrizePicks and Underdog lines without violating ToS or risking account bans.

## ✅ Recommended Approach: Multi-Tier Strategy

### Tier 1: Manual Entry (Start Here) ✅ IMPLEMENTED
- **Status**: ✅ Ready to use
- **File**: `dashboard/manual_dfs_entry.py`
- **Risk**: None
- **Cost**: Free
- **How**: Users manually enter lines they see on PrizePicks/Underdog
- **Next Step**: Add to navigation (already done)

### Tier 2: Third-Party APIs (If Budget Allows)
- **Status**: ✅ Code ready, needs API keys
- **Files**: 
  - `services/dfs_api.py` (API integration)
  - `workers/fetch_dfs_lines_api.py` (worker script)
- **Risk**: None (legal APIs)
- **Cost**: $50-200/month
- **Options** (in order of popularity):
  1. **DailyFantasyAPI.io** ⭐⭐⭐ - Most popular, both PrizePicks & Underdog
  2. **OpticOdds** - PrizePicks data
  3. **WagerAPI** - Both PrizePicks & Underdog
  4. **Odds-API.io** - Underdog data
- **Next Step**: 
  1. **Start with DailyFantasyAPI.io** (most mentioned in developer communities)
  2. Sign up: https://www.dailyfantasyapi.io
  3. Add API key to `.env` as `DAILYFANTASYAPI_KEY`
  4. Run `python workers/fetch_dfs_lines_api.py`

### Tier 3: Browser Extension (Future)
- **Status**: ⏳ Not implemented
- **Risk**: Low (user-initiated)
- **Cost**: Free
- **How**: Users install extension, click to extract lines from pages they visit
- **Next Step**: Develop Chrome/Firefox extension

## 🚀 Quick Start

### Option A: Manual Entry (Recommended First Step)

1. **Access the page**: Navigate to "📝 Manual DFS Entry" in the dashboard
2. **Enter lines**: 
   - Search/select player
   - Enter prop type, line, side
   - Select source (PrizePicks/Underdog)
   - Save
3. **Use in slips**: Generated slips will automatically use these lines

### Option B: Third-Party API (If You Have Budget)

1. **Sign up**: Start with DailyFantasyAPI.io (most popular):
   - DailyFantasyAPI.io: https://www.dailyfantasyapi.io ⭐ Recommended
   - Or choose: OpticOdds, WagerAPI, or Odds-API.io

2. **Get API key**: Add to `.env`:
   ```env
   DAILYFANTASYAPI_KEY=your_key_here
   # OR
   OPTICODDS_API_KEY=your_key_here
   # OR
   WAGERAPI_KEY=your_key_here
   # OR
   ODDS_API_IO_KEY=your_key_here
   ```

3. **Run worker**:
   ```bash
   python workers/fetch_dfs_lines_api.py
   ```

4. **Automate** (optional): Set up cron/Task Scheduler to run daily

## 📊 Comparison

| Method | Legal | Risk | Cost | Automation | Status |
|--------|-------|------|------|------------|--------|
| **Manual Entry** | ✅ Yes | None | Free | Manual | ✅ Ready |
| **Third-Party API** | ✅ Yes | None | $50-200/mo | Full | ✅ Ready (needs API key) |
| **Browser Extension** | ⚠️ Maybe | Low | Free | Semi | ⏳ Future |
| **Web Scraping** | ❌ No | High | Free | Full | ❌ Not recommended |

## 🎯 Recommendation

**Start with Manual Entry** - It's:
- ✅ 100% safe and legal
- ✅ Free
- ✅ Available immediately
- ✅ User-controlled

**Upgrade to API** if:
- You need automation
- You have budget ($50-200/month)
- You want real-time updates

## 📝 Notes

- All methods store data in the same `dfs_lines` table
- Slip generator automatically uses scraped/entered DFS lines
- Manual entry is always available as fallback
- API integration is plug-and-play once you have keys

