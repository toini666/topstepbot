# TopStep Trading Bot - Product Requirements Document

## Executive Summary

TopStep Bot is an automated trading system that bridges TradingView alerts with TopStepX trading accounts. It enables rule-based trade execution with comprehensive risk management, multi-account support, and real-time monitoring through a modern web dashboard, Telegram bot, and Discord notifications.

---

## Product Vision

**For** discretionary traders using TradingView strategies
**Who** need automated execution on TopStepX prop firm accounts
**TopStep Bot** is an automation platform
**That** executes trades with built-in risk controls and multi-account management
**Unlike** manual order entry or basic webhook bots
**Our product** provides hierarchical settings, session-aware trading, economic calendar integration, and comprehensive analytics

---

## Core Features

### 1. Automated Trade Execution

| Feature | Description |
|---------|-------------|
| **TradingView Webhooks** | Receives 4 alert types: SETUP, SIGNAL, PARTIAL, CLOSE |
| **Market Orders with Brackets** | Places market orders with automatic SL/TP bracket orders |
| **Position Sizing** | Auto-calculates quantity based on risk amount and stop distance |
| **Contract Resolution** | Maps TV tickers (MNQ1!) to TopStep contracts via TickerMap |
| **Signal Deduplication** | 30s TTL cache prevents duplicate execution |

### 2. Multi-Account Trading

| Feature | Description |
|---------|-------------|
| **Simultaneous Execution** | Signals execute on ALL configured accounts in parallel |
| **Per-Account Settings** | Independent risk amount, max contracts, trading enabled status |
| **Cross-Account Protection** | Prevents opposing positions on same asset across accounts (configurable) |
| **Account-Specific Strategies** | Different strategies and configs enabled per account |
| **Graceful Degradation** | Individual account failures don't block other accounts |

### 3. Hierarchical Settings System

```
Global Settings (all accounts)
├── Market Hours (open/close times, Brussels TZ)
├── Weekend Markets Open (toggle)
├── Trading Days (MON-SUN toggles)
├── Blocked Trading Periods (manual time blocks)
├── News Blocks (auto-generated from economic calendar)
├── Position Action on Blocks (NOTHING / BREAKEVEN / FLATTEN)
├── Auto-Flatten Time
├── Trading Sessions (ASIA, UK, US with time ranges)
├── Single Position Per Asset (toggle)
└── Block Cross-Account Opposite (toggle)

Account Settings (per account)
├── Trading Enabled (pause/resume)
├── Risk Per Trade ($)
├── Max Contracts (micro-equivalent)
└── Strategy Configurations
    ├── Enabled (toggle)
    ├── Risk Factor (multiplier)
    ├── Allowed Sessions (ASIA, UK, US)
    ├── Allow Outside Sessions
    ├── Partial TP %
    └── Move SL to Breakeven
```

### 4. Risk Management

| Control | Description |
|---------|-------------|
| **Single Position Rule** | Max 1 position per ticker per account (configurable) |
| **Cross-Account Direction** | Cannot hold opposing positions across accounts (configurable) |
| **Trading Days** | Configurable day-of-week toggles |
| **Session Restrictions** | Strategies only execute during allowed sessions |
| **Allow Outside Sessions** | Per-strategy override via "OUTSIDE" session option |
| **Market Hours Filter** | Blocks trades outside configured hours |
| **Blocked Periods** | Custom time blocks where trading is disabled |
| **News Blocks** | Dynamic trading blocks based on major economic events |
| **Contract Limit** | Maximum contracts (micro-equivalent) per account |
| **Force Flatten** | Manual and scheduled flatten-all capability |
| **Position Action** | Automatic BREAKEVEN/FLATTEN before entering blocked periods |

### 5. Alert Types

#### SETUP
- **Purpose**: Informational only, logged for reference
- **Action**: No trade execution
- **Use Case**: Record price levels or pattern formations

#### SIGNAL
- **Purpose**: Open new position
- **Required Fields**: ticker, side (BUY/SELL), entry, stop, tp, timeframe, strat
- **Action**: Opens position with SL/TP brackets on all eligible accounts

#### PARTIAL
- **Purpose**: Take partial profits
- **Matching**: By ticker + timeframe + strategy (finds matching OPEN trades)
- **Action**: Reduces position via `partialCloseContract` API
- **Post-Actions**: Syncs SL/TP order quantities, optionally moves SL to breakeven
- **Feedback**: Returns Realized PnL (closed portion) and Unrealized PnL (remaining)

#### CLOSE
- **Purpose**: Close entire position
- **Matching**: By ticker + timeframe + strategy
- **Action**: Closes position and cancels all related orders

### 6. Dashboard Interface

| Section | Features |
|---------|----------|
| **Header** | Connection status, market status, current session, daily PnL, active positions count |
| **Account Selector** | Dropdown to switch between accounts |
| **Open Positions** | Live positions with strategy/timeframe, current price, unrealized PnL, close button |
| **Account Details** | Balance, editable risk per trade, max contracts, trading toggle |
| **Trade History** | Aggregated trades (entry + partials = 1 line), strategy filter, time filter, reconciliation button |
| **Order History** | Working and filled orders with type/status |
| **System Logs** | Timestamped logs with expandable JSON details, pagination |
| **Orphaned Orders Warning** | Alert for orders without matching positions |

### 7. Telegram Integration

| Notification Type | Content |
|-------------------|---------|
| **Signal Received** | Ticker, action, prices, strategy, timeframe |
| **Order Submitted** | Ticker, quantity, account name |
| **Position Opened** | Entry price, side, quantity, signal price, slippage (ticks) |
| **Position Closed** | PnL, fees, duration, daily PnL |
| **Partial Executed** | Reduced qty, remaining, fill price, SL moved status, realized + unrealized PnL |
| **Trade Rejection** | Ticker, reason, account |
| **Orphaned Orders** | Warning for orders without positions |
| **Trading Toggled** | Account name, new status |
| **System Events** | Startup (with positions summary), shutdown, API health, ngrok URL changes |
| `/status` | Balance, daily PnL, positions with per-position unrealized PnL |
| `/status_all` | All accounts with per-account and total unrealized PnL |

#### Telegram Bot Commands

| Command | Description |
|---------|-------------|
| `/status` | Current account status |
| `/status_all` | All accounts summary |
| `/accounts` | List accounts with IDs |
| `/switch [ID]` | Change active account |
| `/on` / `/off` | Enable/disable trading (current account) |
| `/on_all` / `/off_all` | Enable/disable trading (ALL accounts) |
| `/flatten` / `/flatten_all` | Flatten current / ALL accounts |
| `/cancel_orders` / `/cancel_all` | Cancel orders on current / ALL accounts |
| `/login` / `/logout` | Connect / disconnect TopStep API |

### 8. Discord Integration

- **Platform**: Rich embed notifications via webhooks
- **Content**: Position Open/Close, Partial Close (with PnL breakdown), Daily Summaries
- **Configuration**: Per-account toggles for enabled/disabled, specific notification types (`notify_position_open`, `notify_position_close`, `notify_partial_close`, `notify_daily_summary`), and summary scheduling
- **Reliability**: Rate-limit handling (429 retries) and connection pooling

### 9. Data & Analytics

| Feature | Description |
|---------|-------------|
| **Trade Recording** | Trades matched by Symbol + Timestamp (5s tolerance) for precise PnL aggregation |
| **Manual Trades** | Automatically detects and records non-bot trades (strategy="MANUAL") |
| **Daily PnL** | Real-time Net PnL calculation (Gross - Fees) |
| **Unrealized PnL** | Floating PnL for open positions (10s refresh) with cached market prices |
| **Auto Reconciliation** | Detects "phantom" OPEN trades in DB missing from API, auto-corrects via history |
| **Manual Reconciliation** | Dashboard button to preview and apply trade corrections |
| **Export** | JSON/CSV export with filters (status, strategy, timeframe, ticker, account, session, date) |
| **Statistics** | Win rate, profit factor, avg PnL, avg duration |
| **Trade Aggregation** | Frontend FIFO matching with weighted average entry prices |

### 10. Economic Calendar

- **Source**: ForexFactory (XML feed)
- **Features**:
  - Daily 7:00 AM fetch (Brussels TZ) + local JSON cache
  - Manual refresh via dashboard button (60s throttle)
  - "Today's Major Events" dashboard card (filterable by impact/country)
  - Weekly schedule table with impact/country/day filters
  - Discord daily briefing (morning summary)
  - Pre-event Discord alerts (configurable N minutes before)
  - Timezone-aware (auto-converts to Brussels)
- **News Blocks Integration**:
  - Auto-converts major events into trading blocks
  - Configurable buffer time before and after events
  - Integrated into risk engine `check_blocked_periods()`

### 11. Contract Validation

- **Schedule**: Daily at 23:00 (Brussels)
- **Function**: Validates all configured `TickerMap` entries against TopStep active contracts
- **Alerts**: Telegram notification if mapped contract is expired/invalid

### 12. Automated Position Actions

- **Trigger**: Approach of any blocked period (manual or news)
- **Actions**:
  - **NOTHING**: Default, no action taken
  - **BREAKEVEN**: Moves SL to entry price for all open positions
  - **FLATTEN**: Closes all positions and cancels orders
- **Buffer**: Configurable minutes before block start to execute action
- **Deduplication**: Each block only triggers action once (reset daily)

### 13. Maintenance & Reliability

| Feature | Description |
|---------|-------------|
| **Daily Backups** | Automatic at 03:00 UTC, keeps last 7 |
| **Startup Backup** | Creates backup if none exists for today |
| **Log Cleanup** | Removes logs older than 7 days at 03:15 UTC |
| **Position Monitoring** | Detects closed/partial positions every 10s |
| **Orphan Detection** | Alerts for orders without matching positions |
| **API Health Check** | Pings TopStep every 60s, alerts on consecutive failures |
| **Heartbeat** | Sends status to external monitor (N8N) with uptime, trading state |
| **Graceful Shutdown** | Notifies monitoring, saves state, sends Telegram notification |
| **State Persistence** | Saves position snapshots to JSON for restart recovery |
| **Ngrok URL Detection** | Notifies user when webhook URL changes |
| **Manual Trade Sync** | Detects and tracks manually executed trades |
| **Signal Deduplication** | 30s cache prevents double execution |

---

## User Personas

### Primary: Discretionary Prop Trader
- Uses TradingView for chart analysis and alerts
- Trades multiple TopStepX accounts (evaluation + funded)
- Needs consistent execution across accounts
- Values risk management and position sizing
- Wants remote monitoring and control via Telegram

### Secondary: Strategy Developer
- Tests multiple strategies simultaneously
- Needs per-strategy performance tracking
- Exports data for optimization analysis
- Uses economic calendar to avoid news events

---

## Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| **Latency** | < 500ms from webhook to order submission |
| **Uptime** | Designed for 24/5 operation (market hours) |
| **Data Retention** | Trades: indefinite, Logs: 7 days |
| **Concurrent Accounts** | Tested up to 5 accounts |
| **API Compatibility** | TopStepX ProjectX Gateway API |
| **Resilience** | Circuit breaker, retry logic, graceful degradation |

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.12+, FastAPI, SQLAlchemy, SQLite, APScheduler |
| **Frontend** | React 19, TypeScript 5, Vite 7, Tailwind CSS 4 |
| **HTTP Client** | httpx (async, persistent connections) |
| **Notifications** | Telegram Bot API, Discord Webhooks |
| **External APIs** | TopStepX REST API, ForexFactory XML Feed |
| **State** | SQLite (persistent), In-memory caches (TTL), JSON (persistence) |

---

## Future Roadmap

1. **Performance Dashboard** - Visual charts for PnL curves, drawdown analysis
2. **Automated Exports** - Scheduled CSV exports to cloud storage
3. **Strategy Backtesting** - Historical replay of signals
4. **Multi-Broker Support** - Extend beyond TopStepX
5. **Mobile App** - Native iOS/Android dashboard
