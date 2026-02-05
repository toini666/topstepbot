# Project Backlog: Roadmap to Professional Algorithmic Trading

This document outlines the roadmap to evolve the current functional prototype into a robust, professional-grade algorithmic trading system.

## 1. Advanced Risk Management (The "Guardian Pro")
*Goal: Protect capital with institutional-grade constraints.*
- [ ] **Consecutive Loss Kill Switch**: Pause trading for X minutes after N consecutive losses to prevent "tilt" or algo-spirals.
- [ ] **Alerting when trading unallowed**: In case a max drawdown on a ticker is reached, CME could stop quotation or Topstep could forbid to trade around specific price levels

## 2. Observability & Logging (Traceability)
*Goal: Know exactly what happened, when, and why.*
- [ ] **More logs in Telegram**: Add monitoring logs in Telegram in case of issue
- [ ] **Add in-app notifications**: Add in-app notifications for trades follow-up
- [ ] **External notifications management**: Configuration of external notifications (Discord / Telegram per signal)


## 3. Data & Analytics (The "Journal")
*Goal: Improve performance through data analysis.*
- [ ] **Equity Curve Plotting**: A chart in the dashboard showing P&L evolution over the day/week.
- [ ] **Win/Loss & Expectancy Stats**: Auto-calculate Sharpe Ratio, Profit Factor, and Average Win/Loss on the Stats panel.
- [ ] **Stats per strategy**: Dashboard with stats about each strategy.

## 4. Infrastructure & DevOps
*Goal: Stability and ease of deployment.*
- [ ] **Cloudflare Tunnel Integration**: Setup a permanent webhook URL (`https://bot.domaine.com`) to avoid daily ngrok reconfiguration.
- [ ] **Automated tests**: setup workflow of automated test to verify everything is still working (core features) after a development
- [x] **Execution optimization**: optimize workflow to have the minimum execution time between trading alert and trade execution
- [x] **Frontend Memory**: Implemented recursive polling, state update guards, and memoization to fix memory leaks.
- [x] **SL/TP Cache**: Fixed stale cache issues causing SL/TP update failures.
- [ ] **Refactor UI**: Harmonize UI, refactor look and feel, add footer and reorganize data visualization

## 5. Quick fixes / bugs
*Goal: Fix bugs and improve user experience.*
- [x] **API Rate Limit Handling**: Fix infinite retry loop on 429 errors with Circuit Breaker & Telegram alerts.
- [x] **Reconciliation**: Fixed duplicate trade detection using signature matching.
- [x] **Partial PnL**: Fixed missing PnL in notifications by aggregating multiple fills and filtering by PnL existence.
- [x] **Breakeven**: Fixed "Order not found" error by filtering for active orders only.
- [x] **Reconciliation**: Fixed TypeError when importing missing trades by parsing string timestamps to datetime objects.
- [x] **Discord Reliability**: Implemented robust rate-limit handling (429 retries) to prevent dropped notifications.
- [x] **Slippage Analytics**: Added signal price tracking and slippage display in Telegram notifications.



