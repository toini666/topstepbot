# Project Backlog: Roadmap to Professional Algorithmic Trading

This document outlines the roadmap to evolve the current functional prototype into a robust, professional-grade algorithmic trading system.

## 1. Advanced Risk Management (The "Guardian Pro")
*Goal: Protect capital with institutional-grade constraints.*
- [ ] **News Event Filter**: Integrate an economic calendar API (e.g., ForexFactory or similar). Automatically BLOCK trading 5 mins before/after specific events (NFP, CPI, FOMC).
- [ ] **Consecutive Loss Kill Switch**: Pause trading for X minutes after N consecutive losses to prevent "tilt" or algo-spirals.
- [ ] **Alerting when trading unallowed**: In case a max drawdown on a ticker is reached, CME could stop quotation or Topstep could forbid to trade around specific price levels

## 2. Observability & Logging (Traceability)
*Goal: Know exactly what happened, when, and why.*
- [ ] **More logs in Telegram**: Add monitoring logs in Telegram in case of issue

## 3. Data & Analytics (The "Journal")
*Goal: Improve performance through data analysis.*
- [ ] **Equity Curve Plotting**: A chart in the dashboard showing P&L evolution over the day/week.
- [ ] **Win/Loss & Expectancy Stats**: Auto-calculate Sharpe Ratio, Profit Factor, and Average Win/Loss on the Stats panel.
- [ ] **Stats per strategy**: Dashboard with stats about each strategy.

## 4. Infrastructure & DevOps
*Goal: Stability and ease of deployment.*
- [ ] **Cloudflare Tunnel Integration**: Setup a permanent webhook URL (`https://bot.domaine.com`) to avoid daily ngrok reconfiguration.
