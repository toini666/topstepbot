# Changelog

All notable changes to TopStepBot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [2026-02-05] - Backend Performance & Frontend Optimization

### Added
- **Validation**: Added input validation for SL/TP prices in `webhook.py` (checks relative to Entry price and Side).
- **Smart Polling**: Implemented adaptive polling loop in `webhook.py` (checking every 0.5s instead of fixed sleep) to speed up trade settlement and confirmation.
- **Frontend Cadence**: Optimized `useTopStep.ts` with adaptive polling intervals (5s active/15s idle for positions, 30s orders, 60s trades) to reduce API load.

### Security
- **Log Redaction**: Implemented automatic redaction of sensitive keys (apikey, token, password) in API logs to prevent credential leakage.

### Changed
- **TopStepClient**: Refactored to use a **Persistent `httpx.AsyncClient`** for all requests, significantly reducing connection overhead and latency.
- **Async Logging**: Converted API call logging to asynchronous tasks `async_add_log` to prevent I/O blocking during critical execution paths.
- **Maintenance**: Switched database backup and log cleanup jobs to async implementations.
- **Position Monitoring**: 
    - Split `monitor_closed_positions_job` into **Async (API Fetch)** and **Sync (DB Processing)** phases.
    - Wrapped synchronous DB operations in `run_in_executor` to prevent blocking the main asyncio event loop.
    - **N+1 Fix**: Implemented batch fetching for `TickerMap` and `Trade` records, replacing iterative queries.
- **Frontend**: Refactored `useTopStep.ts` to fetch account data (positions, orders, trades) in **parallel** using `Promise.all`, drastically reducing dashboard load times for multi-account users.
- **Scheduler**: Added `max_instances=1` and `coalesce=True` to all scheduled jobs to prevent execution overlaps.
- **Discord Service**: Added console fallback logging for `notify_user` failures to ensure errors are visible even if DB logging fails.

### Fixed
- **Silent Exceptions**: Removed bare `except: pass` in `discord_service.py` logging methods.

---

## [2026-02-05] - Notification Fixes & News Alerts

### Added
### Added
- **News Alerts**: 
    - Implemented a new scheduled job that runs every minute to detect high-impact news events starting soon and sends a warning to Discord.
    - **Configurable**: Added "Pre-News Alerts" toggle and "Minutes Before" setting (default 5m) to the Calendar Dashboard.
- **Calendar Persistence**: Implemented file-based caching (`calendar_cache.json`) for economic calendar events. This ensures data availability on bot restart without triggering API rate limits.

### Fixed
- **Telegram Formatting**: Fixed `Bad Request` error when sending rejection notifications for position sizes < 1 contract by properly escaping HTML special characters.

---

## [2026-02-05] - Critical Audit Fixes
