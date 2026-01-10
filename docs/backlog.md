# Project Backlog: Roadmap to Professional Algorithmic Trading

This document outlines the roadmap to evolve the current functional prototype into a robust, professional-grade algorithmic trading system.

## 1. Advanced Risk Management (The "Guardian Pro")
*Goal: Protect capital with institutional-grade constraints.*
- [ ] **Trailing Max Drawdown**: Implement a session-based trailing drawdown (e.g., if equity peaks at +$500, stop out if it drops back to +$100).
- [ ] **News Event Filter**: Integrate an economic calendar API (e.g., ForexFactory or similar). Automatically BLOCK trading 5 mins before/after specific events (NFP, CPI, FOMC).
- [ ] **Max Open Exposure**: Limit the total number of contracts open simultaneously across all matching symbols.
- [ ] **Consecutive Loss Kill Switch**: Pause trading for X minutes after N consecutive losses to prevent "tilt" or algo-spirals.

## 2. Order Execution & Strategy Engine
*Goal: Fine-tune how orders are managed after entry.*
- [ ] **Breakeven Trigger**: Auto-move Stop Loss to Entry Price after the price moves X ticks in favor.
- [ ] **Trailing Stop Loss**: Locally manage a trailing stop that moves up with price (handling the detailed updates via API).
- [ ] **Scale-Out Logic (Partial TPs)**: Support signal inputs that specify multiple Take Profit levels (e.g., Sell 50% at TP1, 50% at TP2).
- [x] **Emergency Flatten Button**: A "PANIC" button in the UI that cancels all pending orders and closes all open positions immediately.
- [x] **Manual Position Close**: Ability to close individual positions directly from the dashboard.

## 3. Observability & Logging (Traceability)
*Goal: Know exactly what happened, when, and why.*
- [x] **Telegram/Discord Notifications**: **(COMPLETED)** Implemented full 2-way Telegram Bot.
    - Commands: Status, Flatten, Cancel Orders, Login/Logout, Switch Account.
    - Notifications: Order Fills, Risk Rejections, PnL.
- [ ] **Heartbeat Monitoring**: A background watchdog that pings the TopStep API every minute. If connection drops, send a critical alert to the user.
- [ ] **Structured File Logging**: Rotate logs daily (e.g., `/logs/2026-01-08-trading.log`). Critical for audit trails if the database fails.
- [ ] **Snapshot Recorder**: Capture the state of the "Order Book" or price at the moment of execution (if data available) for slippage analysis.

## 4. Data & Analytics (The "Journal")
*Goal: Improve performance through data analysis.*
- [ ] **Equity Curve Plotting**: A chart in the dashboard showing P&L evolution over the day/week.
- [x] **Real-time Daily PnL**: View realized P&L for the day directly in the header stats (Net PnL displayed in Telegram).
- [ ] **Trade Reconciliation**: A nightly job that downloads all official trades from TopStep API and checks them against local DB to find discrepancies (slippage, missed fills).
- [x] **Strategy Tagging**: **(COMPLETED)** Added "Strategy Tags" to incoming webhooks (e.g., "RobReversal") to label trades in the dashboard.
- [ ] **Win/Loss & Expectancy Stats**: Auto-calculate Sharpe Ratio, Profit Factor, and Average Win/Loss on the Stats panel.

## 5. Infrastructure & DevOps
*Goal: Stability and ease of deployment.*
- [ ] **Cloudflare Tunnel Integration**: Setup a permanent webhook URL (`https://bot.domaine.com`) to avoid daily ngrok reconfiguration.
- [ ] **Dockerization**: Create a `docker-compose.yml` to spin up Backend, Frontend, and Database in one command. Essential for eventual VPS deployment.
- [ ] **Database Migration**: Move from SQLite to PostgreSQL if trade volume becomes high or for better concurrency.

## 6. Recently Completed (v1.2 Reliability & Simulation)
- [x] **Mock API & Simulation**: Implemented a full UI interface to trigger mock webhooks, allowing rapid testing of trade logic and risk rules without live market data.
- [x] **Robust Trade Execution**: Fixed `Modify Order` API calls to properly handle SL/TP updates (using `stopPrice`/`limitPrice`).
- [x] **Auto-Cancel on Close**: Closing a position manually now automatically finds and cancels all associated SL/TP orders ("Orphan Protection").
- [x] **Custom Account Selector**: Replaced native HTML select with a styled, custom dropdown.
- [x] **Smart History Filtering**: "Today" filter now strictly respects local midnight start time.
