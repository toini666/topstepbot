# TopStep Trading Bot - Technical Architecture

## System Overview

TopStep Bot is a FastAPI-based trading automation system that processes TradingView webhook alerts and executes trades on TopStepX accounts through their REST API.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   TradingView   │────▶│   TopStep Bot   │────▶│    TopStepX     │
│    (Webhooks)   │     │   (FastAPI)     │     │   (REST API)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │  SQLite  │ │ Telegram │ │ React UI │
              │    DB    │ │   Bot    │ │Dashboard │
              └──────────┘ └──────────┘ └──────────┘
```

---

## Directory Structure

```
topstepbot/
├── backend/
│   ├── main.py                 # FastAPI app, scheduler, position monitor
│   ├── database.py             # SQLAlchemy models
│   ├── schemas.py              # Pydantic schemas
│   ├── routers/
│   │   ├── webhook.py          # Signal processing (SIGNAL, PARTIAL, CLOSE)
│   │   ├── dashboard.py        # UI API endpoints
│   │   ├── strategies.py       # Strategy CRUD
│   │   └── export.py           # Data export & statistics
│   └── services/
│       ├── topstep_client.py   # TopStepX API wrapper
│       ├── risk_engine.py      # Risk management logic
│       ├── telegram_service.py # Telegram notifications
│       ├── telegram_bot.py     # Telegram command handler
│       ├── maintenance_service.py # Backup & log cleanup
│       └── persistence_service.py # State persistence
├── frontend/
│   ├── src/
│   │   ├── App.tsx             # Main dashboard component
│   │   ├── hooks/useTopStep.ts # Data fetching hook
│   │   ├── types.ts            # TypeScript interfaces
│   │   ├── components/         # UI components
│   │   └── utils/              # Helper functions
│   └── dist/                   # Built static files
├── backups/                    # Database backups
├── DOCS/                       # Documentation
└── start_bot.sh                # Startup script
```

---

## Core Components

### 1. Database Layer (`database.py`)

#### Models

| Model | Purpose |
|-------|---------|
| `Setting` | Key-value global settings store |
| `TradingSession` | Session definitions (ASIA, UK, US) |
| `TickerMap` | TradingView → TopStep contract mapping |
| `Strategy` | Strategy templates with default configs |
| `AccountSettings` | Per-account trading configuration |
| `AccountStrategyConfig` | Strategy overrides per account |
| `Trade` | Local trade records with full metadata |
| `Log` | System event logs |

#### Trade Model Fields
```python
Trade:
  - id, account_id, ticker, action
  - entry_price, exit_price, sl, tp
  - quantity, status, pnl, fees
  - timeframe, session, strategy
  - timestamp, exit_time, duration_seconds
  - topstep_order_id, rejection_reason
```

### 2. Risk Engine (`risk_engine.py`)

Central risk management service with hierarchical settings resolution.

#### Key Methods

```python
class RiskEngine:
    # Global Settings
    get_global_settings() → dict
    get_trading_sessions() → List[TradingSession]
    get_current_session() → Optional[str]
    
    # Validation Checks
    check_market_hours() → Tuple[bool, str]
    check_blocked_periods() → Tuple[bool, str]
    check_account_enabled(account_id) → Tuple[bool, str]
    check_strategy_enabled(account_id, strategy) → Tuple[bool, str]
    check_session_allowed(account_id, strategy) → Tuple[bool, str]
    check_open_position(account_id, ticker, client) → Tuple[bool, str]
    check_cross_account_direction(ticker, direction, client) → Tuple[bool, str]
    
    # Position Sizing
    get_risk_amount(account_id, strategy) → float
    calculate_position_size(entry, sl, risk, tick_size, tick_value) → int
```

#### Settings Hierarchy
```
1. Strategy.default_* (base defaults)
2. AccountStrategyConfig.* (per-account overrides)
3. AccountSettings.risk_per_trade (account risk amount)
4. Applied: risk_per_trade × risk_factor = effective_risk
```

### 3. TopStep Client (`topstep_client.py`)

Async HTTP client for TopStepX API with automatic token management.

#### API Endpoints Used

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/Auth/loginKey` | Authenticate with API key |
| POST | `/api/Account/search` | List trading accounts |
| POST | `/api/Position/searchOpen` | Get open positions |
| POST | `/api/Position/closeContract` | Close entire position |
| POST | `/api/Order/search` | Get order history |
| POST | `/api/Order/place` | Place new order |
| POST | `/api/Order/modify` | Modify existing order |
| POST | `/api/Order/cancel` | Cancel order |
| POST | `/api/Contract/available` | List available contracts |
| POST | `/api/Trade/search` | Get trade history |

#### Order Types
```python
type: 1 = Limit, 2 = Market, 4 = Stop
side: 0 = Buy, 1 = Sell
status: 1 = Working, 2 = Filled, 3 = Cancelled
```

### 4. Webhook Router (`webhook.py`)

Processes incoming TradingView alerts.

#### Alert Schema
```json
{
  "type": "SIGNAL",
  "ticker": "MNQ1!",
  "side": "BUY",
  "entry": 20000.00,
  "stop": 19980.00,
  "tp": 20040.00,
  "timeframe": "M5",
  "strat": "rob_rev"
}
```

#### Signal Processing Flow
```
1. Verify source IP (TradingView whitelist)
2. Log reception
3. Route by type (SETUP/SIGNAL/PARTIAL/CLOSE)
4. For SIGNAL:
   a. Check market hours (global)
   b. Check blocked periods (global)
   c. Iterate ALL accounts:
      - Check account enabled
      - Check strategy enabled
      - Check session allowed
      - Check existing position
   d. Check cross-account direction
   e. Resolve contract info
   f. For each eligible account:
      - Calculate position size
      - Create Trade record
      - Execute in background
```

### 5. Dashboard Router (`dashboard.py`)

REST API for frontend dashboard.

#### Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/dashboard/status` | GET | Connection status |
| `/dashboard/market-status` | GET | Market open + current session |
| `/dashboard/config` | GET/POST | Global settings |
| `/dashboard/trades` | GET | Local trade records |
| `/dashboard/logs` | GET | System logs (paginated) |
| `/dashboard/accounts` | GET | TopStep accounts list |
| `/dashboard/positions/{id}` | GET | Account positions |
| `/dashboard/orders/{id}` | GET | Account orders |
| `/dashboard/history/{id}` | GET | Account trade history |
| `/settings/accounts/{id}` | GET/POST | Account settings |
| `/settings/sessions` | GET/POST | Trading sessions |
| `/dashboard/account/{id}/flatten` | POST | Flatten single account |
| `/dashboard/flatten-all` | POST | Flatten all accounts |

### 6. Export Router (`export.py`)

Data export and analytics endpoints.

#### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/export/trades` | GET | Export trades (JSON/CSV) |
| `/export/stats` | GET | Aggregated statistics |

#### Filter Parameters
- `status`, `strategy`, `timeframe`, `ticker`
- `account_id`, `session`
- `from_date`, `to_date`, `limit`

---

## Scheduled Jobs

| Job | Schedule | Function |
|-----|----------|----------|
| Position Monitor | Every 5s | Detect closed positions |
| Orphan Detection | Every 60s | Find orders without positions |
| Auto Flatten | Configurable time | Close all positions daily |
| Database Backup | 03:00 UTC | Copy database file |
| Log Cleanup | 04:00 UTC | Remove logs > 7 days |

---

## Frontend Architecture

### Technology Stack
- **React 18** with TypeScript
- **Vite** for build tooling
- **Sonner** for toast notifications
- **Lucide React** for icons
- **date-fns** for date formatting

### Main Hook (`useTopStep.ts`)

Centralized data management with polling.

```typescript
useTopStep() → {
  // Connection
  isConnected, loading, connect, logout
  
  // Data (per-account)
  accounts, positions, orders, historicalTrades
  positionsByAccount, ordersByAccount, tradesByAccount
  
  // Settings
  globalConfig, accountSettings, tradingSessions, strategies
  updateGlobalConfig, updateAccountSettings, toggleAccountTrading
  
  // Actions
  closePosition, flattenAccount, flattenAllAccounts
  
  // UI State
  selectedAccountId, historyFilter, marketStatus
}
```

### Component Structure

```
App.tsx
├── Header (status, account selector)
├── Main Content
│   ├── Open Positions Table
│   ├── Account Details Card
│   ├── Daily P&L Summary
│   ├── Trade History Table
│   └── Order History Table
├── System Logs Section
├── ConfigModal (global settings)
├── StrategiesManager (strategy config)
├── MockWebhookModal (testing)
└── ConfirmModal (actions)
```

---

## Security Considerations

| Aspect | Implementation |
|--------|----------------|
| **Credentials** | Environment variables (.env file) |
| **Webhook Security** | TradingView IP whitelist (4 IPs) |
| **API Authentication** | Bearer token, auto-refresh on 401 |
| **CORS** | Restricted to localhost:5173/5174 (GET, POST, OPTIONS) |
| **Input Validation** | Pydantic schemas for all inputs |
| **Logging** | Sensitive data masked in logs |

### TradingView IP Whitelist
```python
TRADINGVIEW_IPS = [
    "52.89.214.238",
    "34.212.75.30",
    "54.218.53.128",
    "52.32.178.7"
]
```
Webhook requests from other IPs are rejected with HTTP 403.

---

## Error Handling

| Scenario | Handling |
|----------|----------|
| TopStep API 401 | Clear token, re-authenticate |
| Order Rejection | Log reason, Telegram notification |
| Contract Not Found | Fallback to ticker as contract ID |
| Database Error | Rollback transaction, log error |
| Network Timeout | 10s timeout, graceful failure |

---

## Performance Optimizations

1. **Contract Caching** - In-memory cache for contract details
2. **Selective Logging** - Skip noisy polling endpoints
3. **Background Execution** - Trade execution in FastAPI BackgroundTasks
4. **Polling Intervals** - 3s for data, 5s for position monitor
5. **Database Indexes** - On frequently queried columns

---

## Configuration

### Environment Variables (`.env`)

```bash
# TopStepX API
TOPSTEP_URL=https://api.topstepx.com
TOPSTEP_USERNAME=your_username
TOPSTEP_APIKEY=your_api_key

# Telegram
TELEGRAM_BOT_TOKEN=bot_token
TELEGRAM_ID=chat_id

# Database
DATABASE_URL=sqlite:///./topstepbot.db
```

### Global Settings (Database)

| Key | Default | Description |
|-----|---------|-------------|
| `market_open_time` | "00:00" | Market opens (Brussels TZ) |
| `market_close_time` | "22:00" | Market closes |
| `blocked_periods_enabled` | true | Enable time blocks |
| `blocked_periods` | [] | JSON array of time blocks |
| `auto_flatten_enabled` | false | Daily auto-flatten |
| `auto_flatten_time` | "21:55" | Flatten time |
