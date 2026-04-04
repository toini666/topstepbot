#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=== TopStepBot — Update ==="

echo "Fetching latest version..."
git pull

echo "Updating Python dependencies..."
source venv/bin/activate
pip install -r backend/requirements.txt --quiet

echo "Rebuilding frontend..."
cd frontend
npm config set strict-ssl false
npm install
npm run build
cd ..

echo ""
echo "=== Update complete! ==="
echo "Restart the bot with: ./start_bot.sh"
