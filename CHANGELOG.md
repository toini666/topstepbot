# Changelog

All notable changes to TopStepBot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [2026-01-18] - UI Refinements & Quick Fixes

### Added
- **Footer**: Added "Made with love" footer to the application.
- **Top Bar**: Merged "Disconnect" button into Account Selector dropdown for cleaner interface.
- **Top Bar**: Enhanced Status/Session indicators with badge styling.

### Fixed
- **Calendar**: Removed duplicate Globe icon in country filter dropdown.
- **Modals**: Fixed backdrop blur height issue (fullscreen overlay).
- **Cleanup**: Removed unused imports (`DiscordNotificationSettings`) in `ConfigModal`.

---

## [2026-01-19] - Shutdown & Reconciliation Fixes

### Fixed
- **Trade Reconciliation**: Fixed incorrect trade matching logic by implementing strict Fill-to-Round-Turn conversion.
- **Trade Reconciliation**: Fixed PnL and Fees aggregation for partial closes.
- **Trade Reconciliation**: Fixed "blue screen" crash in UI caused by missing `total_pnl_change` and undefined animations.
- **Startup**: Fixed race condition where "Shutdown complete" logs appeared during new process startup.
- **Startup**: Eliminated `asyncio.CancelledError` traceback during graceful shutdown.

---

## [2026-01-18] - News Trading Blocks & Position Action

### Added
- **Dynamic News Blocks**: Automatically block trading around major economic events (configurable buffer)
- **Position Action on Block**: Automatically `BREAKEVEN` or `FLATTEN` positions before entering a blocked period
- **News Block UI**: New settings section in ConfigModal to manage news blockers and position actions
- **News Block API**: New endpoint `/dashboard/news-blocks` to retrieve calculated daily blocks
- **Notification**: Daily Telegram summary of effective news trading blocks
- **Risk Engine Update**: `check_blocked_periods` now respects both manual and dynamic news blocks

### Changed
- **ConfigModal UI**: Refined layout moving News/Risk sections and implementing consistent UI patterns (toggles, inputs)

---

## [2026-01-18] - Unrealized PnL Display

### Added
- **Unrealized PnL**: Real-time floating PnL display for open positions
- **Price Cache Service**: In-memory caching of current contract prices with 5-second TTL
- **Price Refresh Job**: Scheduled task fetching prices every 5 seconds using `/api/History/retrieveBars`
- **Dashboard Current Price**: New "Current" column in Open Positions table showing live price
- **Dashboard PnL Column**: New "PnL" column with green/red styling based on profit/loss
- **Telegram `/status`**: Shows per-position unrealized PnL with emoji indicators
- **Telegram `/status_all`**: Shows per-account and total unrealized PnL in summary

---
## [2026-01-16] - Economic Calendar & Discord Improvements

### Added
- **Economic Calendar**: Automated daily event fetching (ForexFactory) and caching
- **Calendar Dashboard**: dedicated tab with "Today's Highlights" and Weekly Schedule
- **Calendar Filters**: Filter by Country, Impact, and Timeframe (Today/Week)
- **Discord Briefing**: Daily morning summary of major economic events (configurable)
- **Discord Integration**: Rich webhooks for Position Open/Close and Daily Summaries
- **Discord Avatar**: Custom generated flat-design robot avatar
- **Strategy & Timeframe**: Added to position close notifications

### Changed
- **ConfigModal**: New premium "Account Selector" dropdown in settings
- **Project Structure**: Consolidated debug scripts and tests into `scripts/debug/`
- **Documentation**: Updated architecture and PRD with Discord features

---

## [2026-01-15] - Ngrok Detection, Reconciliation & Dependencies

### Added
- **Ngrok URL Change Detection**: Automatically detects when the Ngrok webhook URL changes and notifies via Terminal, System Logs, and Telegram
- **Python 3.12 Support**: Upgraded from Python 3.9 to Python 3.12 for improved performance
- **Manual Trade Reconciliation**: Dashboard button to preview and apply trade corrections with TopStep API (disabled during open positions)

### Changed
- Upgraded all backend Python dependencies to latest versions
- Upgraded all frontend Node.js dependencies to latest versions
- Migrated Tailwind CSS from v3 to v4
- Updated `dependency-check` workflow to include Python/Node version checks
- Updated documentation to reflect Python 3.12+ requirement

---

## [2026-01-14] - Heartbeat & Formatting

### Added
- **Heartbeat Monitoring**: Periodic pings to external monitoring systems (N8N)
- **Graceful Shutdown Notifications**: Notifies monitoring on planned stops
- Unix timestamp field in heartbeat/shutdown payloads

### Changed
- Timestamp format improvements in webhook payloads

---

## [2026-01-13] - Trade Reconciliation & Manual Trades

### Added
- **Manual Trade Detection**: Automatically detects and tracks manually executed trades
- **Strict Reconciliation**: DB corrections based on API truth data

### Fixed
- Duplicate trade entries caused by race conditions
- Trade history aggregation accuracy

---

## [2026-01-12] - Multi-Account & Risk Management

### Added
- Configurable trading days (per-day toggles)
- "Allow trading outside sessions" toggle per strategy
- Partial TP execution with fill price in notifications
- API Health Check with consecutive failure alerts

### Changed
- Optimized position monitoring polling frequency

---

## [2026-01-11] - Security Audit Implementation

### Added
- TradingView IP whitelist for webhook security
- Restricted CORS methods (GET, POST, OPTIONS only)

### Fixed
- Bare `except:` clauses replaced with `except Exception:`
- TimePicker component behavior improvements

---

## [2026-01-09] - Risk Factor Refactor

### Added
- Per-strategy risk factor multipliers
- Contract limits (micro-equivalent) per account
- Blocked trading hours with individual enable/disable

### Changed
- Centralized frontend API configuration
- Optimized backend API interactions

---

## Format Guide

### Types of changes
- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** for vulnerability fixes
