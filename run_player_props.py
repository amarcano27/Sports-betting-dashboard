"""
Quick launcher for Player Props Dashboard
Run this instead of dashboard/app.py to access the player props view
"""
import subprocess
import sys
from pathlib import Path

dashboard_dir = Path(__file__).parent / "dashboard"
player_props_file = dashboard_dir / "player_props_page.py"

if __name__ == "__main__":
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(player_props_file)])

