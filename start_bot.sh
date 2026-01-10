#!/bin/bash

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "==================================================="
echo "   🚀 STARTING TOPSTEP TRADING BOT"
echo "==================================================="

# Prevent Sleep (MacOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "☕️ Preventing sleep while bot is running..."
    caffeinate -i -w $$ &
fi

# 1. Pre-start Cleanup
echo "🧹 Cleaning up existing processes..."
# Kill process occupying port 8000 (Backend)
if lsof -t -i :8000 >/dev/null; then
    echo "   -> Killing process on port 8000..."
    lsof -t -i :8000 | xargs kill -9
fi
pkill -f "uvicorn backend.main:app" || true
pkill -f "vite" || true
sleep 2

# 2. Activate Python Environment
echo "🐍 Activating Virtual Environment..."
source ./venv/bin/activate

# Function to kill child processes on exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    # Only kill jobs started by this script (backend & frontend)
    # Ngrok is disowned so it won't be killed here
    kill $(jobs -p) 2>/dev/null
    echo "✅ Done. Bye!"
    exit
}
trap cleanup SIGINT

# 2. Start Backend
echo "⚙️  Starting Backend Server (Port 8000)..."
uvicorn backend.main:app --reload --no-access-log &
BACKEND_PID=$!

# Wait for backend to initialize
sleep 3

# 3. Start Frontend
echo "💻 Starting Frontend Dashboard..."
cd frontend
npm run dev &
FRONTEND_PID=$!

# 4. Start Ngrok (Persistent)
echo "🌍 Checking Ngrok Tunnel..."
NGROK_URL=""
NGROK_IS_RUNNING=false

# Check if Ngrok is already running (API check)
if curl -s --max-time 2 http://localhost:4040/api/tunnels >/dev/null; then
    echo "   ✅ Found existing Ngrok instance. Reusing it."
    NGROK_IS_RUNNING=true
else
    # Prepare to start new instance
    NGROK_CMD="ngrok"
    NGROK_LOCAL="$DIR/ngrok"
    CAN_START_NGROK=true

    if ! command -v ngrok &> /dev/null; then
        if [ -f "$NGROK_LOCAL" ]; then
            echo "   -> Found local ngrok binary."
            chmod +x "$NGROK_LOCAL"
            NGROK_CMD="$NGROK_LOCAL"
        else
            echo "⚠️  Ngrok not found. Webhook URL will not be generated."
            NGROK_URL="Not available (Install 'ngrok')"
            CAN_START_NGROK=false
        fi
    fi

    if [ "$CAN_START_NGROK" = true ]; then
        echo "   🚀 Starting new Ngrok instance..."
        $NGROK_CMD http 8000 > /dev/null &
        # Disown so it survives script exit
        disown $!
        sleep 3
        NGROK_IS_RUNNING=true
    fi
fi

if [ "$NGROK_IS_RUNNING" = true ]; then
    # Fetch Webhook URL
    sleep 2
    NGROK_URL=$(curl -s localhost:4040/api/tunnels | grep -o "https://[a-zA-Z0-9.-]*\.ngrok-free\.[a-z]*" | head -n 1)
fi

echo "==================================================="
echo "✅ BOT IS RUNNING!"
echo "   -> Dashboard: http://localhost:5173"
echo "   -> Webhook URL: $NGROK_URL/api/webhook"
echo ""
echo "👉 Copy the Webhook URL to your TradingView Alert."
echo "👉 Keep this terminal open while trading."
echo "👉 Press Ctrl+C to stop."
echo "==================================================="

# Keep script running
wait
