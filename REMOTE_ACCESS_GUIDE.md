# Sports Betting Dashboard - Remote Access & Auto-Refresh Guide

## 🌐 Remote Access Setup

### Option 1: Local Network Access (Recommended)

1. **Start the dashboard with remote access:**
   ```bash
   # Windows
   start_remote.bat
   
   # Linux/Mac
   ./start_remote.sh
   ```

2. **Find your computer's IP address:**
   - **Windows**: Open Command Prompt, run `ipconfig`, look for "IPv4 Address"
   - **Linux/Mac**: Run `ifconfig` or `ip addr`, look for your network interface IP
   - Example: `192.168.1.100`

3. **Access from another device:**
   - Make sure both devices are on the same Wi-Fi/network
   - Open browser on your phone/tablet/other computer
   - Go to: `http://YOUR_IP:8501`
   - Example: `http://192.168.1.100:8501`

### Option 2: Internet Access (Advanced)

For access from anywhere (not just local network):

#### Using ngrok (Easiest):
1. Install ngrok: https://ngrok.com/download
2. Start your dashboard normally
3. In a new terminal, run: `ngrok http 8501`
4. Use the ngrok URL (e.g., `https://abc123.ngrok.io`) on any device

#### Using Port Forwarding:
1. Configure your router to forward port 8501 to your computer
2. Find your public IP: https://whatismyipaddress.com
3. Access via: `http://YOUR_PUBLIC_IP:8501`
4. **Security Note**: Consider adding authentication for internet access

### Option 3: Cloud Deployment (Best for Production)

Deploy to:
- **Streamlit Cloud** (free): https://streamlit.io/cloud
- **Railway**: https://railway.app
- **Heroku**: https://heroku.com
- **AWS/GCP/Azure**: For enterprise scale

---

## ⏰ Automatic Refresh Schedule

### Recommended Schedule: **Every 4 Hours**

**Times:**
- 8:00 AM
- 12:00 PM (Noon)
- 4:00 PM
- 8:00 PM

**Total:** ~4 refreshes/day = ~120 refreshes/month

### API Usage Calculation:

**Per Refresh:**
- The Odds API: 7 calls (6 sports + Esports)
- PandaScore: ~3 calls (esports matches)
- **Total per refresh: ~10 API calls**

**Monthly:**
- 120 refreshes × 10 calls = **1,200 API calls/month**
- Well within free tier limits (typically 500-1000/month for The Odds API)

### Starting the Auto-Refresh Scheduler:

```bash
# Windows
python scheduler.py

# Or run in background:
start /B python scheduler.py

# Linux/Mac
python scheduler.py &

# Or use nohup to keep running after terminal closes:
nohup python scheduler.py > scheduler.log 2>&1 &
```

### Windows Task Scheduler (Alternative):

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: Daily at 8:00 AM, repeat every 4 hours
4. Action: Start program
   - Program: `python`
   - Arguments: `scheduler.py`
   - Start in: `D:\Model2025\sports-betting-dashboard`

### Adjusting Refresh Frequency:

Edit `scheduler.py` and modify the schedule:

```python
# More frequent (every 2 hours) - uses more API calls
schedule.every(2).hours.do(refresh_all_data)

# Less frequent (every 6 hours) - saves API calls
schedule.every(6).hours.do(refresh_all_data)

# Custom times
schedule.every().day.at("09:00").do(refresh_all_data)
schedule.every().day.at("15:00").do(refresh_all_data)
schedule.every().day.at("21:00").do(refresh_all_data)
```

---

## 🔒 Security Considerations

### For Local Network Access:
- ✅ Safe - only accessible on your Wi-Fi
- ✅ No internet exposure
- ✅ Fast and reliable

### For Internet Access:
- ⚠️ Add authentication (Streamlit has built-in password protection)
- ⚠️ Use HTTPS (consider reverse proxy like nginx)
- ⚠️ Firewall rules to limit access
- ⚠️ Monitor for unauthorized access

### Adding Password Protection:

Create `.streamlit/secrets.toml`:
```toml
[server]
enableXsrfProtection = true

# Add basic auth (requires streamlit-authenticator)
```

Or use environment variables for API keys (already implemented).

---

## 📱 Mobile Access Tips

1. **Bookmark the URL** on your phone's browser
2. **Add to Home Screen** (iOS/Android) for app-like experience
3. **Use responsive design** - dashboard is mobile-friendly
4. **Keep computer running** - dashboard needs to be active

---

## 🐛 Troubleshooting

### Can't access from other device:
1. Check firewall - allow port 8501
2. Verify both devices on same network
3. Check IP address is correct
4. Try disabling Windows Firewall temporarily to test

### Scheduler not running:
1. Check Python path is correct
2. Verify `schedule` library installed: `pip install schedule`
3. Check logs for errors
4. Run manually first to test: `python scheduler.py`

### API limits exceeded:
1. Reduce refresh frequency in `scheduler.py`
2. Check API dashboard for usage
3. Consider upgrading API tier if needed

---

## 📊 Monitoring

Check scheduler logs:
- Console output (if running in foreground)
- `scheduler.log` (if using nohup)
- Windows Event Viewer (if using Task Scheduler)

Monitor API usage:
- The Odds API dashboard
- PandaScore dashboard

