# How to Deploy Your Portfolio

This guide will help you share your portfolio website and Sports Betting Dashboard with the world!

## 🎯 Quick Overview

You have two main components:
1. **Portfolio Website** (`portfolio/` folder) - Static HTML/CSS/JS website
2. **Sports Betting Dashboard** - Streamlit application

## 📋 Step-by-Step Deployment

### Part 1: Deploy Portfolio Website

#### Option A: GitHub Pages (Recommended - Free)

1. **Create a GitHub Repository**
   ```bash
   cd portfolio
   git init
   git add .
   git commit -m "Initial portfolio commit"
   ```

2. **Push to GitHub**
   - Create a new repository on GitHub (e.g., `my-portfolio`)
   - Push your code:
   ```bash
   git remote add origin https://github.com/yourusername/my-portfolio.git
   git branch -M main
   git push -u origin main
   ```

3. **Enable GitHub Pages**
   - Go to your repository on GitHub
   - Click **Settings** → **Pages**
   - Under "Source", select **main** branch
   - Click **Save**
   - Your portfolio will be live at: `https://yourusername.github.io/my-portfolio/`

#### Option B: Netlify (Easiest - Free)

1. Go to [Netlify Drop](https://app.netlify.com/drop)
2. Drag and drop your `portfolio` folder
3. Your site is live instantly!
4. You'll get a URL like: `https://random-name-123.netlify.app`

#### Option C: Vercel (Free)

1. Install Vercel CLI: `npm i -g vercel`
2. Navigate to portfolio folder: `cd portfolio`
3. Run: `vercel`
4. Follow the prompts
5. Your site will be deployed!

### Part 2: Deploy Sports Betting Dashboard

#### Option A: Streamlit Cloud (Recommended - Free)

1. **Push Dashboard to GitHub**
   ```bash
   cd sports-betting-dashboard
   git init
   git add .
   git commit -m "Sports Betting Dashboard"
   git remote add origin https://github.com/yourusername/sports-betting-dashboard.git
   git push -u origin main
   ```

2. **Deploy on Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with GitHub
   - Click **New app**
   - Select your repository: `sports-betting-dashboard`
   - Set main file: `dashboard/main.py`
   - Click **Deploy**
   - Your dashboard will be live at: `https://your-app-name.streamlit.app`

3. **Update Portfolio Link**
   - Edit `portfolio/index.html`
   - Replace `http://localhost:8501` with your Streamlit Cloud URL

#### Option B: Heroku (Alternative)

1. Create `Procfile`:
   ```
   web: streamlit run dashboard/main.py --server.port=$PORT --server.address=0.0.0.0
   ```

2. Create `setup.sh`:
   ```bash
   mkdir -p ~/.streamlit/
   echo "[server]" > ~/.streamlit/config.toml
   echo "headless = true" >> ~/.streamlit/config.toml
   ```

3. Deploy via Heroku CLI or GitHub integration

### Part 3: Update Portfolio Links

After deploying both:

1. **Edit `portfolio/index.html`**
   - Update the "View Live Demo" button link to your Streamlit Cloud URL
   - Update GitHub repository links
   - Update contact information (email, LinkedIn, etc.)

2. **Add Screenshots** (Optional but Recommended)
   - Take screenshots of your dashboard
   - Create `portfolio/images/` folder
   - Add screenshots
   - Update the image placeholder in `index.html`:
   ```html
   <img src="images/dashboard-screenshot.png" alt="Dashboard Screenshot" style="width: 100%; border-radius: 16px;">
   ```

## 🔗 Linking Everything Together

### Portfolio → Dashboard
- Add a prominent "View Live Demo" button linking to your Streamlit app
- Include screenshots/GIFs of the dashboard
- Add a "View Code" button linking to your GitHub repository

### Dashboard → Portfolio
- Add a link in your dashboard footer/sidebar back to your portfolio
- Or mention it in the README

## 📝 Customization Checklist

Before sharing:

- [ ] Update email address in portfolio
- [ ] Update GitHub username/links
- [ ] Update LinkedIn profile link
- [ ] Update repository URLs
- [ ] Replace placeholder images with screenshots
- [ ] Update Streamlit app URL (if deployed)
- [ ] Test all links work
- [ ] Add your name/bio
- [ ] Customize colors if desired

## 🌐 Custom Domain (Optional)

### For Portfolio:
1. Buy a domain (Namecheap, Google Domains, etc.)
2. In GitHub Pages settings, add your custom domain
3. Update DNS records as instructed

### For Dashboard:
1. Streamlit Cloud supports custom domains (paid plan)
2. Or use a reverse proxy (Cloudflare, etc.)

## 📊 Analytics (Optional)

Add Google Analytics to track visitors:

1. Get Google Analytics tracking ID
2. Add to `portfolio/index.html` before `</head>`:
```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
```

## 🎨 Final Touches

1. **Add More Projects**: Expand your portfolio with other projects
2. **Add Blog Section**: Share your learning journey
3. **Add Resume**: Link to downloadable PDF resume
4. **Add Testimonials**: If you have any
5. **Optimize Images**: Compress screenshots for faster loading

## 🚀 Quick Deploy Commands

```bash
# Portfolio to GitHub Pages
cd portfolio
git init
git add .
git commit -m "Portfolio website"
git remote add origin https://github.com/yourusername/portfolio.git
git push -u origin main
# Then enable Pages in GitHub Settings

# Dashboard to Streamlit Cloud
cd sports-betting-dashboard
git init
git add .
git commit -m "Sports Betting Dashboard"
git remote add origin https://github.com/yourusername/sports-betting-dashboard.git
git push -u origin main
# Then deploy on share.streamlit.io
```

## 📞 Need Help?

- **GitHub Pages**: [docs.github.com/pages](https://docs.github.com/pages)
- **Streamlit Cloud**: [docs.streamlit.io/streamlit-cloud](https://docs.streamlit.io/streamlit-cloud)
- **Netlify**: [docs.netlify.com](https://docs.netlify.com)

---

**You're all set!** Share your portfolio URL with potential employers, clients, or collaborators. Good luck! 🎉

