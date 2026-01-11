# TopStep Trading Bot - Product Requirements Document

## Executive Summary

TopStep Bot is an automated trading system that bridges TradingView alerts with TopStepX trading accounts. It enables rule-based trade execution with comprehensive risk management, multi-account support, and real-time monitoring through a modern web dashboard and Telegram notifications.

---

## Product Vision

**For** discretionary traders using TradingView strategies  
**Who** need automated execution on TopStepX prop firm accounts  
**TopStep Bot** is an automation platform  
**That** executes trades with built-in risk controls and multi-account management  
**Unlike** manual order entry or basic webhook bots  
**Our product** provides hierarchical settings, session-aware trading, and comprehensive analytics

---

## Core Features

### 1. Automated Trade Execution

| Feature | Description |
|---------|-------------|
| **TradingView Webhooks** | Receives 4 alert types: SETUP, SIGNAL, PARTIAL, CLOSE |
| **Market Orders with Brackets** | Places market orders with automatic SL/TP brackets |
| **Position Sizing** | Auto-calculates quantity based on risk amount and stop distance |
| **Contract Resolution** | Automatically maps TV tickers (MNQ1!) to TopStep contracts |

### 2. Multi-Account Trading

| Feature | Description |
|---------|-------------|
| **Simultaneous Execution** | Signals execute on ALL configured accounts |
| **Per-Account Settings** | Independent risk amount, trading enabled status |
| **Cross-Account Protection** | Prevents opposing positions on same asset across accounts |
| **Account-Specific Strategies** | Different strategies enabled per account |

### 3. Hierarchical Settings System

```
Global Settings (all accounts)
├── Market Hours (open/close times)
├── Blocked Trading Periods
├── Auto-Flatten Time
└── Trading Sessions (ASIA, UK, US)

Account Settings (per account)
├── Trading Enabled (pause/resume)
├── Risk Per Trade ($)
└── Strategy Configurations
    ├── Risk Factor (multiplier)
    ├── Allowed Sessions
    ├── Partial TP %
    └── Move SL to Breakeven
```

### 4. Risk Management

| Control | Description |
|---------|-------------|
| **Single Position Rule** | Maximum 1 position per ticker per account |
| **Cross-Account Direction** | Cannot hold opposing positions across accounts |
| **Session Restrictions** | Strategies only execute during allowed sessions |
| **Market Hours Filter** | Blocks trades outside configured hours |
| **Blocked Periods** | Custom time blocks where trading is disabled |
| **Force Flatten** | Manual and scheduled flatten-all capability |

### 5. Alert Types

#### SETUP
- **Purpose**: Informational only, logged for reference
- **Action**: No trade execution
- **Use Case**: Record price levels or pattern formations

#### SIGNAL
- **Purpose**: Open new position
- **Required Fields**: ticker, side (BUY/SELL), entry, stop, tp, timeframe, strat
- **Action**: Opens position with SL/TP on all eligible accounts

#### PARTIAL
- **Purpose**: Take partial profits
- **Matching**: By ticker + timeframe + strategy
- **Action**: Reduces position by configured %, optionally moves SL to entry

#### CLOSE
- **Purpose**: Close entire position
- **Matching**: By ticker + timeframe + strategy
- **Action**: Closes position and cancels related orders

### 6. Dashboard Interface

| Section | Features |
|---------|----------|
| **Header** | Connection status, market status, current session |
| **Account Selector** | Switch between accounts, trading toggle |
| **Open Positions** | Live positions with strategy/timeframe, close button |
| **Account Details** | Balance, risk per trade (editable), trading status |
| **Trade History** | Aggregated trades with strategy filter, PnL display |
| **Order History** | Working and filled orders |
| **System Logs** | Timestamped logs with load more pagination |

### 7. Telegram Integration

| Notification Type | Content |
|-------------------|---------|
| **Signal Received** | Ticker, action, prices, strategy, timeframe |
| **Order Submitted** | Ticker, quantity, account name |
| **Position Opened** | Entry price, side, quantity |
| **Position Closed** | PnL, fees, duration |
| **Partial Executed** | Reduced qty, remaining, SL moved status |
| **Trade Rejection** | Ticker, reason, account |
| **Orphaned Orders** | Warning for orders without positions |

### 8. Data & Analytics

| Feature | Description |
|---------|-------------|
| **Trade Recording** | All trades stored with full metadata |
| **Export Endpoint** | JSON/CSV export with filters |
| **Statistics API** | Win rate, profit factor, avg PnL, duration |
| **Filter Options** | By strategy, timeframe, ticker, account, session, date |

### 9. Maintenance & Reliability

| Feature | Description |
|---------|-------------|
| **Daily Backups** | Automatic at 03:00 UTC, keeps last 7 |
| **Startup Backup** | Creates backup if none exists for today |
| **Log Cleaning** | Removes logs older than 7 days at 04:00 UTC |
| **Position Monitoring** | Detects closed positions for notifications |
| **Orphan Detection** | Alerts for orders without matching positions |

---

## User Personas

### Primary: Discretionary Prop Trader
- Uses TradingView for chart analysis and alerts
- Trades multiple TopStepX accounts (evaluation + funded)
- Needs consistent execution across accounts
- Values risk management and position sizing

### Secondary: Strategy Developer
- Tests multiple strategies simultaneously
- Needs per-strategy performance tracking
- Exports data for optimization analysis

---

## Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| **Latency** | < 500ms from webhook to order submission |
| **Uptime** | Designed for 24/5 operation (market hours) |
| **Data Retention** | Trades: indefinite, Logs: 7 days |
| **Concurrent Accounts** | Tested up to 5 accounts |
| **API Compatibility** | TopStepX ProjectX Gateway API |

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.9+, FastAPI, SQLAlchemy, SQLite |
| **Frontend** | React 18, TypeScript, Vite, TailwindCSS |
| **Scheduling** | APScheduler |
| **Notifications** | Telegram Bot API |
| **External API** | TopStepX REST API |

---

## Future Roadmap

1. **Performance Dashboard** - Visual charts for PnL curves, drawdown analysis
2. **Automated Exports** - Scheduled CSV exports to cloud storage
3. **Strategy Backtesting** - Historical replay of signals
4. **Multi-Broker Support** - Extend beyond TopStepX
5. **Mobile App** - Native iOS/Android dashboard
