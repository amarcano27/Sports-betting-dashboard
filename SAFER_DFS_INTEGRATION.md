# Safer Approaches to Get PrizePicks & Underdog Lines

## 🛡️ Why Avoid Web Scraping?

- **Legal risks**: May violate Terms of Service
- **Account bans**: Can result in permanent account suspension
- **Fragile**: Breaks when websites change structure
- **Unreliable**: Rate limiting, CAPTCHAs, IP blocks
- **Ethical concerns**: Unauthorized data access

## ✅ Recommended Safer Approaches

### Option 1: Third-Party Aggregation APIs (Best Option)

These services legally aggregate data from multiple sources, including PrizePicks and Underdog.

#### **DailyFantasyAPI.io** ⭐⭐⭐ Most Popular
- **URL**: https://www.dailyfantasyapi.io
- **Features**: 
  - PrizePicks AND Underdog in one API
  - Real-time player props
  - Most mentioned solution in developer communities
- **Cost**: Check pricing
- **Setup**: Requires API key
- **Legal**: ✅ Official API service
- **Why recommended**: Most developers use this

#### **OpticOdds API** ⭐
- **URL**: https://opticodds.com/sportsbooks/prizepicks-api
- **Features**: 
  - Real-time PrizePicks odds
  - Player props, alternate markets
  - Historical data
- **Cost**: Check pricing (typically $50-200/month)
- **Setup**: Requires API key
- **Legal**: ✅ Official partnership/aggregation

#### **WagerAPI**
- **URL**: https://wagerapi.com
- **Features**: 
  - Aggregates DFS operators (PrizePicks, Underdog)
  - Player props across multiple platforms
- **Cost**: Contact for pricing (enterprise-focused)
- **Legal**: ✅ Official data service

#### **Odds-API.io**
- **URL**: https://odds-api.io/sportsbooks/underdog
- **Features**: 
  - Underdog Fantasy data
  - Pre-match and live odds
  - Player props
- **Cost**: Check pricing
- **Legal**: ✅ Official API service

**Implementation**: See `services/dfs_api.py` (created below)

---

### Option 2: Manual Entry (Free, User-Controlled)

Allow users to manually enter DFS lines they see on PrizePicks/Underdog.

**Pros:**
- ✅ 100% legal and safe
- ✅ No API costs
- ✅ User controls data entry
- ✅ No risk of bans

**Cons:**
- ⚠️ Requires manual work
- ⚠️ Not automated

**Implementation**: See `dashboard/manual_dfs_entry.py` (created below)

---

### Option 3: Browser Extension (User-Initiated)

A browser extension that users install and activate to extract lines from PrizePicks/Underdog pages they visit.

**Pros:**
- ✅ User-initiated (more ethical)
- ✅ No server-side scraping
- ✅ User controls when/where to extract
- ✅ Lower risk of bans

**Cons:**
- ⚠️ Requires extension development
- ⚠️ Users must install extension
- ⚠️ Still may violate ToS (but user-initiated is safer)

**Implementation**: See `browser_extension/` folder (future implementation)

---

### Option 4: Data Aggregation Platforms (Read-Only)

Use platforms that already integrate with PrizePicks/Underdog:

- **Outlier**: https://help.outlier.bet (integrates with PrizePicks/Underdog)
- **Props Made Easy**: https://www.propsmadeeasy.com
- **Stokastic**: https://www.stokastic.com

**Note**: These are typically read-only platforms, not APIs you can integrate.

---

## 🚀 Recommended Implementation Plan

### Phase 1: Manual Entry (Immediate)
1. Create manual entry interface
2. Users enter lines they see on PrizePicks/Underdog
3. Store in `dfs_lines` table
4. **Zero risk, immediate implementation**

### Phase 2: Third-Party API (If Budget Allows)
1. **Start with DailyFantasyAPI.io** (most popular in developer communities)
2. Or sign up for OpticOdds, WagerAPI, or Odds-API.io
3. Add API key to `.env`
4. Run `python workers/fetch_dfs_lines_api.py`
5. **Legal, reliable, automated**

### Phase 3: Browser Extension (Optional)
1. Develop Chrome/Firefox extension
2. User clicks extension to extract current page data
3. Sends to your dashboard
4. **User-controlled, lower risk**

---

## 💰 Cost Comparison

| Method | Cost | Risk | Automation |
|--------|------|------|------------|
| **Manual Entry** | Free | None | Manual |
| **OpticOdds API** | ~$50-200/mo | None | Full |
| **WagerAPI** | Contact | None | Full |
| **Browser Extension** | Free | Low | Semi |
| **Web Scraping** | Free | High | Full |

---

## 📋 Next Steps

1. **Start with Manual Entry** (implemented below)
2. **Evaluate API costs** (OpticOdds/WagerAPI)
3. **Test API integration** if budget allows
4. **Consider browser extension** for advanced users

---

## ⚖️ Legal Disclaimer

- Always review Terms of Service before accessing data
- Third-party APIs are the safest legal option
- Manual entry is always safe
- Web scraping may violate ToS and have legal implications
- Consult legal counsel if unsure

