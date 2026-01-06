# Quick Start Guide

## 🚀 Starting the Dashboard (Remote Access)

### Windows:
```bash
start_remote.bat
```

### Linux/Mac:
```bash
./start_remote.sh
```

### Manual:
```bash
streamlit run dashboard/main.py --server.address 0.0.0.0 --server.port 8501
```

**Then access from any device on your network:**
- Find your IP: `ipconfig` (Windows) or `ifconfig` (Linux/Mac)
- Open browser: `http://YOUR_IP:8501`

---

## ⏰ Auto-Refresh Setup

### Start Scheduler:
```bash
python scheduler.py
```

**Schedule:** Every 4 hours (8 AM, 12 PM, 4 PM, 8 PM)
**API Usage:** ~120 refreshes/month (safe for free tiers)

### Windows Task Scheduler (Background):
1. Open Task Scheduler
2. Create Task → Triggers → Daily at 8:00 AM, repeat every 4 hours
3. Actions → Start program: `python` with args: `scheduler.py`
4. Start in: `D:\Model2025\sports-betting-dashboard`

---

## 📱 Mobile Access

1. Start dashboard with `start_remote.bat`
2. Find your computer's IP address
3. On your phone, open: `http://YOUR_IP:8501`
4. Bookmark it for easy access!

---

## 🔧 Troubleshooting

**Can't access from phone?**
- Check firewall allows port 8501
- Verify both devices on same Wi-Fi
- Try disabling firewall temporarily to test

**Scheduler not working?**
- Install: `pip install schedule`
- Check Python path is correct
- Run manually first: `python scheduler.py`

---

For detailed instructions, see `REMOTE_ACCESS_GUIDE.md`
