#!/bin/bash
# Start Sports Betting Dashboard with Remote Access (Linux/Mac)

echo "Starting Sports Betting Dashboard..."
echo ""
echo "Dashboard will be accessible at:"
echo "  - Local: http://localhost:8501"
echo "  - Network: http://YOUR_IP:8501"
echo ""
echo "To find your IP address, run: ifconfig (Linux) or ipconfig (Mac)"
echo ""

cd "$(dirname "$0")"
source venv/bin/activate
streamlit run dashboard/main.py --server.address 0.0.0.0 --server.port 8501

