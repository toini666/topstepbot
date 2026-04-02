# TopStepBot — Installation (Windows)
# Run this script in PowerShell as Administrator if needed.
# Right-click > "Run with PowerShell" or open PowerShell and type: .\install.ps1

$ErrorActionPreference = "Stop"

$DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $DIR

Write-Host "=== TopStepBot — Installation ===" -ForegroundColor Cyan

# --- Python 3.12 ---
Write-Host ""
Write-Host "Checking Python 3.12..." -ForegroundColor Yellow

$PYTHON = $null

# Try py launcher first (standard on Windows)
try {
    $ver = & py -3.12 --version 2>&1
    if ($ver -match "3\.12") {
        $PYTHON = { py -3.12 @args }
        Write-Host "Found Python 3.12 via py launcher." -ForegroundColor Green
    }
} catch {}

# Fallback: python3.12 or python commands
if (-not $PYTHON) {
    foreach ($cmd in @("python3.12", "python3", "python")) {
        try {
            $ver = & $cmd --version 2>&1
            if ($ver -match "3\.12") {
                $PYTHON = $cmd
                Write-Host "Found Python 3.12: $cmd" -ForegroundColor Green
                break
            }
        } catch {}
    }
}

if (-not $PYTHON) {
    Write-Host ""
    Write-Host "ERROR: Python 3.12 not found." -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install it:" -ForegroundColor Yellow
    Write-Host "  1. Go to https://www.python.org/downloads/" -ForegroundColor White
    Write-Host "  2. Download Python 3.12.x (the latest 3.12 version)" -ForegroundColor White
    Write-Host "  3. Run the installer and CHECK the box 'Add Python to PATH'" -ForegroundColor White
    Write-Host "  4. Re-open PowerShell and run this script again." -ForegroundColor White
    exit 1
}

# --- Node.js ---
Write-Host ""
Write-Host "Checking Node.js..." -ForegroundColor Yellow
try {
    $nodeVer = & node --version 2>&1
    Write-Host "Found Node.js: $nodeVer" -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "ERROR: Node.js not found." -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install it:" -ForegroundColor Yellow
    Write-Host "  1. Go to https://nodejs.org/" -ForegroundColor White
    Write-Host "  2. Download the LTS version (recommended)" -ForegroundColor White
    Write-Host "  3. Run the installer (leave all options as default)" -ForegroundColor White
    Write-Host "  4. Re-open PowerShell and run this script again." -ForegroundColor White
    exit 1
}

# --- Python virtual environment ---
Write-Host ""
Write-Host "Setting up Python environment..." -ForegroundColor Yellow

if ($PYTHON -is [scriptblock]) {
    & py -3.12 -m venv venv
} else {
    & $PYTHON -m venv venv
}

Write-Host "Upgrading pip..." -ForegroundColor Yellow
& .\venv\Scripts\python.exe -m pip install --upgrade pip --quiet

Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
& .\venv\Scripts\pip.exe install -r backend\requirements.txt

# --- Build frontend ---
Write-Host ""
Write-Host "Building frontend..." -ForegroundColor Yellow
Set-Location frontend
& npm install
& npm run build
Set-Location ..

Write-Host ""
Write-Host "=== Installation complete! ===" -ForegroundColor Green
Write-Host ""
Write-Host "To start TopStepBot, run:" -ForegroundColor White
Write-Host "  .\start_bot.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "Then open: http://localhost:5173" -ForegroundColor White
Write-Host "A setup wizard will guide you through entering your credentials." -ForegroundColor White
