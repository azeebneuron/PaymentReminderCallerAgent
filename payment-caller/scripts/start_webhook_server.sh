#!/bin/bash

echo "================================="
echo "Starting Webhook Server Setup"
echo "================================="
echo ""

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "⚠️  ngrok is not installed!"
    echo ""
    echo "Please install ngrok:"
    echo "  brew install ngrok"
    echo "  OR download from: https://ngrok.com/download"
    echo ""
    exit 1
fi

echo "✓ ngrok is installed"
echo ""

# Start the FastAPI server in background if not already running
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "✓ Webhook server already running on port 8000"
else
    echo "Starting webhook server..."
    cd "$(dirname "$0")/.."
    source venv/bin/activate
    nohup uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload > logs/uvicorn.log 2>&1 &
    echo $! > .uvicorn.pid
    sleep 3
    echo "✓ Webhook server started"
fi

echo ""
echo "Starting ngrok tunnel..."
echo ""

# Start ngrok
ngrok http 8000
