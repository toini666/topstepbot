# TopStepX Trading Bot 🤖

A professional-grade automated trading system for TopStepX. Executes TradingView alerts with enterprise-level risk management, multi-account support, and real-time monitoring.

---

## ✨ Key Features

### ⚡ Multi-Account Execution
- **Simultaneous Trading**: Execute signals across ALL connected accounts automatically
- **Per-Account Risk Settings**: Configure different risk amounts and strategy settings per account
- **Cross-Account Protection**: Prevents opening opposing positions across accounts

### 🛡️ Risk Management
- **Position Sizing**: Auto-calculates quantity based on risk per trade
- **Session Filters**: Block trading during specific sessions (ASIA, UK, US)
- **Blocked Periods**: Define custom time windows to prevent trading
- **Trading Days**: Per-day toggles for when you want to trade

### 📈 Trade Lifecycle
- **SIGNAL**: Open new positions with SL/TP orders
- **PARTIAL**: Take partial profits with automatic SL/TP synchronization
- **CLOSE**: Full position closure on command

### 📊 Dashboard
- **Real-Time Positions**: View open positions across all accounts
- **Trade History**: Aggregated closed trades with strategy/timeframe
- **Daily P&L**: Live profit tracking per account
- **Order History**: All orders with status updates
- **System Logs**: Full audit trail of all actions

### 🤖 Telegram Bot Control
| Command | Description |
|---------|-------------|
| `/status` | Current account status |
| `/status_all` | All accounts: trading status, PnL, positions |
| `/accounts` | List accounts with IDs |
| `/switch [ID]` | Change active account |
| `/on` / `/off` | Enable/disable trading (current account) |
| `/on_all` / `/off_all` | Enable/disable trading (ALL accounts) |
| `/flatten` | Flatten current account (shows position + order count) |
| `/flatten_all` | 🚨 Flatten ALL accounts (per-account breakdown) |
| `/cancel_orders` | Cancel orders (shows count) |
| `/cancel_all` | Cancel ALL account orders (per-account breakdown) |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+ & npm
- ngrok (for webhook URL)

### Installation

```bash
# Clone
git clone https://github.com/toini666/topstepbot.git
cd topstepbot

# Configure
cp .env.example .env
# Edit .env with your credentials
```

### Environment Variables (`.env`)
```env
# TopStep API
TOPSTEP_USERNAME=your_username
TOPSTEP_APIKEY=your_api_key

# Telegram (required)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ID=your_chat_id

# Database
DATABASE_URL=sqlite:///./topstepbot.db

# Optional
NGROK_AUTHTOKEN=your_ngrok_token
```

### Start the Bot
```bash
./start_bot.sh
```
This handles: Backend API → Frontend → Ngrok → Sleep prevention

**Access Points:**
- Dashboard: http://localhost:5173
- API Docs: http://localhost:8000/docs

---

## 📡 TradingView Webhook

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

## 🏗️ Architecture

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
              │    DB    │ │   Bot    │ │Dashboard │
              └──────────┘ └──────────┘ └──────────┘
```

### Stack
- **Backend**: FastAPI + SQLAlchemy + APScheduler
- **Frontend**: React 18 + TypeScript + Vite
- **Database**: SQLite with auto-backup

---

## 🔧 Configuration

### Dashboard Settings
- **Market Hours**: Define trading window
- **Blocked Periods**: Custom no-trade time blocks
- **Auto-Flatten**: Daily position closure time
- **Account Risk**: Base risk amount per account
- **Strategy Configs**: Risk factor, allowed sessions, partial TP settings

### Ticker Mapping
Map TradingView tickers (e.g., `MNQ1!`) to TopStep contracts (e.g., `MNQH6`):
- Configured via Dashboard → Strategies tab
- Auto-resolved if no manual mapping

---

## 🛡️ Security

| Feature | Implementation |
|---------|----------------|
| Webhook Security | TradingView IP whitelist |
| CORS | Restricted to localhost only |
| Credentials | Environment variables only |
| Input Validation | Pydantic schemas |

---

## 🗂️ Maintenance

| Task | Schedule | Automatic |
|------|----------|-----------|
| Database Backup | 03:00 UTC | ✅ |
| Log Cleanup | 03:15 UTC | ✅ (7 days) |
| Startup Backup | On start | ✅ |

Backups stored in `./backups/`

---

## 📚 Documentation

- [Architecture Details](docs/architecture.md)
- [Execution Flows](docs/flows.md)
- [TopStep API Reference](docs/docapitopstep.md)
- [Project Backlog](docs/backlog.md)

---

## ⚠️ Disclaimer

This software is provided as-is for educational purposes. Trading involves risk. Use at your own discretion.

---

**Made with ❤️ for TopStepX traders**
