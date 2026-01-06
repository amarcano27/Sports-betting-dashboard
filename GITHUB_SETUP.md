# Setting Up GitHub Repository

## Step-by-Step Guide

### 1. Initialize Git Repository (Already Done)
```bash
cd D:\Model2025\sports-betting-dashboard
git init
```

### 2. Add Files to Git
```bash
git add .
```

### 3. Create Initial Commit
```bash
git commit -m "Initial commit: Sports Betting Analytics Platform"
```

### 4. Create GitHub Repository

**Option A: Using GitHub Website**
1. Go to https://github.com/new
2. Repository name: `sports-betting-dashboard` (or your preferred name)
3. Description: "A production-ready sports betting analytics platform with real-time odds aggregation, ML-powered projections, and AI insights"
4. Choose Public or Private
5. **DO NOT** initialize with README, .gitignore, or license (we already have these)
6. Click "Create repository"

**Option B: Using GitHub CLI (if installed)**
```bash
gh repo create sports-betting-dashboard --public --description "Sports Betting Analytics Platform"
```

### 5. Connect Local Repository to GitHub

After creating the repo on GitHub, you'll see instructions. Use these commands:

```bash
git remote add origin https://github.com/amarcano27/sports-betting-dashboard.git
git branch -M main
git push -u origin main
```

### 6. Verify

Visit your repository:
```
https://github.com/amarcano27/sports-betting-dashboard
```

## What Gets Committed

✅ **Included:**
- All Python source code
- Dashboard files
- Documentation (README, guides)
- Configuration files
- Requirements.txt
- Schema files

❌ **Excluded (via .gitignore):**
- Virtual environment (venv/)
- Environment variables (.env)
- Cache files (__pycache__/)
- IDE settings
- Log files
- Sensitive credentials

## Important Notes

### Before Pushing:

1. **Check for sensitive data:**
   - Make sure `.env` is in `.gitignore` (it is)
   - Remove any API keys from code
   - Check for hardcoded credentials

2. **Update README.md:**
   - Add setup instructions
   - Include API key requirements
   - Add screenshots/demo links

3. **Consider adding:**
   - LICENSE file
   - CONTRIBUTING.md (if open source)
   - .github/workflows (for CI/CD)

## Quick Commands Reference

```bash
# Check status
git status

# Add all files
git add .

# Commit changes
git commit -m "Your commit message"

# Push to GitHub
git push origin main

# View remote
git remote -v

# Pull latest changes
git pull origin main
```

## Troubleshooting

### If you need to remove sensitive data:
```bash
# Remove file from git history (use carefully!)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all
```

### If you need to update .gitignore:
```bash
# Remove cached files
git rm -r --cached .
git add .
git commit -m "Update .gitignore"
```

## Next Steps After Setup

1. Add repository description on GitHub
2. Add topics/tags (e.g., `python`, `streamlit`, `sports-betting`, `machine-learning`)
3. Enable GitHub Pages (if you want to host portfolio)
4. Add screenshots to README
5. Create releases for major versions

---

**Your repository will be live at:**
`https://github.com/amarcano27/sports-betting-dashboard`

