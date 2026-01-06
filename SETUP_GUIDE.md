# Setup Guide - Getting Your API Keys

## 1. The Odds API Key

### Steps:
1. Go to https://the-odds-api.com/
2. Sign up for a free account (500 requests/month free tier)
3. Navigate to your dashboard
4. Copy your API key
5. Paste it in `.env` as: `ODDS_API_KEY=your_actual_key_here`

### Note:
- Free tier: 500 requests/month
- Paid tiers available for more requests
- No credit card required for free tier

## 2. Supabase Setup

### Steps:
1. Go to https://supabase.com/
2. Sign up for a free account
3. Create a new project
4. Wait for the project to finish setting up (takes 1-2 minutes)
5. Go to **Project Settings** → **API**
6. Copy:
   - **Project URL** → Use as `SUPABASE_URL`
   - **service_role key** (secret) → Use as `SUPABASE_KEY`

### Important:
- Use the **service_role** key (not the anon key) for this project
- The service_role key bypasses Row Level Security, which is needed for the workers
- Keep this key secret - never commit it to git!

## 3. Database Schema Setup

After creating your Supabase project:

1. Go to **SQL Editor** in your Supabase dashboard
2. Click **New Query**
3. Copy and paste the entire contents of `schema.sql`
4. Click **Run** (or press Ctrl+Enter)
5. Verify tables were created by checking the **Table Editor**

You should see three tables:
- `games`
- `odds_snapshots`
- `ai_suggestions`

## 4. Update Your .env File

Once you have both keys, edit `sports-betting-dashboard/.env`:

```
ODDS_API_KEY=your_actual_odds_api_key
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your_service_role_key_here
```

**Important:** 
- No quotes around the values
- No spaces around the `=` sign
- Make sure there are no extra spaces at the end of lines

## 5. Test Your Setup

Run the connection test:
```bash
cd sports-betting-dashboard
.\venv\Scripts\Activate.ps1
python test_connection.py
```

You should see:
- `[OK] ODDS_API_KEY is set`
- `[OK] SUPABASE_URL is set`
- `[OK] SUPABASE_KEY is set`
- `[OK] Supabase connection successful`
- `[OK] The Odds API connection successful`

## Troubleshooting

### "ODDS_API_KEY not configured"
- Make sure you copied the entire key (no extra spaces)
- Check that the `.env` file is in `sports-betting-dashboard/` directory
- Try running `python check_env.py` to see what's being loaded

### "Supabase connection failed"
- Verify your SUPABASE_URL is correct (should end with `.supabase.co`)
- Make sure you're using the service_role key (not anon key)
- Check that you've run the schema.sql to create tables

### "The Odds API connection failed"
- Verify your API key is correct
- Check if you've exceeded your monthly request limit
- Make sure you have internet connection

## Next Steps

Once everything is configured:
1. **Fetch odds data**: `python workers/fetch_odds.py`
2. **Calculate EV**: `python workers/calc_ev.py`
3. **Generate slips**: `python workers/generate_slip.py`
4. **View dashboard**: `streamlit run dashboard/app.py`

