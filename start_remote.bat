@echo off
REM Start Sports Betting Dashboard with Remote Access
REM This allows access from other devices on your network

echo Starting Sports Betting Dashboard...
echo.
python show_ip.py
echo.
echo Starting server...
echo.

cd /d "%~dp0"
call venv\Scripts\activate.bat
streamlit run dashboard\main.py --server.address 0.0.0.0 --server.port 8501

pause

