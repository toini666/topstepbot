# Changelog

All notable changes to TopStepBot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [2026-05-17] - Risk Override Toggle & TopStep Commissions

### Added
- **Per-Account "Force 1 Contract Over Risk" Toggle**: New `allow_min_contract_over_risk` setting on `AccountSettings` (default OFF). When enabled, signals whose stop-loss distance would normally yield qty=0 (because risk-per-contract exceeds the configured `risk_per_trade`) are taken with a forced minimum of **1 contract** instead of being rejected. Every override triggers a WARNING log entry and a Telegram notification showing the real risk vs. the configured risk, so the user can audit the deviation.
- **Toggle Visible in Dashboard**: Account Details panel exposes the switch between "Max Contracts" and "Balance" with a tooltip explaining the behavior.

### Changed
- **Position Sizing Return**: `RiskEngine.calculate_position_size()` now returns `(qty, risk_per_contract)` instead of just `qty`, so callers can detect when the override kicked in and report the discrepancy.
- **Fees Include TopStep Commissions**: TopStep's `/api/Trade/search` exposes a new `commissions` field separate from the legacy `fees` field ($0.50 round-turn per micro contract). The bot now sums `fees + commissions` everywhere it reads fills:
  - `jobs/position_monitor.py` — full close, partial close, daily PnL aggregation, fallback exit fill.
  - `services/reconciliation_service.py` — round-turn builder.
  - `routers/webhook.py` — partial close fill aggregation.
  The combined total is stored in the existing `Trade.fees` column, so reconciliation, exports, Telegram/Discord notifications, and Discord summaries all show correct net PnL with no schema change. **Historical trades stored before this change keep their underestimated fees** — only trades closed from this version onward reflect the new total.
- **Trade History Table (Frontend)**: "Fees" column renamed to **"Fees + Comm."** with explanatory tooltip; "PnL" column renamed to **"Net PnL"** and now displays `gross_pnl - (fees + commissions)` instead of gross PnL. The cell tooltip shows the gross-vs-fees breakdown.

### Migration
- DB column `account_settings.allow_min_contract_over_risk BOOLEAN DEFAULT 0` added via Alembic migration `a3f7e2c91b04` and via the idempotent `backend/update_db_schema.py` (which `update.sh` / `update.ps1` now invoke automatically).
- The update scripts also reliably target the populated DB at the project root even when `backend/topstepbot.db` exists as an empty stub.

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
