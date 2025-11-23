#!/bin/bash
# Hardware deployment startup script for Raspberry Pi
# This script starts the Flask server which will manage the enhanced_main.py process

set -e

echo "========================================"
echo "Study Focus Tracker - Hardware Startup"
echo "========================================"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Get local IP address
LOCAL_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "✓ Device IP Address: $LOCAL_IP"
echo "✓ Server will start on: http://$LOCAL_IP:3000"
echo ""
echo "📱 Enter this IP in your Android app: $LOCAL_IP"
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Creating..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install/update dependencies
echo "Checking dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo ""
echo "========================================"
echo "Starting Flask Server..."
echo "========================================"
echo ""
echo "The server will:"
echo "  1. Listen for Android app connections"
echo "  2. Launch enhanced_main.py when /start is called"
echo "  3. Manage WebSocket connections for real-time alerts"
echo ""
echo "Android app should connect to: http://$LOCAL_IP:${PORT:-3000}"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
python -m driver_state_detection.server
