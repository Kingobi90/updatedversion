#!/bin/bash

echo "=== Testing Python Server Connection ==="
echo ""
echo "1. Testing server status..."
curl -s http://127.0.0.1:3000/status | python3 -m json.tool
echo ""

echo "2. Testing /start endpoint..."
curl -s -X POST http://127.0.0.1:3000/start -H "Content-Type: application/json" -d '{"username":"test"}' | python3 -m json.tool
echo ""

echo "3. Testing /session/start endpoint..."
curl -s -X POST http://127.0.0.1:3000/session/start -H "Content-Type: application/json" -d '{"username":"test"}' | python3 -m json.tool
echo ""

echo "4. Testing /session/stats endpoint..."
curl -s http://127.0.0.1:3000/session/stats | python3 -m json.tool
echo ""

echo "=== Server is working! ==="
echo ""
echo "Now test from Android app:"
echo "1. Login to the app"
echo "2. Go to 'Untimed Session' tab"
echo "3. Click 'Start Untimed Session'"
echo ""
echo "Watch the server logs for incoming requests..."
