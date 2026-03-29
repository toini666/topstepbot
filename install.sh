#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=== TopStepBot — Installation ==="

# --- Homebrew ---
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Add to PATH (Apple Silicon)
    if [[ -f "/opt/homebrew/bin/brew" ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
    fi
fi

# --- Python 3.12 ---
if ! python3 --version 2>/dev/null | grep -qE "3\.(1[2-9]|[2-9][0-9])"; then
    echo "Installing Python 3.12..."
    brew install python@3.12
    brew link --force python@3.12
fi

# --- Node.js ---
if ! command -v node &> /dev/null; then
    echo "Installing Node.js..."
    brew install node
fi

# --- Python virtual environment ---
echo "Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r backend/requirements.txt

# --- Build frontend ---
echo "Building frontend..."
cd frontend
npm install
npm run build
cd ..

echo ""
echo "=== Installation complete! ==="
echo ""
echo "To start TopStepBot, run:"
echo "  ./start_bot.sh"
echo ""
echo "Then open: http://localhost:5173"
echo "A setup wizard will guide you through entering your credentials."
