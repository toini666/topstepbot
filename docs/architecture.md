# TopStep Trading Bot - Technical Architecture

## System Overview

TopStep Bot is a FastAPI-based trading automation system that processes TradingView webhook alerts and executes trades on TopStepX accounts through their REST API. It provides multi-account management, hierarchical risk controls, real-time monitoring via a React dashboard, and notifications through Telegram and Discord.

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
                    │
                    ▼
              ┌──────────┐
              │ ForexFact│
              │ Calendar │
              └──────────┘
```

---

## Directory Structure

```
topstepbot/
├── backend/
│   ├── main.py                          # FastAPI app, lifespan, scheduler setup
│   ├── database.py                      # SQLAlchemy models & DB init
│   ├── schemas.py                       # Pydantic request/response schemas
│   ├── constants.py                     # Centralized config constants
│   ├── routers/
│   │   ├── webhook.py                   # TradingView signal processing
│   │   ├── dashboard.py                 # UI API endpoints & account controls
│   │   ├── strategies.py                # Strategy template CRUD
│   │   ├── calendar.py                  # Economic calendar endpoints
│   │   ├── mapping.py                   # Ticker mapping management
│   │   └── export.py                    # Data export & statistics
│   ├── services/
│   │   ├── topstep_client.py            # TopStepX API wrapper
│   │   ├── risk_engine.py               # Risk management logic
│   │   ├── settings_cache.py            # In-memory TTL settings cache
│   │   ├── price_cache.py               # Real-time price caching
│   │   ├── async_db.py                  # Async DB wrapper (thread pool)
│   │   ├── logging_service.py           # Structured logging + DB persistence
│   │   ├── telegram_service.py          # Telegram notifications
│   │   ├── telegram_bot.py              # Telegram command handler (polling)
│   │   ├── discord_service.py           # Discord webhook notifications
│   │   ├── calendar_service.py          # ForexFactory calendar + news blocks
│   │   ├── contract_validator.py        # Contract expiration validation
│   │   ├── maintenance_service.py       # Backup & log cleanup
│   │   ├── persistence_service.py       # JSON state persistence
│   │   ├── reconciliation_service.py    # Manual trade reconciliation
│   │   └── market_hub_client.py         # Market data integration
│   ├── jobs/
│   │   ├── state.py                     # Global state (positions, health, heartbeat)
│   │   ├── position_monitor.py          # Detect closed/partial positions (10s)
│   │   ├── price_refresh.py             # Refresh cached prices (10s)
│   │   ├── auto_flatten.py              # Scheduled position flatten (1m check)
│   │   ├── position_actions.py          # Pre-block SL/flatten actions (30s)
│   │   ├── health_checks.py             # API health + heartbeat monitoring
│   │   ├── discord_summary.py           # Daily Discord summary
│   │   ├── news_alert.py                # Pre-news Discord alerts (1m)
│   │   └── maintenance.py               # Auto-backups & log cleanup
│   └── alembic/                         # Database migrations
├── frontend/
│   ├── src/
│   │   ├── App.tsx                      # Main dashboard container
│   │   ├── main.tsx                     # Entry point
│   │   ├── config.ts                    # API base URL config
│   │   ├── types.ts                     # TypeScript interfaces
│   │   ├── index.css                    # Tailwind styles & custom utilities
│   │   ├── hooks/
│   │   │   └── useTopStep.ts            # Central data fetching & state hook
│   │   ├── utils/
│   │   │   └── tradeAggregator.ts       # Trade aggregation for display
│   │   └── components/
│   │       ├── dashboard/
│   │       │   ├── Header.tsx           # Status, account selector, daily PnL
│   │       │   ├── PositionsTable.tsx   # Open positions with close actions
│   │       │   ├── AccountDetails.tsx   # Balance, risk settings
│   │       │   ├── TradesHistory.tsx    # Closed trades with filters
│   │       │   ├── OrdersTable.tsx      # Order history
│   │       │   ├── LogsPanel.tsx        # System logs with JSON viewer
│   │       │   └── OrphanedOrdersWarning.tsx
│   │       ├── config-tabs/
│   │       │   ├── GeneralSettingsTab.tsx
│   │       │   ├── SessionsTab.tsx
│   │       │   └── NotificationsTab.tsx
│   │       ├── Calendar.tsx             # Economic calendar with filters
│   │       ├── ConfigModal.tsx          # Settings modal (4 tabs)
│   │       ├── ConfirmationModal.tsx    # Generic confirm dialog
│   │       ├── MockWebhookModal.tsx     # Test webhook signals
│   │       ├── ReconciliationModal.tsx  # Trade reconciliation UI
│   │       ├── StrategiesManager.tsx    # Global + per-account strategies
│   │       ├── TickerMapping.tsx        # TV → TopStep contract mapping
│   │       ├── RiskInput.tsx            # Inline editable risk field
│   │       └── TimePicker.tsx           # Time selection component
│   └── dist/                            # Built static files
├── backups/                             # Database backups
├── docs/                                # Documentation
└── start_bot.sh                         # Startup script
```

---

## Core Components

### 1. Database Layer (`database.py`)

SQLAlchemy ORM with SQLite. All tables created on startup via `init_db()`.

#### Models

| Model | Table | Purpose |
|-------|-------|---------|
| `Setting` | `settings` | Global key-value settings store (JSON strings) |
| `TradingSession` | `trading_sessions` | Session definitions (ASIA, UK, US) with time ranges |
| `TickerMap` | `ticker_maps` | TradingView → TopStep contract mapping + tick info |
| `Strategy` | `strategies` | Global strategy templates with default configs |
| `AccountSettings` | `account_settings` | Per-account trading config (risk, enabled, max contracts) |
| `AccountStrategyConfig` | `account_strategy_configs` | Strategy overrides per account (sessions, risk factor, partial %) |
| `DiscordNotificationSettings` | `discord_notification_settings` | Per-account Discord webhook preferences |
| `Trade` | `trades` | Local trade records with full lifecycle metadata |
| `Log` | `logs` | System event logs with level, message, details |

#### Trade Model Fields
```python
Trade:
  - id, account_id, ticker, action (BUY/SELL)
  - entry_price, signal_entry_price, exit_price, sl, tp
  - quantity, status (PENDING/OPEN/CLOSED/REJECTED)
  - pnl, fees
  - timeframe, session, strategy
  - timestamp, exit_time, duration_seconds
  - topstep_order_id, rejection_reason
```

#### Relationships
```
Strategy (1) ──→ (*) AccountStrategyConfig ←── (1) AccountSettings
TradingSession (global, seeded on startup)
TickerMap (global)
DiscordNotificationSettings (per account_id)
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

    # Validation Checks (all return Tuple[bool, str])
    check_market_hours()         # trading_days + market_open/close + weekend_markets_open
    check_blocked_periods()      # Manual blocks + dynamic news blocks
    check_account_enabled(account_id)
    check_strategy_enabled(account_id, strategy)
    check_session_allowed(account_id, strategy)   # Respects allow_outside_sessions
    check_open_position(account_id, ticker, client)  # Configurable toggle
    check_contract_limit(account_id, new_size)       # micro_equivalent weighted
    check_cross_account_direction(ticker, direction, client)  # Configurable toggle

    # Position Sizing
    get_risk_amount(account_id, strategy) → float
    calculate_position_size(entry, sl, risk, tick_size, tick_value) → int

# Standalone utility
calculate_unrealized_pnl(entry_price, current_price, quantity, is_long, tick_size, tick_value) → float
```

#### Settings Hierarchy
```
1. Strategy.default_* (base defaults from template)
2. AccountStrategyConfig.* (per-account overrides)
3. AccountSettings.risk_per_trade (account risk amount)
4. Applied: risk_per_trade × risk_factor = effective_risk
```

### 3. TopStep Client (`topstep_client.py`)

Async HTTP client for TopStepX API with automatic token management.

- **Persistent Connection**: Single `httpx.AsyncClient` session for the app lifecycle.
- **Circuit Breaker**: 60s cooldown on HTTP 429, tracks consecutive errors.
- **API Response Caching**: Short-TTL per-endpoint cache (5-10s).
- **Retry Logic**: Exponential backoff up to 5 retries.

#### API Endpoints Used

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/Auth/loginKey` | Authenticate with API key |
| POST | `/api/Account/search` | List trading accounts |
| POST | `/api/Position/searchOpen` | Get open positions |
| POST | `/api/Position/closeContract` | Close entire position |
| POST | `/api/Position/partialCloseContract` | Partial close position |
| POST | `/api/Order/search` | Get order history |
| POST | `/api/Order/place` | Place new order |
| POST | `/api/Order/modify` | Modify existing order |
| POST | `/api/Order/cancel` | Cancel order |
| POST | `/api/Contract/available` | List available contracts |
| POST | `/api/Trade/search` | Get trade history |
| POST | `/api/History/retrieveBars` | Get current price (1s bars) |
| POST | `/api/Status/ping` | API health check |

#### Order Types & Enums
```python
# Order Types
type: 1 = Limit, 2 = Market, 3 = Stop Limit, 4 = Stop

# Order Side
side: 0 = Buy, 1 = Sell

# Order Status
status: 1 = Working, 2 = Filled, 3 = Cancelled, 6 = Pending

# Position Type
type: 1 = Long, 2 = Short
```

### 4. Webhook Router (`webhook.py`)

Processes incoming TradingView alerts with IP whitelist verification and signal deduplication (30s TTL cache).

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
1. Verify source IP (TradingView whitelist + localhost)
2. Deduplicate signal (30s cache)
3. Route by type (SETUP/SIGNAL/PARTIAL/CLOSE)
4. For SIGNAL:
   a. Check market hours (global)
   b. Check blocked periods (manual + news blocks)
   c. Iterate ALL accounts:
      - Check account enabled
      - Check strategy enabled
      - Check session allowed
   d. Parallel async checks:
      - Check existing position per ticker
      - Check cross-account direction
   e. Resolve contract info (TickerMap)
   f. For each eligible account:
      - Calculate position size
      - Create Trade record (PENDING)
      - Execute in BackgroundTask

5. For PARTIAL:
   - Match open trades by ticker + timeframe + strategy
   - Calculate reduce_qty from strategy config
   - Execute partial close via TopStep API
   - Sync SL/TP order quantities
   - Optionally move SL to breakeven
   - Fetch realized PnL via trade history
   - Notify Telegram and Discord

6. For CLOSE:
   - Match open trades by ticker + timeframe + strategy
   - Close position and cancel related orders
   - Notify Telegram and Discord
```

### 5. Dashboard Router (`dashboard.py`)

REST API for frontend dashboard and account management.

#### Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/dashboard/status` | GET | Connection status |
| `/dashboard/market-status` | GET | Market open + current session |
| `/dashboard/config` | GET/POST | Global settings |
| `/dashboard/accounts` | GET | TopStep accounts list |
| `/dashboard/accounts/{id}/positions` | GET | Account positions (enriched with price/PnL) |
| `/dashboard/accounts/{id}/orders` | GET | Account orders |
| `/dashboard/accounts/{id}/trades` | GET | Account trade history |
| `/dashboard/trades` | GET | Local trade records |
| `/dashboard/logs` | GET | System logs (paginated) |
| `/dashboard/accounts/{id}/close-position` | POST | Close specific position |
| `/dashboard/accounts/{id}/toggle-trading` | POST | Toggle account trading |
| `/dashboard/account/{id}/flatten` | POST | Flatten single account |
| `/dashboard/flatten-all` | POST | Flatten all accounts |
| `/dashboard/reconcile/{id}/preview` | POST | Preview trade corrections |
| `/dashboard/reconcile/{id}/apply` | POST | Apply trade corrections |
| `/settings/accounts/{id}` | GET/POST | Account settings |
| `/settings/sessions` | GET/POST | Trading sessions |

### 6. Strategies Router (`strategies.py`)

Strategy template CRUD and per-account configuration.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/strategies/` | GET | List all templates |
| `/strategies/` | POST | Create template |
| `/strategies/{id}` | PUT | Update template |
| `/strategies/{id}` | DELETE | Delete template |
| `/settings/accounts/{id}/strategies` | GET | Get account configs |
| `/settings/accounts/{id}/strategies` | POST | Add/update account config |
| `/settings/accounts/{id}/strategies/{sid}` | DELETE | Remove from account |

### 7. Calendar Router (`calendar.py`)

Economic calendar data and news block settings.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/calendar/events` | GET | Get cached economic calendar |
| `/calendar/fetch` | POST | Force refresh from ForexFactory |
| `/calendar/settings` | GET/POST | News block settings |

### 8. Export Router (`export.py`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/export/trades` | GET | Export trades (JSON/CSV) |
| `/export/stats` | GET | Aggregated statistics |

Filter parameters: `status`, `strategy`, `timeframe`, `ticker`, `account_id`, `session`, `from_date`, `to_date`, `limit`

### 9. Mapping Router (`mapping.py`)

Ticker mapping management for TradingView → TopStep contract resolution.

---

## Core Services

### Settings Cache (`settings_cache.py`)

In-memory cache for frequently accessed configuration to minimize database I/O.

- **TTL Caching**: Global settings and account configs cached for 5s (configurable).
- **Thread-Safe**: Uses `threading.RLock` for concurrent access.
- **Smart Invalidation**: API updates automatically invalidate relevant cache keys.

### Async Database (`async_db.py`)

Wrapper to execute synchronous SQLAlchemy blocking calls in a dedicated thread pool, preventing `asyncio` event loop blocking.

```python
@async_db_session
def get_users(db):
    return db.query(User).all()

# Usage
users = await get_users()
```

### Logging Service (`logging_service.py`)

Centralized structured logger for console output and database persistence.

- **Console**: Color-coded output for readability.
- **Database**: Async persistence to `Log` table via `async_add_log`.
- **Security**: Automatic redaction of sensitive fields (api_key, token) in API logs.
- **Context**: Supports extra metadata (trade_id, account_name) for auditing.

### Discord Service (`discord_service.py`)

Discord webhook notifications with reliability features:

- **Rate Limit Handling**: Automatic HTTP 429 `Retry-After` backoff.
- **Connection Pooling**: Reuses HTTP connections for high-frequency messaging.
- **Rich Embeds**: Color-coded side indicators, PnL formatting, partial close details.
- **Per-Account Config**: Enable/disable per notification type.

### Calendar Service (`calendar_service.py`)

Economic calendar from ForexFactory XML feed:

- **Daily Fetch**: 7:00 AM Brussels, cached to local JSON file.
- **News Blocks**: Auto-generates trading blocks from major events (configurable buffer).
- **Throttling**: Max 1 fetch per 60s to respect source rate limits.
- **Timezone**: Auto-converts event times to Brussels timezone.

### Price Cache (`price_cache.py`)

In-memory price cache with 5s TTL for open position unrealized PnL calculations.

- Refreshed by `price_refresh_job` every 10s.
- Fetches via `/api/History/retrieveBars` (1s bars, 10s lookback).
- Returns `None` for expired prices (frontend shows "-").

### Contract Validator (`contract_validator.py`)

Daily validation of configured TickerMap entries against TopStep active contracts.

- Scheduled at 23:00 Brussels time.
- Sends Telegram alert if a mapped contract has expired or is invalid.

### Persistence Service (`persistence_service.py`)

JSON-based state persistence for graceful restart handling.

- Saves/restores `_last_open_positions` to avoid false notifications on restart.
- Tracks last known ngrok URL for change detection.

### Reconciliation Service (`reconciliation_service.py`)

Manual trade reconciliation between local DB and TopStep API trade history.

- Preview mode (dry-run) shows proposed changes.
- Apply mode corrects Trade records (status, PnL, fees).

---

## Scheduled Jobs

| Job | Interval | Purpose |
|-----|----------|---------|
| Position Monitor | 10s | Detect closed/partial positions, record PnL, notify |
| Price Refresh | 10s (offset +5s) | Refresh cached prices for unrealized PnL |
| Auto Flatten | 1m check | Close all positions at configured time |
| Position Action | 30s | Check upcoming blocks, execute BREAKEVEN/FLATTEN |
| API Health Check | 60s | Ping TopStep API, alert on consecutive failures |
| Heartbeat | Configurable (60s) | Send status to external monitor (N8N) |
| Discord Summary | 1m check | Send daily account summary at configured time |
| News Alert | 1m | Check for high-impact events in next N minutes |
| Calendar Fetch | Daily 07:00 Brussels | Fetch ForexFactory events, recalculate news blocks |
| Contract Validation | Daily 23:00 Brussels | Validate configured contracts vs TopStep API |
| Database Backup | Daily 03:00 UTC | Copy database file (keeps last 7) |
| Log Cleanup | Daily 03:15 UTC | Remove logs older than 7 days |

### Global State Management (`jobs/state.py`)

- `_last_open_positions`: Per-account position snapshots for change detection.
- `_last_orphans_ids`: Orphaned order IDs for alerting.
- `_api_health`: Consecutive failures count, last response time.
- `_heartbeat_state`: Start time, last sent, uptime calculation.
- `_handled_position_action_blocks`: Deduplication of block actions (reset daily).

---

## Trade History (Aggregated View)

The frontend displays trade history from the **internal Trade table** instead of raw TopStep API data.

### Benefits
- **Aggregated trades**: Entry + all partial TPs + final close shown as single line.
- **Consistent data**: PnL and fees are totals for the complete trade.
- **Precision**: Trades filtered by Symbol + Entry Timestamp (with 5s tolerance).
- **Strategy tracking**: Strategy name and timeframe preserved from webhook.

### Data Flow
```
1. Webhook opens trade → Trade record created (status=PENDING)
2. TopStep executes → Position appears in API
3. Position Monitor detects fill:
   - Updates Trade: status=OPEN, entry_price (from fill), preserves signal_entry_price
4. Position closes (SL/TP/manual) → Position disappears from API
5. Position Monitor detects closure:
   - Matches trade by Symbol AND Entry Timestamp (5s tolerance)
   - Fetches exit data from API Trade History
   - Updates Trade: status=CLOSED, exit_price, pnl, fees, exit_time
   - Sends Telegram & Discord notifications
6. Reconciliation Loop:
   - Checks for "phantom" OPEN trades in DB missing from API
   - Verifies against API History using timestamp comparison
   - Auto-corrects DB if confirmed closed
7. Manual Trade Detection:
   - Detects new positions not initiated by webhook
   - Creates Trade record with strategy="MANUAL"
   - Tracks through normal lifecycle
```

### Frontend Trade Aggregation (`tradeAggregator.ts`)
- FIFO matching of opens/closes by contract.
- Weighted average entry prices for multi-fill entries.
- Combined PnL and fees across matched fills.

---

## Telegram Bot Commands

Remote control and monitoring via Telegram polling bot.

### Monitoring Commands

| Command | Description |
|---------|-------------|
| `/status` | Current account balance, PnL, positions with unrealized PnL |
| `/status_all` | All accounts summary with per-account and total unrealized PnL |
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
| `/cancel_orders` | Cancel orders on current account |
| `/cancel_all` | Cancel orders on ALL accounts |
| `/flatten` | Flatten current account |
| `/flatten_all` | Flatten ALL accounts |

### Startup Notification
On bot startup, sends a summary of open positions across all accounts (or "Bot Online" if none).

---

## Frontend Architecture

### Technology Stack
- **React 19** with TypeScript 5
- **Vite 7** for build tooling
- **Tailwind CSS 4** with PostCSS
- **Axios** for HTTP requests
- **Sonner** for toast notifications
- **Lucide React** for icons
- **date-fns** for date formatting

### Main Hook (`useTopStep.ts`)

Centralized data management with smart polling.

```typescript
useTopStep() → {
  // Connection
  isConnected, loading, connect, logout, accounts

  // Per-Account Data
  positionsByAccount, ordersByAccount, tradesByAccount
  positions, orders, historicalTrades  // Selected account shortcuts

  // Settings
  globalConfig, accountSettings, tradingSessions, strategies
  updateGlobalConfig, updateAccountSettings, toggleAccountTrading

  // Actions
  closePosition, flattenAccount, flattenAllAccounts
  previewReconciliation, applyReconciliation

  // UI State
  selectedAccountId, historyFilter, marketStatus, logs, stats
}
```

### Polling Strategy
- **Static data** (config, sessions, strategies): Fetched once on mount.
- **Dynamic data**: 5s interval with smart sub-polling:
  - Positions: 5s when open, 15s when empty.
  - Orders: 30s.
  - Historical trades: 60s.
- **Parallel fetching**: All accounts fetched concurrently via `Promise.all`.
- **JSON comparison**: Prevents unnecessary React state updates.

### Component Structure

```
App.tsx
├── Header (status, account selector, daily PnL)
├── OrphanedOrdersWarning
├── Tab Navigation: Trading | Logs | Strategies | Calendar
│
├── Trading Tab
│   ├── PositionsTable (live positions, close/flatten)
│   ├── AccountDetails (balance, risk, toggle trading)
│   ├── TradesHistory (aggregated trades, strategy filter, reconcile)
│   └── OrdersTable (working/filled orders)
│
├── Logs Tab
│   └── LogsPanel (expandable, JSON viewer, pagination)
│
├── Strategies Tab
│   └── StrategiesManager
│       ├── Global Templates view (CRUD)
│       └── Account Strategies view (per-account config)
│
├── Calendar Tab
│   └── Calendar (major events, weekly table, filters, settings)
│
├── ConfigModal (4 tabs)
│   ├── GeneralSettingsTab (hours, days, blocks, position actions)
│   ├── SessionsTab (ASIA/UK/US time config)
│   ├── TickerMapping (TV → TopStep mapping)
│   └── NotificationsTab (Discord per account)
│
├── MockWebhookModal (test signals)
├── ConfirmationModal (danger/info)
└── ReconciliationModal (preview/apply)
```

### Styling
- Dark theme with Tailwind utilities.
- Custom CSS classes: `.btn-primary`, `.badge-success`, `.table-header`, `.modal-container`, etc.
- Animations: `.animate-fade-in`, `.animate-scale-in`.
- Responsive: Mobile-first with `sm`/`md`/`lg` breakpoints.

---

## Security

| Aspect | Implementation |
|--------|----------------|
| **Credentials** | Environment variables (.env file) |
| **Webhook Security** | TradingView IP whitelist (4 IPs) + localhost |
| **Signal Deduplication** | 30s TTL cache prevents duplicate execution |
| **API Authentication** | Bearer token, auto-refresh on 401 |
| **CORS** | Restricted to localhost:5173/5174 (GET, POST, OPTIONS) |
| **Input Validation** | Pydantic schemas for all inputs |
| **Log Redaction** | Sensitive data (api_key, token) masked in logs |

### TradingView IP Whitelist
```python
TRADINGVIEW_IPS = [
    "52.89.214.238",
    "34.212.75.30",
    "54.218.53.128",
    "52.32.178.7"
]
```

---

## Error Handling

| Scenario | Handling |
|----------|----------|
| TopStep API 401 | Clear token, re-authenticate |
| TopStep API 429 | Circuit breaker (60s cooldown), Telegram alert |
| TopStep API 502 | Wait 60s, retry (maintenance mode) |
| TopStep API 5xx | Exponential backoff (max 5 retries) |
| Order Rejection | Log reason, Telegram notification |
| Contract Not Found | Fallback to ticker as contract ID |
| Database Error | Rollback transaction, log error |
| Network Timeout | 15s timeout, graceful failure |
| Individual Account Failure | Skip account, continue with others |
| Notification Failure | Log error, don't abort execution |

---

## Performance Optimizations

1. **Persistent HTTP Client** - Single `httpx.AsyncClient` session reduces TCP/TLS overhead.
2. **Multi-Level Caching** - API responses (5-10s TTL), settings (5s TTL), calendar (daily), prices (5s TTL).
3. **Async Database** - Dedicated thread pool for DB operations, non-blocking event loop.
4. **Parallel Account Operations** - `asyncio.gather` for concurrent eligibility checks.
5. **Non-blocking Notifications** - Telegram/Discord dispatched via `asyncio.create_task`.
6. **SL/TP Retry Logic** - 3-attempt retry with 0.3s/0.5s delays for order corrections.
7. **Batch Processing** - Configurable batch sizes for cancel/close operations with rate limit delays.
8. **Background Execution** - Trade execution in FastAPI `BackgroundTasks`.
9. **Smart Frontend Polling** - Adaptive intervals (5s/15s/30s/60s) based on data type and state.
10. **JSON Comparison** - Frontend skips React state updates when data hasn't changed.
11. **Signal Deduplication** - 30s cache prevents duplicate webhook processing.
12. **Job Staggering** - Position monitor and price refresh offset by 5s to spread API load.

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

# Ngrok (Optional)
NGROK_AUTHTOKEN=your_ngrok_token
```

### Global Settings (Database)

| Key | Default | Description |
|-----|---------|-------------|
| `market_open_time` | "00:00" | Market opens (Brussels TZ) |
| `market_close_time` | "22:00" | Market closes |
| `weekend_markets_open` | false | Futures markets open on weekends? |
| `trading_days` | ["MON"-"FRI"] | Days when trading is allowed |
| `blocked_periods_enabled` | true | Enable manual time blocks |
| `blocked_periods` | [] | JSON array of time blocks |
| `auto_flatten_enabled` | false | Daily auto-flatten |
| `auto_flatten_time` | "21:55" | Flatten time |
| `enforce_single_position_per_asset` | true | Block duplicate positions per ticker |
| `block_cross_account_opposite` | true | Block opposing positions across accounts |
| `news_block_enabled` | false | Enable dynamic news blocks |
| `news_block_before_minutes` | 5 | Buffer before news event |
| `news_block_after_minutes` | 5 | Buffer after news event |
| `blocked_hours_position_action` | "NOTHING" | Action before blocks: NOTHING/BREAKEVEN/FLATTEN |
| `position_action_buffer_minutes` | 1 | Minutes before block to trigger action |
| `calendar_discord_enabled` | false | Enable daily calendar briefing |
| `calendar_discord_url` | "" | Webhook URL for calendar |
| `calendar_major_countries` | ["USD"] | Countries to highlight |
| `calendar_news_alert_enabled` | false | Enable pre-news Discord alerts |
| `calendar_news_alert_minutes` | 5 | Minutes before event to alert |

### Constants (`constants.py`)

Key configuration constants:

| Constant | Value | Purpose |
|----------|-------|---------|
| `API_TIMEOUT_SECONDS` | 15 | HTTP request timeout |
| `API_MAX_RETRIES` | 5 | Max retry attempts |
| `CIRCUIT_BREAKER_COOLDOWN_SECONDS` | 60 | Rate limit cooldown |
| `CACHE_TTL_POSITIONS` | 5 | Position cache TTL (seconds) |
| `CACHE_TTL_ACCOUNTS` | 10 | Account cache TTL (seconds) |
| `TRADE_MATCH_TIME_TOLERANCE_SECONDS` | 5 | Trade matching window |
| `DEFAULT_RISK_PER_TRADE` | 200.0 | Default risk amount ($) |
| `DEFAULT_MAX_CONTRACTS` | 50 | Default max micro-equivalent contracts |
| `BATCH_SIZE_CANCEL_ORDERS` | 10 | Parallel cancel batch size |
| `BATCH_SIZE_CLOSE_POSITIONS` | 5 | Parallel close batch size |

---

## Startup & Shutdown

### Startup Sequence
```
1. init_db() → Create all tables
2. topstep_client.startup() → Initialize persistent HTTP client
3. calendar_service.recalculate_news_blocks() → Load calendar cache
4. seed_default_sessions() → Create ASIA/UK/US sessions if missing
5. check_and_run_startup_backup() → Backup DB if none today
6. load_state() → Restore position snapshots from persistence.json
7. topstep_client.login() → Authenticate with TopStep
8. Pre-load positions for all accounts → Prevent false "new position" alerts
9. Send startup notification (Telegram with position summary)
10. Schedule all jobs (with max_instances=1, coalesce=True)
11. Start Telegram polling bot (background task)
```

### Shutdown Sequence
```
1. Stop scheduler (prevent new job runs)
2. Stop Telegram polling
3. Close persistent HTTP client
4. Send shutdown webhook (external monitoring)
5. Save state to persistence.json
6. Send Telegram shutdown notification
7. Wait for polling task to finish
```
