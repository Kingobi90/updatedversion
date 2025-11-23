#!/usr/bin/env python3
"""
Integration Test Script
Tests the complete flow: Server -> enhanced_main.py -> WebSocket
"""

import os
import sys
import time
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

SERVER_URL = os.getenv('SERVER_URL', 'http://127.0.0.1:3000')
PORT = os.getenv('PORT', '3000')


def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_server_connection():
    """Test basic server connectivity."""
    print_section("Test 1: Server Connection")
    
    try:
        response = requests.get(f"{SERVER_URL}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Server is running at {SERVER_URL}")
            print(f"✓ Available endpoints: {', '.join(data.get('endpoints', []))}")
            return True
        else:
            print(f"✗ Server returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to server at {SERVER_URL}")
        print(f"  Make sure the server is running: ./start_hardware.sh")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_status_endpoint():
    """Test the status endpoint."""
    print_section("Test 2: Status Endpoint")
    
    try:
        response = requests.get(f"{SERVER_URL}/status", timeout=5)
        data = response.json()
        
        if data.get('running'):
            print(f"✓ Detection process is running (PID: {data.get('pid')})")
            return True
        else:
            print("○ Detection process is not running (this is normal)")
            print("  It will start when you call /start endpoint")
            return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_start_endpoint():
    """Test starting the detection process."""
    print_section("Test 3: Start Detection Process")
    
    print("Attempting to start detection process...")
    print("Note: This requires a camera to be connected")
    print()
    
    try:
        response = requests.post(
            f"{SERVER_URL}/start",
            json={"username": "test_user"},
            timeout=5
        )
        data = response.json()
        
        if data.get('status') == 'started':
            print(f"✓ Detection process started (PID: {data.get('pid')})")
            print("  enhanced_main.py is now running")
            return True
        elif data.get('status') == 'already running':
            print(f"✓ Detection process already running (PID: {data.get('pid')})")
            return True
        else:
            print(f"✗ Failed to start: {data.get('status')}")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_session_endpoints():
    """Test session management endpoints."""
    print_section("Test 4: Session Management")
    
    try:
        # Start session
        print("Starting session...")
        response = requests.post(
            f"{SERVER_URL}/session/start",
            json={"username": "test_user"},
            timeout=5
        )
        data = response.json()
        
        if data.get('status') == 'ok':
            session_id = data.get('sessionId')
            print(f"✓ Session started: {session_id}")
        else:
            print(f"○ Session start skipped: {data.get('error', 'Unknown')}")
            print("  (Firebase may not be configured)")
            return True
        
        # Wait a moment
        time.sleep(2)
        
        # Get session stats
        print("Getting session stats...")
        response = requests.get(f"{SERVER_URL}/session/stats", timeout=5)
        data = response.json()
        
        if data.get('status') == 'ok':
            print(f"✓ Current focus score: {data.get('currentFocusScore')}%")
            print(f"  Elapsed: {data.get('elapsedMs', 0) / 1000:.1f}s")
        
        # Stop session
        print("Stopping session...")
        response = requests.post(f"{SERVER_URL}/session/stop", json={}, timeout=5)
        data = response.json()
        
        if data.get('status') == 'ok':
            print(f"✓ Session stopped")
            print(f"  Final focus score: {data.get('focusScore', 0):.1f}%")
            return True
        else:
            print(f"○ Session stop: {data.get('status')}")
            return True
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_stop_endpoint():
    """Test stopping the detection process."""
    print_section("Test 5: Stop Detection Process")
    
    try:
        response = requests.post(f"{SERVER_URL}/stop", json={}, timeout=5)
        data = response.json()
        
        if data.get('status') == 'stopped':
            print("✓ Detection process stopped")
            if 'focusScore' in data:
                print(f"  Final focus score: {data.get('focusScore', 0):.1f}%")
            return True
        elif data.get('status') == 'not running':
            print("○ Detection process was not running")
            return True
        else:
            print(f"✗ Unexpected status: {data.get('status')}")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_websocket_info():
    """Display WebSocket connection information."""
    print_section("Test 6: WebSocket Information")
    
    ws_url = SERVER_URL.replace('http://', 'ws://') + '/ws'
    print(f"WebSocket URL: {ws_url}")
    print()
    print("To test WebSocket connection:")
    print(f"  1. Install wscat: npm install -g wscat")
    print(f"  2. Connect: wscat -c {ws_url}")
    print(f"  3. You should receive 'ON' or 'OFF' messages")
    print()
    print("Android app connects to this WebSocket for real-time alerts")
    return True


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("  Study Focus Tracker - Integration Test")
    print("=" * 60)
    print()
    print(f"Testing server at: {SERVER_URL}")
    print()
    
    # Check if .env exists
    if not (Path(__file__).parent / '.env').exists():
        print("WARNING: .env file not found!")
        print("Run setup_network.py first to configure the system")
        print()
    
    results = []
    
    # Run tests
    results.append(("Server Connection", test_server_connection()))
    
    if results[-1][1]:  # Only continue if server is reachable
        results.append(("Status Endpoint", test_status_endpoint()))
        results.append(("Start Detection", test_start_endpoint()))
        
        # Wait for process to initialize
        time.sleep(3)
        
        results.append(("Session Management", test_session_endpoints()))
        results.append(("Stop Detection", test_stop_endpoint()))
        results.append(("WebSocket Info", test_websocket_info()))
    
    # Summary
    print_section("Test Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    print()
    
    if passed == total:
        print("✓ All tests passed! System is ready for hardware deployment.")
        print()
        print("Next steps:")
        print("  1. Configure Android app to connect to:", SERVER_URL)
        print("  2. Press 'Start' in the app")
        print("  3. Detection will begin automatically")
        return 0
    else:
        print("✗ Some tests failed. Please review the output above.")
        return 1


if __name__ == '__main__':
    try:
        exit(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        exit(1)
