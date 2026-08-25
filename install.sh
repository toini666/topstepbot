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
if ! command -v python3.12 &> /dev/null; then
    echo "Installing Python 3.12..."
    brew install python@3.12
fi
# Always use the explicit python3.12 binary (avoids using system Python)
PYTHON=$(command -v python3.12)

# --- Node.js ---
if ! command -v node &> /dev/null; then
    echo "Installing Node.js..."
    brew install node
else
    echo "Updating Node.js..."
    brew upgrade node 2>/dev/null || true
fi

# --- Python virtual environment ---
echo "Setting up Python environment..."
"$PYTHON" -m venv venv
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r backend/requirements.txt

# --- Build frontend ---
echo "Building frontend..."
cd frontend
# "npm cache clean --force" a ete retire: il vide le cache npm GLOBAL (~/.npm/_cacache) de
# tous les projets de la machine, et forcait a re-telecharger les 227 paquets a chaque install.
# "verify" repare/compacte le cache sans le detruire; le determinisme vient du lockfile.
npm cache verify
rm -rf node_modules
# TLS: portee limitee a cette commande. NE PAS utiliser "npm config set strict-ssl false":
# cela ecrit dans le ~/.npmrc de l'utilisateur et desactive la verification TLS pour
# TOUS ses projets, definitivement. Correctif propre derriere un proxy qui casse le TLS:
#   npm config set cafile /chemin/vers/certificat-racine.pem
npm install --strict-ssl=false
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
