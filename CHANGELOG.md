# Changelog

All notable changes to TopStepBot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
