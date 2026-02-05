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
│   │   ├── export.py           # Data export & statistics
│   │   └── calendar.py         # Calendar endpoints
│   └── services/
│       ├── topstep_client.py   # TopStepX API wrapper
│       ├── risk_engine.py      # Risk management logic
│       ├── price_cache.py      # Real-time price caching (5s TTL)
│       ├── telegram_service.py # Telegram notifications
│       ├── telegram_bot.py     # Telegram command handler
│       ├── maintenance_service.py # Backup & log cleanup
│       ├── persistence_service.py # State persistence
│       ├── reconciliation_service.py # Manual trade reconciliation
│       ├── discord_service.py # Discord notifications
│       └── calendar_service.py # Economic Calendar & News Block calculation
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
| `TickerMap` | TradingView → TopStep contract mapping + micro_equivalent |
| `Strategy` | Strategy templates with default configs |
| `AccountSettings` | Per-account trading configuration |
| `AccountStrategyConfig` | Strategy overrides per account |
| `Trade` | Local trade records with full metadata |
| `DiscordNotificationSettings` | Per-account Discord preferences |
| `Log` | System event logs |

#### Trade Model Fields
```python
Trade:
  - id, account_id, ticker, action
  - id, account_id, ticker, action
  - entry_price, signal_entry_price, exit_price, sl, tp
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
    check_market_open() → Tuple[bool, str]      # Market status (hours + weekend_markets_open)
    check_market_hours() → Tuple[bool, str]     # Trading allowed (trading_days + hours)
    check_blocked_periods() → Tuple[bool, str]  # Manual blocks + Dynamic news blocks
    check_account_enabled(account_id) → Tuple[bool, str]
    check_strategy_enabled(account_id, strategy) → Tuple[bool, str]
    check_session_allowed(account_id, strategy) → Tuple[bool, str]  # Respects allow_outside_sessions
    check_open_position(account_id, ticker, client) → Tuple[bool, str]  # Configurable via toggle
    check_contract_limit(account_id, new_size) → Tuple[bool, str]
    check_cross_account_direction(ticker, direction, client) → Tuple[bool, str]  # Configurable via toggle
    
    # Position Sizing
    get_risk_amount(account_id, strategy) → float
    calculate_position_size(entry, sl, risk, tick_size, tick_value) → int

# Standalone utility function
calculate_unrealized_pnl(entry_price, current_price, quantity, is_long, tick_size, tick_value) → float
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
- **Persistent Connection**: Uses a single `httpx.AsyncClient` session throughout the application lifecycle to minimize TCP/TLS overhead.
- **Circuit Breaker**: Integrated rate limiting protection.

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
| POST | `/api/Position/partialCloseContract` | Partial close position |
| POST | `/api/Status/ping` | API Health Check |
| POST | `/api/Order/cancel` | Cancel order |
| POST | `/api/Contract/available` | List available contracts |
| POST | `/api/Trade/search` | Get trade history |
| POST | `/api/History/retrieveBars` | Get current price (1s bars) |

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

5. For PARTIAL:
   - Identify matching open trades
   - Calculate reduction quantity based on strategy config
   - Execute partial close via TopStep API
   - Sync remaining SL/TP order quantities
   - Fetch realized PnL via trade history lookup
   - Notify Telegram and Discord (if enabled)
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
| `/dashboard/reconcile/{id}/preview` | POST | Preview trade corrections (dry-run) |
| `/dashboard/reconcile/{id}/apply` | POST | Apply trade corrections |

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

## Core Services & Utilities

### 1. Settings Cache (`settings_cache.py`)

In-memory cache for frequently accessed configuration to minimize database I/O.

#### Features
- **TTL Caching**: Global settings and account configs cached for 60s (configurable).
- **Thread-Safe**: Uses `threading.RLock` to ensure safety across threads.
- **Smart Invalidation**: Updates to settings via API automatically invalidate relevant cache keys.

### 2. Async Database (`async_db.py`)

Wrapper to execute synchronous SQLAlchemy blocking calls in a dedicated thread pool, preventing `asyncio` event loop blocking.

#### Pattern
```python
@async_db_session
def get_users(db):
    return db.query(User).all()

# Usage
users = await get_users()
```

### 3. Logging Service (`logging_service.py`)

Centralized structured logger that handles both console output and database persistence.

- **Console**: Color-coded output for standard IO.
- **Database**: Asynchronous persistence to `Log` table for dashboard viewing via `async_add_log`.
- **Security**: Automatic redaction of sensitive fields (api_key, token) in API logs.
- **Context**: Supports extra metadata (e.g., trade_id, account_name) for detailed auditing.

### 4. Discord Service (`discord_service.py`)

Handles Discord notifications with robust reliability features:
- **Rate Limit Handling**: Automatically handles HTTP 429 responses with `Retry-After` backoff.
- **Connection Pooling**: Reuses HTTP clients/connections for high-frequency messaging.
- **Rich Embeds**: Formats messages with color-coded side indicators/PnL.

---

## Scheduled Jobs

| Job | Schedule | Function |
|-----|----------|----------|
| Position Monitor | Every 5s | Detect closed positions. **Optimized**: Async API fetch + Sync DB processing in thread pool to prevent event loop blocking. Batch queries to avoid N+1 issues. |
| **Price Refresh** | Every 5s | Fetches current prices for all open positions, updates price cache for unrealized PnL |
| Auto Flatten | Configurable time | Close all positions daily |
| API Health Check | Every 60s | Pings API, tracks health, alerts on consecutive failures |
| **Heartbeat** | Configurable (default 60s) | Sends ping to external monitoring (N8N) with bot status |
| **Ngrok URL Detection** | On startup | Detects URL changes, notifies via Terminal/Logs/Telegram |
| Database Backup | 03:00 UTC | Copy database file |
| Log Cleanup | 03:15 UTC | Remove logs > 7 days |
| Discord Daily Summary | Configurable | Sends account summary to Discord |
| Discord Daily Summary | Configurable | Sends account summary to Discord |
| **Economic Calendar** | Daily 07:00 | Fetches events, calculates news blocks, sends briefing |
| **News Alert** | Every 1m | Checks for high-impact events starting in 5m, sends Discord alert |
| **Contract Validation** | Daily 23:00 | Checks validity of configured contracts vs TopStep API |
| **Position Action** | Every 30s | Checks upcoming blocks, executes BREAKEVEN/FLATTEN |

---

## Trade History (Aggregated View)

The frontend displays trade history from the **internal Trade table** instead of raw TopStep API data.

### Benefits
- **Aggregated trades**: Entry + all partial TPs + final close shown as single line
- **Consistent data**: PnL and fees are totals for the complete trade
- **Precision**: Trades filtered by Symbol + Entry Timestamp (with 2s tolerance) to prevent data mixing
- **Strategy tracking**: Strategy name and timeframe preserved from webhook

### Data Flow
```
1. Webhook opens trade → Trade record created (status=OPEN)
2. TopStep executes → Position appears in API
3. Position closes (SL/TP/manual) → Position disappears from API
4. Position Monitor detects closure:
   - Matches trade by Symbol AND matching Entry Timestamp (captured from API or initial fill)
   - Updates Trade: status=CLOSED, exit_price, pnl, fees, exit_time
   - Sends Telegram notification
5. Frontend fetches /dashboard/trades?status=CLOSED → Shows aggregated history
6. **Reconciliation Loop**:
   - Checks for "phantom" open trades in DB that are missing from API
   - Verifies against "Truth" (API History) using robust timestamp comparison
   - Automatically marks as CLOSED if verified
7. **Manual Trade Detection**:
   - Detects new positions not initiated by webhook
   - Creates Trade record with strategy="MANUAL"
   - Tracks these trades normally through to closure
```

### API Endpoint
```
GET /dashboard/trades?account_id={id}&days={n}&status=CLOSED
```

---

## System Logged Events

The following operations are logged to System Logs (visible in Logs tab):

### Strategy Operations

| Operation | Level | Message | Details |
|-----------|-------|---------|---------|
| Create Template | INFO | `Strategy Template Created: {name} (tv_id: {id})` | - |
| Update Template | INFO | `Strategy Template Updated: {name} (sessions, factor)` | - |
| Delete Template | WARNING | `Strategy Template Deleted: {name}` | - |
| Add to Account | INFO | `Strategy Added to Account: {strategy} on {account}` | JSON config |
| Update Config | INFO | `Strategy Config Updated: {strategy} on {account}` | JSON config |
| Remove from Account | WARNING | `Strategy Removed from Account: {strategy} from {account}` | JSON details |

---

## Telegram Bot Commands

The bot provides remote control and monitoring via Telegram.

### Monitoring Commands

| Command | Description |
|---------|-------------|
| `/status` | Current account balance, PnL, positions |
| `/status_all` | All accounts: trading status, balance, PnL, positions |
| `/accounts` | List all available accounts with IDs |

### Control Commands

| Command | Description |
|---------|-------------|
| `/on` | Enable trading on selected account |
| `/off` | Disable trading on selected account |
| `/on_all` | Enable trading on ALL accounts |
| `/off_all` | Disable trading on ALL accounts |
| `/login` | Connect to TopStep API |
| `/logout` | Disconnect from TopStep API |
| `/switch [ID]` | Switch active account |

### Emergency Commands

| Command | Description |
|---------|-------------|
| `/cancel_orders` | Cancel orders on current account (shows count) |
| `/cancel_all` | Cancel orders on ALL accounts (per-account breakdown) |
| `/flatten` | Flatten current account (shows positions + orders count) |
| `/flatten_all` | 🚨 Flatten ALL accounts (per-account breakdown) |

### Startup Notification
On bot startup, sends a summary of any open positions across all accounts instead of individual "Position Opened" notifications.

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
├── StrategiesManager
│   ├── View Toggle (Account Strategies / Global Templates)
│   ├── Account Strategies Table (per-account configs with inline edit)
│   └── Global Templates Table (strategy CRUD)
├── MockWebhookModal (testing)
└── ConfirmModal (actions)
```

### StrategiesManager Features

The Strategies tab provides two views:

| View | Purpose | Features |
|------|---------|----------|
| **Account Strategies** | Per-account config | Inline edit sessions, risk factor, partial %, SL→BE toggle |
| **Global Templates** | Strategy templates | Create/edit/delete strategy definitions |

Both tables display consistent columns:
- Strategy (Name + TV ID)
- Sessions (ASIA, UK, US)
- Risk Factor (multiplier)
- Partial % (take-profit percentage)
- SL → BE (move stop-loss to entry on partial)
- Risk Factor (multiplier)
- Partial % (take-profit percentage)
- SL → BE (move stop-loss to entry on partial)
- Outside (allow trading outside configured sessions) - *Integrated into Sessions list as "OUTSIDE" option*

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
| TopStep API 429 | Circuit Breaker (60s cooldown), Telegram Alert |
| Order Rejection | Log reason, Telegram notification |
| Contract Not Found | Fallback to ticker as contract ID |
| Database Error | Rollback transaction, log error |
| Network Timeout | 10s timeout, graceful failure |

---

---

## Performance Optimizations

1.  **Contract Caching** - In-memory cache for contract details.
2.  **Settings Caching** - TTL-based caching for global and account settings to reduce DB load.
3.  **Async Database Access** - Dedicated thread pool for DB operations to keep the event loop non-blocking.
4.  **API Response Caching** - Cached account and position data with configurable TTL.
5.  **Parallel Position Checks** - Concurrent account eligibility verification using `asyncio.gather`.
6.  **Non-blocking Notifications** - Telegram alerts dispatched via `asyncio.create_task`.
7.  **SL/TP Retry Logic** - 3-attempt retry with exponential backoff for order corrections.
8.  **Selective Logging** - Skip noisy polling endpoints.
9.  **Background Execution** - Trade execution in FastAPI BackgroundTasks.
10. **Polling Intervals** - 3s for data, 5s for position monitor.
12. **Persistent HTTP Client** - Single `httpx.AsyncClient` session reduces connection overhead.
13. **Parallel Frontend Fetching** - `Promise.all` used to fetch data for all accounts simultaneously.
14. **Smart Polling** - Adaptive polling in Webhook router (0.5s intervals) instead of fixed sleeps.

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

# Heartbeat Monitoring (Optional)
HEARTBEAT_WEBHOOK_URL=https://your-monitoring.com/webhook
HEARTBEAT_INTERVAL_SECONDS=60
HEARTBEAT_AUTH_TOKEN=your_secret_token
```

### Global Settings (Database)

| Key | Default | Description |
|-----|---------|-------------|
| `market_open_time` | "00:00" | Market opens (Brussels TZ) |
| `market_close_time` | "22:00" | Market closes |
| `weekend_markets_open` | false | Are futures markets open on weekends? |
| `blocked_periods_enabled` | true | Enable time blocks |
| `blocked_periods` | [] | JSON array of time blocks |
| `auto_flatten_enabled` | false | Daily auto-flatten |
| `auto_flatten_time` | "21:55" | Flatten time |
| `trading_days` | ["MON","TUE","WED","THU","FRI"] | Days when user wants to trade |
| `enforce_single_position_per_asset` | true | Block duplicate positions on same ticker |
| `enforce_single_position_per_asset` | true | Block duplicate positions on same ticker |
| `block_cross_account_opposite` | true | Block opposing positions across accounts |
| `calendar_discord_enabled` | false | Enable daily calendar briefing |
| `calendar_discord_url` | "" | Webhook URL for calendar |
| `calendar_major_countries` | ["USD"] | Countries to highlight/notify |
| `calendar_major_impacts` | ["High","Medium"] | Impacts to highlight/notify |
