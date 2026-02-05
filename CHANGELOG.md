# Changelog

All notable changes to TopStepBot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [2026-02-05] - Backend Performance & Frontend Optimization

### Added
- **Validation**: Added input validation for SL/TP prices in `webhook.py` (checks relative to Entry price and Side).
- **Smart Polling**: Implemented adaptive polling loop in `webhook.py` (checking every 0.5s instead of fixed sleep) to speed up trade settlement and confirmation.

### Changed
- **TopStepClient**: Refactored to use a **Persistent `httpx.AsyncClient`** for all requests, significantly reducing connection overhead and latency.
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

## [2026-02-05] - Critical Audit Fixes
