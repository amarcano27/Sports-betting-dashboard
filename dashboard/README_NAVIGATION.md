# Navigation Setup

## Important: How to Run the Dashboard

**You MUST run the main router file, not individual pages:**

```bash
streamlit run dashboard/main.py
```

**DO NOT run individual pages directly:**
- ❌ `streamlit run dashboard/player_props_page.py` (this will skip navigation)
- ❌ `streamlit run dashboard/home_page.py` (this will skip navigation)
- ❌ `streamlit run dashboard/moneylines_page.py` (this will skip navigation)

## What You Should See

When you run `dashboard/main.py`, you should see:

1. **Sidebar Navigation** on the left with:
   - 🏠 Home (default page)
   - 🎯 Player Props
   - 💰 Moneylines
   - 📊 Analytics

2. **Main Content Area** showing the selected page

3. **Click any page in the sidebar** to switch between pages

## Troubleshooting

If you're seeing "Josh Hart data" or going straight to player props:

1. **Stop the current Streamlit server** (Ctrl+C in terminal)

2. **Make sure you're running the correct command:**
   ```bash
   streamlit run dashboard/main.py
   ```

3. **Check the URL** - it should be something like:
   - `http://localhost:8501/` (Home page)
   - NOT `http://localhost:8501/player_props_page` (direct page)

4. **Clear browser cache** or use an incognito window

5. **Restart Streamlit** completely

## If Navigation Still Doesn't Work

If the sidebar navigation isn't showing up, try:

1. Check your Streamlit version:
   ```bash
   streamlit --version
   ```
   Should be 1.28.0 or higher for `st.navigation()` support

2. Update Streamlit if needed:
   ```bash
   pip install --upgrade streamlit
   ```

