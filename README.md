# TopStepX Trading Bot

Automated trading system for TopStepX. Executes TradingView alerts with risk management, multi-account support, and real-time monitoring.

---

## Key Features

### Multi-Account Execution
- **Simultaneous Trading**: Execute signals across ALL connected accounts
- **Per-Account Settings**: Independent risk amounts, max contracts, strategy configs
- **Cross-Account Protection**: Prevents opposing positions across accounts

### Risk Management
- **Position Sizing**: Auto-calculates quantity based on risk per trade and stop distance
- **Session Filters**: Block trading during specific sessions (ASIA, UK, US)
- **Blocked Periods**: Custom time windows to prevent trading
- **News Blocks**: Auto-generated trading blocks from economic calendar events
- **Position Actions**: Automatic BREAKEVEN/FLATTEN before entering blocked periods
- **Trading Days**: Per-day toggles for when trading is allowed
- **Contract Limits**: Max micro-equivalent contracts per account
- **Signal Deduplication**: 30s cache prevents duplicate execution

### Trade Lifecycle
- **SIGNAL**: Open new positions with SL/TP bracket orders
- **PARTIAL**: Take partial profits with automatic SL/TP sync and optional SL-to-breakeven
- **CLOSE**: Full position closure on command
- **SETUP**: Informational alerts, logged but no execution

### Dashboard
- **Real-Time Positions**: Open positions with current price and unrealized PnL
- **Trade History**: Aggregated closed trades with strategy/timeframe filters
- **Daily P&L**: Live profit tracking per account
- **Order History**: Working and filled orders
- **System Logs**: Full audit trail with expandable JSON details
- **Economic Calendar**: Major events, weekly schedule, impact/country filters
- **Strategies Manager**: Global templates + per-account configuration
- **Ticker Mapping**: TradingView to TopStep contract mapping
- **Mock Webhook**: Test signals directly from the dashboard
- **Trade Reconciliation**: Preview and apply corrections between local DB and broker API

### Notifications
- **Telegram Bot**: Full remote control + real-time alerts (positions, PnL, errors, health)
- **Discord Webhooks**: Rich embeds for positions, partial closes, daily summaries
- **Per-Account Config**: Enable/disable notification types per account

### Economic Calendar
- **ForexFactory Integration**: Daily fetch with local caching
- **Dashboard View**: Today's major events + weekly schedule with filters
- **Discord Briefing**: Morning summary of high-impact events
- **Pre-Event Alerts**: Configurable Discord notification before major news
- **News Blocks**: Auto-converts events into trading blocks for the risk engine

### Telegram Bot Commands

| Command | Description |
|---------|-------------|
| `/status` | Current account status with unrealized PnL |
| `/status_all` | All accounts summary |
| `/accounts` | List accounts with IDs |
| `/switch [ID]` | Change active account |
| `/on` / `/off` | Enable/disable trading (current account) |
| `/on_all` / `/off_all` | Enable/disable trading (ALL accounts) |
| `/flatten` / `/flatten_all` | Flatten current / ALL accounts |
| `/cancel_orders` / `/cancel_all` | Cancel orders on current / ALL accounts |
| `/login` / `/logout` | Connect / disconnect TopStep API |

---

## Quick Start

### Prerequisites
- A Mac with internet access
- [ngrok](https://ngrok.com) account — for receiving TradingView webhooks
- Everything else (Python 3.12, Node.js) is installed automatically by `install.sh`

### Installation

```bash
# Clone
git clone https://github.com/toini666/topstepbot.git
cd topstepbot

# Install everything (run once)
./install.sh
```

Then start the bot and open http://localhost:5173 — a setup wizard will guide you through entering your credentials on first launch.

> **Alternative**: power users can skip the wizard by copying `.env.example` to `.env` and filling it in before starting.


### Environment Variables (`.env`)
```env
# TopStep API (required)
TOPSTEP_USERNAME=your_username
TOPSTEP_APIKEY=your_api_key

# Telegram (optional)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ID=your_chat_id

# Database
DATABASE_URL=sqlite:///./topstepbot.db

# Ngrok (required for TradingView webhooks)
NGROK_AUTHTOKEN=your_ngrok_token

# Heartbeat Monitoring (optional)
HEARTBEAT_WEBHOOK_URL=https://your-monitoring.com/webhook
HEARTBEAT_INTERVAL_SECONDS=60
HEARTBEAT_AUTH_TOKEN=your_secret_token
```

### Start the Bot
```bash
./start_bot.sh
```
This handles: Backend API, Frontend, Ngrok, Sleep prevention, Ngrok URL change detection.

**Access Points:**
- Dashboard: http://localhost:5173
- API Docs: http://localhost:8080/docs

### Update
```bash
./update.sh
./start_bot.sh
```

---

## TradingView Webhook

### Webhook URL
```
https://your-ngrok-url.ngrok-free.app/api/webhook
```

### Alert Payload (SIGNAL)
```json
{
  "type": "SIGNAL",
  "ticker": "MNQ1!",
  "side": "BUY",
  "entry": 20000.00,
  "stop": 19980.00,
  "tp": 20040.00,
  "timeframe": "M15",
  "strat": "RobReversal"
}
```

### Alert Payload (PARTIAL)
```json
{
  "type": "PARTIAL",
  "ticker": "MNQ1!",
  "timeframe": "M15",
  "strat": "RobReversal"
}
```

### Alert Payload (CLOSE)
```json
{
  "type": "CLOSE",
  "ticker": "MNQ1!",
  "timeframe": "M15",
  "strat": "RobReversal"
}
```

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   TradingView   │────▶│   TopStep Bot   │────▶│    TopStepX     │
│   (Webhooks)    │     │   (FastAPI)     │     │   (REST API)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │  SQLite  │ │ Telegram │ │ React UI │
              │    DB    │ │ & Discord│ │Dashboard │
              └──────────┘ └──────────┘ └──────────┘
```

### Stack
- **Backend**: Python 3.12+, FastAPI, SQLAlchemy, APScheduler, httpx — port 8080
- **Frontend**: React 19, TypeScript 5, Vite 7, Tailwind CSS 4 — port 5173
- **Database**: SQLite with auto-backup
- **Notifications**: Telegram Bot API, Discord Webhooks
- **External**: TopStepX REST API, ForexFactory (economic calendar)

---

## Configuration

### Dashboard Settings
- **Market Hours**: Define trading window (Brussels TZ)
- **Trading Days**: Day-of-week toggles
- **Blocked Periods**: Custom no-trade time blocks
- **News Blocks**: Auto-generated from economic calendar
- **Position Actions**: NOTHING/BREAKEVEN/FLATTEN before blocks
- **Auto-Flatten**: Daily position closure time
- **Account Risk**: Base risk amount and max contracts per account
- **Strategy Configs**: Risk factor, allowed sessions, partial TP, SL-to-breakeven

### Ticker Mapping
Map TradingView tickers (e.g., `MNQ1!`) to TopStep contracts (e.g., `MNQH6`):
- Configured via Dashboard Settings > Mappings tab
- Includes tick size, tick value, micro equivalent

---

## Security

| Feature | Implementation |
|---------|----------------|
| Webhook Security | TradingView IP whitelist (4 IPs) + localhost |
| Signal Deduplication | 30s TTL cache prevents duplicates |
| CORS | Restricted to localhost only |
| Credentials | Environment variables only |
| Input Validation | Pydantic schemas |
| Log Redaction | Sensitive data masked automatically |

---

## Maintenance

| Task | Schedule | Automatic |
|------|----------|-----------|
| Database Backup | 03:00 UTC | 7-day retention |
| Log Cleanup | 03:15 UTC | 7-day retention |
| Startup Backup | On start | If none today |
| API Health Check | Every 60s | Telegram alert on failure |
| Contract Validation | Daily 23:00 | Telegram alert on expiry |

Backups stored in `./backups/`

---

## External Monitoring (Heartbeat)

Periodic status pings to external systems (N8N, Healthchecks.io) for crash detection.

**Heartbeat (every 60s):**
```json
{
  "bot_name": "TopStepBot",
  "timestamp": "2026-01-15T12:31:00+01:00",
  "timestamp_unix": 1736939460,
  "uptime_seconds": 3600,
  "uptime_formatted": "1h 0m",
  "trading_enabled": true,
  "active_accounts": 2,
  "api_healthy": true,
  "version": "2.0.0"
}
```

**Graceful Shutdown (CTRL-C):**
```json
{
  "bot_name": "TopStepBot",
  "event": "shutdown",
  "reason": "graceful",
  "uptime_seconds": 7200,
  "uptime_formatted": "2h 0m",
  "version": "2.0.0"
}
```

> **Tip**: In N8N, check for `event: "shutdown"` to avoid false alerts on planned restarts.

---

## Documentation

- [Architecture Details](docs/architecture.md)
- [Product Requirements](docs/prd.md)
- [Execution Flows](docs/flows.md)
- [TopStep API Reference](docs/docapitopstep.md)

---

## Disclaimer

This software is provided as-is for educational purposes. Trading involves risk. Use at your own discretion.

---

**Made for TopStepX traders**
