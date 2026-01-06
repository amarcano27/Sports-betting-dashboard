# Push Sports Betting Dashboard to GitHub
# Run this script after creating the repository on GitHub

Write-Host "🚀 GitHub Repository Setup" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan
Write-Host ""

# Check if git remote already exists
$remoteExists = git remote -v 2>&1
if ($remoteExists -match "origin") {
    Write-Host "⚠️  Remote 'origin' already exists!" -ForegroundColor Yellow
    Write-Host "Current remotes:" -ForegroundColor Yellow
    git remote -v
    Write-Host ""
    $overwrite = Read-Host "Do you want to update it? (y/n)"
    if ($overwrite -eq "y") {
        git remote remove origin
    } else {
        Write-Host "Exiting. Update remote manually if needed." -ForegroundColor Yellow
        exit
    }
}

Write-Host "📝 Step 1: Create repository on GitHub" -ForegroundColor Green
Write-Host "   Go to: https://github.com/new" -ForegroundColor White
Write-Host "   Repository name: sports-betting-dashboard" -ForegroundColor White
Write-Host "   Description: Sports Betting Analytics Platform" -ForegroundColor White
Write-Host "   Choose Public or Private" -ForegroundColor White
Write-Host "   DO NOT initialize with README, .gitignore, or license" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Enter after creating the repository on GitHub..." -ForegroundColor Cyan
Read-Host

Write-Host ""
Write-Host "📝 Step 2: Enter your GitHub username" -ForegroundColor Green
$username = Read-Host "GitHub username (default: amarcano27)"

if ([string]::IsNullOrWhiteSpace($username)) {
    $username = "amarcano27"
}

Write-Host ""
Write-Host "📝 Step 3: Enter repository name" -ForegroundColor Green
$repoName = Read-Host "Repository name (default: sports-betting-dashboard)"

if ([string]::IsNullOrWhiteSpace($repoName)) {
    $repoName = "sports-betting-dashboard"
}

$repoUrl = "https://github.com/$username/$repoName.git"

Write-Host ""
Write-Host "🔗 Adding remote repository..." -ForegroundColor Yellow
Write-Host "   URL: $repoUrl" -ForegroundColor White

git remote add origin $repoUrl

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Remote added successfully!" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to add remote" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🌿 Setting default branch to 'main'..." -ForegroundColor Yellow
git branch -M main

Write-Host ""
Write-Host "📤 Pushing to GitHub..." -ForegroundColor Yellow
Write-Host "   This may take a moment..." -ForegroundColor White

git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Successfully pushed to GitHub!" -ForegroundColor Green
    Write-Host ""
    Write-Host "🎉 Your repository is now live at:" -ForegroundColor Cyan
    Write-Host "   https://github.com/$username/$repoName" -ForegroundColor White
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Add repository description on GitHub" -ForegroundColor White
    Write-Host "  2. Add topics: python, streamlit, sports-betting, machine-learning" -ForegroundColor White
    Write-Host "  3. Add screenshots to README" -ForegroundColor White
    Write-Host "  4. Update portfolio link to GitHub repo" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "❌ Failed to push. Check your GitHub credentials." -ForegroundColor Red
    Write-Host "   You may need to:" -ForegroundColor Yellow
    Write-Host "   1. Set up GitHub authentication" -ForegroundColor White
    Write-Host "   2. Use GitHub CLI: gh auth login" -ForegroundColor White
    Write-Host "   3. Or use SSH instead of HTTPS" -ForegroundColor White
}

