# Changelog

All notable changes to TopStepBot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added
- **Ngrok URL Change Detection**: Automatically detects when the Ngrok webhook URL changes and notifies via Terminal, System Logs, and Telegram
- **Python 3.12 Support**: Upgraded from Python 3.9 to Python 3.12 for improved performance
- **Manual Trade Reconciliation**: Dashboard button to preview and apply trade corrections with TopStep API (disabled during open positions)

### Changed
- Updated `dependency-check` workflow to include Python/Node version checks
- Updated documentation to reflect Python 3.12+ requirement

---

## [2026-01-15] - Dependency & Security Update

### Changed
- Upgraded all backend Python dependencies to latest versions
- Upgraded all frontend Node.js dependencies to latest versions
- Migrated Tailwind CSS from v3 to v4
- Updated documentation to reflect new tech stack

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
