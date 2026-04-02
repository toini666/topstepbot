# TopStepBot — Start (Windows)
# Keep this window open while the bot is running.
# Press Ctrl+C to stop.

$ErrorActionPreference = "Stop"

$DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $DIR

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "   STARTING TOPSTEP TRADING BOT" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

# --- Prevent Sleep (Windows equivalent of macOS caffeinate) ---
try {
    Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class SleepPreventer {
    [DllImport("kernel32.dll")]
    public static extern uint SetThreadExecutionState(uint esFlags);
    public const uint ES_CONTINUOUS      = 0x80000000;
    public const uint ES_SYSTEM_REQUIRED = 0x00000001;
}
"@ -ErrorAction SilentlyContinue
    [SleepPreventer]::SetThreadExecutionState(
        [SleepPreventer]::ES_CONTINUOUS -bor [SleepPreventer]::ES_SYSTEM_REQUIRED
    ) | Out-Null
    Write-Host "Preventing sleep while bot is running..." -ForegroundColor Green
} catch {}

# --- 1. Pre-start Cleanup ---
Write-Host "Cleaning up existing processes..." -ForegroundColor Yellow

# Stop existing uvicorn (backend)
try {
    Get-CimInstance Win32_Process |
        Where-Object { $_.CommandLine -like "*uvicorn*backend.main*" } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
} catch {}

# Wait up to 10s for port 8080 to free
$count = 0
while ((Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue)) {
    if ($count -eq 0) { Write-Host "   -> Waiting for port 8080 to free..." -ForegroundColor Gray }
    Start-Sleep -Seconds 1
    $count++
    if ($count -ge 10) {
        Write-Host "   -> Forcing port 8080 free..." -ForegroundColor Yellow
        Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue |
            ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
        break
    }
}

# Stop existing vite / frontend preview
try {
    Get-CimInstance Win32_Process |
        Where-Object { $_.CommandLine -like "*vite*" } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
} catch {}

# --- 2. Activate venv check ---
if (-not (Test-Path ".\venv\Scripts\uvicorn.exe")) {
    Write-Host ""
    Write-Host "ERROR: Virtual environment not found." -ForegroundColor Red
    Write-Host "Please run .\install.ps1 first." -ForegroundColor Yellow
    exit 1
}

$backendProc  = $null
$frontendProc = $null
$ngrokProc    = $null

try {
    # --- 3. Start Backend ---
    Write-Host "Starting Backend Server (Port 8080)..." -ForegroundColor Yellow
    $backendProc = Start-Process `
        -FilePath ".\venv\Scripts\uvicorn.exe" `
        -ArgumentList "backend.main:app", "--host", "0.0.0.0", "--port", "8080", "--no-access-log" `
        -PassThru -NoNewWindow
    Start-Sleep -Seconds 3

    # --- 4. Start Frontend ---
    Write-Host "Starting Frontend (Port 5173)..." -ForegroundColor Yellow
    $frontendProc = Start-Process `
        -FilePath "cmd.exe" `
        -ArgumentList "/c", "npm run preview" `
        -WorkingDirectory "$DIR\frontend" `
        -PassThru -NoNewWindow
    Start-Sleep -Seconds 2

    # --- 5. Ngrok ---
    Write-Host "Checking Ngrok Tunnel..." -ForegroundColor Yellow
    $NGROK_URL = ""
    $NGROK_IS_RUNNING = $false

    # Check if ngrok is already running
    try {
        $null = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -TimeoutSec 2
        Write-Host "   Found existing Ngrok instance. Reusing it." -ForegroundColor Green
        $NGROK_IS_RUNNING = $true
    } catch {
        # Look for ngrok binary
        $NGROK_CMD = $null
        if (Get-Command "ngrok" -ErrorAction SilentlyContinue) {
            $NGROK_CMD = "ngrok"
        } elseif (Test-Path "$DIR\ngrok.exe") {
            $NGROK_CMD = "$DIR\ngrok.exe"
        }

        if ($NGROK_CMD) {
            Write-Host "   Starting new Ngrok instance..." -ForegroundColor Yellow
            $ngrokProc = Start-Process -FilePath $NGROK_CMD -ArgumentList "http", "8080" -PassThru -NoNewWindow
            Start-Sleep -Seconds 3
            $NGROK_IS_RUNNING = $true
        } else {
            Write-Host "   Ngrok not found. Webhook URL will not be generated." -ForegroundColor Yellow
            $NGROK_URL = "Not available (install ngrok from https://ngrok.com/download)"
        }
    }

    # Fetch ngrok public URL
    if ($NGROK_IS_RUNNING) {
        Start-Sleep -Seconds 2
        try {
            $tunnels = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -TimeoutSec 5
            $NGROK_URL = ($tunnels.tunnels |
                Where-Object { $_.proto -eq "https" } |
                Select-Object -First 1).public_url
        } catch {
            $NGROK_URL = "Could not fetch URL (check http://localhost:4040)"
        }
    }

    Write-Host "===================================================" -ForegroundColor Cyan
    Write-Host "BOT IS RUNNING!" -ForegroundColor Green
    Write-Host "   -> Dashboard  : http://localhost:5173" -ForegroundColor White
    Write-Host "   -> Webhook URL: $NGROK_URL/api/webhook" -ForegroundColor White
    Write-Host ""
    Write-Host "Copy the Webhook URL to your TradingView Alert." -ForegroundColor Yellow
    Write-Host "Keep this window open while trading." -ForegroundColor Yellow
    Write-Host "Press Ctrl+C to stop." -ForegroundColor Yellow
    Write-Host "===================================================" -ForegroundColor Cyan

    # Send ngrok URL to backend
    if ($NGROK_URL -and
        $NGROK_URL -notlike "Not available*" -and
        $NGROK_URL -notlike "Could not fetch*") {
        Start-Sleep -Seconds 2
        try {
            Invoke-RestMethod `
                -Uri "http://localhost:8080/api/ngrok-url" `
                -Method POST `
                -ContentType "application/json" `
                -Body "{`"url`": `"$NGROK_URL`"}" `
                -ErrorAction SilentlyContinue | Out-Null
        } catch {}
    }

    # Keep running (Ctrl+C exits the loop and triggers finally)
    while ($true) {
        Start-Sleep -Seconds 5
        if ($backendProc.HasExited) {
            Write-Host ""
            Write-Host "ERROR: Backend stopped unexpectedly!" -ForegroundColor Red
            break
        }
    }

} finally {
    Write-Host ""
    Write-Host "Stopping services..." -ForegroundColor Yellow

    foreach ($proc in @($backendProc, $frontendProc, $ngrokProc)) {
        if ($proc -and -not $proc.HasExited) {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        }
    }

    # Re-enable sleep
    try {
        [SleepPreventer]::SetThreadExecutionState([SleepPreventer]::ES_CONTINUOUS) | Out-Null
    } catch {}

    Write-Host "Done. Bye!" -ForegroundColor Green
}
