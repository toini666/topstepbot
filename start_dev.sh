#!/bin/bash

# Function to kill processes on exit
cleanup() {
    echo "Stopping servers..."
    kill $(jobs -p) 2>/dev/null
}
trap cleanup EXIT

echo "Starting TopStep Trading Bot..."

# Start Backend
echo "Starting Backend (Port 8000)..."
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000 &

# Start Frontend
echo "Starting Frontend (Port 5173)..."
cd frontend
npm run dev &

# Keep script running
wait
