# TopStepBot — Update (Windows)
# Run this script to pull the latest version and rebuild.

$ErrorActionPreference = "Stop"

$DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $DIR

Write-Host "=== TopStepBot — Update ===" -ForegroundColor Cyan

Write-Host "Fetching latest version..." -ForegroundColor Yellow
& git pull

Write-Host "Updating Python dependencies..." -ForegroundColor Yellow
& .\venv\Scripts\pip.exe install -r backend\requirements.txt --quiet

Write-Host "Rebuilding frontend..." -ForegroundColor Yellow
Set-Location frontend
& npm install
& npm run build
Set-Location ..

Write-Host ""
Write-Host "=== Update complete! ===" -ForegroundColor Green
Write-Host "Restart the bot with: .\start_bot.ps1" -ForegroundColor Cyan
