@echo off
cd /d "%~dp0"
echo Starting Sports Betting Dashboard...
echo.
call venv\Scripts\activate.bat

echo Starting Auto-Refresh Scheduler...
start "Dashboard Scheduler" /MIN python scheduler.py

echo Starting Streamlit...
streamlit run dashboard/main.py
pause
