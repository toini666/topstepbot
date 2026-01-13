# TopStep Trading Bot - Execution Flows & Logic

This document details the exact sequences, validations, and API calls for all trading operations.

---

## Table of Contents

1. [Webhook Signal Flow](#1-webhook-signal-flow)
2. [Partial Take-Profit Flow](#2-partial-take-profit-flow)
3. [Close Signal Flow](#3-close-signal-flow)
4. [Position Monitoring Flow](#4-position-monitoring-flow)
5. [Force Flatten Flow](#5-force-flatten-flow)
6. [Cross-Account Direction Check](#6-cross-account-direction-check)
7. [Session Validation Logic](#7-session-validation-logic)
8. [Position Sizing Calculation](#8-position-sizing-calculation)

9. [Strategy Configuration Management](#9-strategy-configuration-management)
10. [API Health Check Flow](#10-api-health-check-flow)

---

## 1. Webhook Signal Flow

### Trigger
TradingView sends POST to `/api/webhook` with alert payload.

### Sequence Diagram

```
TradingView         Webhook Router         RiskEngine          TopStep API
    │                     │                     │                    │
    │── POST /webhook ───▶│                     │                    │
    │                     │                     │                    │
    │                     │── Verify IP ────────│                    │
    │                     │   (TradingView IPs) │                    │
    │                     │   ❌ 403 if invalid │                    │
    │                     │                     │                    │
    │                     │── Log Reception ───▶│                    │
    │                     │                     │                    │
    │                     │◀─ Notify Signal ────│                    │
    │                     │   (Telegram)        │                    │
    │                     │                     │                    │
    ├─────────────────────┼─ GLOBAL CHECKS ─────┼────────────────────┤
    │                     │                     │                    │
    │                     │── check_market_hours()                   │
    │                     │◀─ (bool, reason) ───│                    │
    │                     │                     │                    │
    │                     │── check_blocked_periods()                │
    │                     │◀─ (bool, reason) ───│                    │
    │                     │                     │                    │
    ├─────────────────────┼─ GET ACCOUNTS ──────┼────────────────────┤
    │                     │                     │                    │
    │                     │─────────────────────┼── get_accounts() ─▶│
    │                     │                     │◀─ accounts[] ──────│
    │                     │                     │                    │
    ├─────────────────────┼─ PER-ACCOUNT LOOP ──┼────────────────────┤
    │                     │                     │                    │
    │                     │── ensure_account_settings(id) ──────────▶│
    │                     │                     │                    │
    │                     │── check_account_enabled(id)              │
    │                     │◀─ (bool, reason) ───│                    │
    │                     │                     │                    │
    │                     │── check_strategy_enabled(id, strat)      │
    │                     │◀─ (bool, reason) ───│                    │
    │                     │                     │                    │
    │                     │── check_session_allowed(id, strat)       │
    │                     │◀─ (bool, reason) ───│                    │
    │                     │                     │                    │

    │                     │                     │                    │
    │                     │── check_contract_limit(id, qty)          │
    │                     │◀─ (bool, reason) ───│                    │
    │                     │                     │                    │
    │                     │── check_open_position(id, ticker) ──────▶│
    │                     │                     │◀─ positions[] ─────│
    │                     │◀─ (bool, reason) ───│                    │
    │                     │                     │                    │
    │                     │── → Add to eligible_accounts[] ─────────▶│
    │                     │                     │                    │
    ├─────────────────────┼─ CROSS-ACCOUNT ─────┼────────────────────┤
    │                     │                     │                    │
    │                     │── check_cross_account_direction() ──────▶│
    │                     │   (checks ALL accounts for opposing)     │
    │                     │◀─ (bool, reason) ───│                    │
    │                     │                     │                    │
    ├─────────────────────┼─ CONTRACT RESOLVE ──┼────────────────────┤
    │                     │                     │                    │
    │                     │── Check TickerMap (DB) ─────────────────▶│
    │                     │── OR get_contract_details() ────────────▶│
    │                     │                     │◀─ contract info ───│
    │                     │                     │                    │
    ├─────────────────────┼─ EXECUTE LOOP ──────┼────────────────────┤
    │                     │                     │                    │
    │   FOR EACH ELIGIBLE ACCOUNT:              │                    │
    │                     │                     │                    │
    │                     │── get_risk_amount(id, strat) ───────────▶│
    │                     │◀─ $amount ──────────│                    │
    │                     │                     │                    │
    │                     │── calculate_position_size()              │
    │                     │◀─ quantity ─────────│                    │
    │                     │                     │                    │
    │                     │── Create Trade record (DB)               │
    │                     │   status=PENDING, session=current        │
    │                     │                     │                    │
    │                     │── BackgroundTask: execute_trade()        │
    │                     │                     │                    │
    │                     │                     │── place_order() ──▶│
    │                     │                     │   (Market + SL/TP) │
    │                     │                     │◀─ orderId ─────────│
    │                     │                     │                    │
    │                     │                     │── Notify Submitted │
    │                     │                     │   (Telegram)       │
    │                     │                     │                    │
    │                     │                     │── Sleep 1s         │
    │                     │                     │                    │
    │                     │                     │── update_sl_tp()──▶│
    │                     │                     │   (Fix prices)     │
    │                     │                     │                    │
    │◀─ Response: {status, accounts} ───────────│                    │
```

### Validation Checklist

| Step | Check | Fail Action |
|------|-------|-------------|
| 0 | IP in TradingView whitelist | HTTP 403 Forbidden |
| 1 | Market hours open | Reject all, log WARNING |
| 2 | Not in blocked period | Reject all, log WARNING |
| 3 | Account trading_enabled | Skip account, log DEBUG |
| 4 | Strategy enabled on account | Skip account, log DEBUG |
| 5 | Session allowed for strategy | Skip account, log DEBUG |
| 6 | No existing position on ticker | Skip account, log INFO |
| 7 | No opposing cross-account position | Reject all, log WARNING |
| 8 | Contract resolved | Reject all, log ERROR |
| 9 | Position size > 0 | Skip account, log WARNING |

---

## 2. Partial Take-Profit Flow

### Trigger
TradingView sends `type: "PARTIAL"` webhook.

### Matching Logic
```python
matching_trades = db.query(Trade).filter(
    Trade.ticker == alert.ticker,
    Trade.timeframe == alert.timeframe,
    Trade.strategy == alert.strat,
    Trade.status == "OPEN"
).all()
```

### Sequence

```
1. Receive PARTIAL webhook
2. Notify partial signal (Telegram) - includes accounts count
3. Query DB for matching open trades
4. FOR EACH matching trade:
   a. Get account_id from trade
   b. Load AccountStrategyConfig
   c. Get partial_tp_percent & move_sl_to_entry settings
   d. Call TopStep: get_open_positions(account_id)
   e. Find matching position by ticker
   f. Calculate reduce_qty:
      - reduce_qty = max(1, int(current_size × partial_percent / 100))
      - If reduce_qty >= current_size: reduce_qty = current_size - 1
      - If reduce_qty <= 0: skip
   g. Call TopStep: `partialCloseContract(account_id, contractId, reduce_qty)`
   h. **CRITICAL: Sync remaining SL/TP order quantities**
      - Call sync_order_quantities(account_id, ticker, remaining_qty)
      - Updates all working SL/TP orders to match new position size
      - Prevents over-closing when SL/TP is triggered
   i. If move_sl_to_entry: call update_sl_tp_orders() with entry_price
   j. If alert has new SL/TP: update_sl_tp_orders()
   k. Notify partial executed (Telegram) - includes side emoji & BE status
5. Return processed accounts
```

### Rounding Logic
```python
# Always rounds DOWN (conservative)
reduce_qty = max(1, int(current_size * (partial_percent / 100)))

# Examples:
# 3 contracts × 50% = 1.5 → 1 contract
# 5 contracts × 50% = 2.5 → 2 contracts
# 2 contracts × 50% = 1.0 → 1 contract
```

### Order Quantity Sync (Critical Fix)
```python
async def sync_order_quantities(account_id, ticker, new_quantity):
    """
    After partial close, SL/TP orders still have original quantity.
    This syncs them to remaining position size to prevent over-closing.
    """
    orders = await get_orders(account_id, days=1)
    
    for order in orders:
        if order is SL/TP type and matches ticker:
            if order.size != new_quantity:
                await modify_order(order_id, size=new_quantity)
```

---

## 3. Close Signal Flow

### Trigger
TradingView sends `type: "CLOSE"` webhook.

### Sequence

```
1. Receive CLOSE webhook
2. Notify close signal (Telegram)
3. Query DB for matching open trades (same as PARTIAL)
4. FOR EACH matching trade:
   a. Get account_id from trade
   b. Call TopStep: close_position(account_id, ticker)
   c. Call TopStep: cancel_all_orders(account_id)
   d. Update Trade record: status=CLOSED, exit_time=now
   e. Notify close executed (Telegram)
5. Return processed accounts
```

---

## 4. Position Monitoring Flow

### Trigger
Scheduled job every 30 seconds.

### Purpose
Detect positions closed externally (TP hit, SL hit, manual close).

### Startup Behavior
On bot startup, existing positions are pre-loaded to avoid false "Position Opened" notifications:

```
1. Login to TopStep
2. Fetch all accounts
3. FOR EACH account:
   a. Get current positions
   b. Store in _last_open_positions[account_id]
   c. Collect for summary
4. Send startup notification:
   - If positions exist: Summary with all positions (contract, side, qty, account)
   - If no positions: Standard "Bot Online" message
```

### Runtime Sequence

```
1. Load previous positions from memory (per account)
2. FOR EACH connected account:
   a. Fetch current positions from TopStep
   b. Compare with previous snapshot
   c. FOR EACH position in previous but NOT in current:
      - Position was closed
      - Fetch trade history to get exit details
      - Calculate PnL and fees
      - **UPDATE Trade record in database:**
        * Find matching Trade by account_id + ticker + status=OPEN
        * Set status=CLOSED, exit_price, pnl, fees, exit_time
      - Calculate Daily PnL total
      - Notify position closed (Telegram) with daily PnL
   d. Update memory with current positions
3. Check for orphaned orders (ALL accounts):
   a. Get working orders from ALL accounts
   b. Get open positions from ALL accounts
   c. Orders for contracts without positions = orphans
   d. If orphans found → Notify (Telegram) with account names
```

### Data Structures
```python
# Memory State
_last_open_positions = {
    account_id: {
        "CON.F.US.MNQ.H6": {position_data},
        ...
    }
}

_last_orphans_ids = {order_id1, order_id2, ...}
```

---

## 5. Force Flatten Flow

### Trigger
- Manual: Dashboard "Flatten & Cancel All" button
- Scheduled: Auto-flatten at configured time

### Per-Account Flatten

```
1. Call TopStep: get_open_positions(account_id)
2. FOR EACH position:
   a. Call TopStep: close_position(account_id, contractId)
3. Call TopStep: cancel_all_orders(account_id)
4. Log action
5. Notify flatten (Telegram)
```

### All-Accounts Flatten

```
1. Call TopStep: get_accounts()
2. FOR EACH account:
   a. Execute per-account flatten
3. Notify flatten_all (Telegram)
```

### Auto-Flatten Job

```python
async def auto_flatten_job():
    settings = get_global_settings()
    if not settings["auto_flatten_enabled"]:
        return
    
    now = datetime.now(BRUSSELS_TZ)
    target_time = parse(settings["auto_flatten_time"])
    
    if now.strftime("%H:%M") == target_time:
        await flatten_all_accounts()
```

---

## 6. Cross-Account Direction Check

### Purpose
Prevent opening BUY on Account A if SHORT exists on Account B for same ticker.
**This check is configurable via `block_cross_account_opposite` global setting.**

### Logic

```python
async def check_cross_account_direction(ticker, direction, client):
    # Check if rule is enabled
    global_settings = get_global_settings()
    if not global_settings.get("block_cross_account_opposite", True):
        return True, "Cross-account check disabled"
    
    clean_ticker = normalize(ticker)
    accounts = await client.get_accounts()
    
    for account in accounts:
        positions = await client.get_open_positions(account["id"])
        
        for pos in positions:
            if clean_ticker in pos["contractId"]:
                pos_side = "LONG" if pos["type"] == 1 else "SHORT"
                signal_side = "LONG" if direction in ["BUY", "LONG"] else "SHORT"
                
                if pos_side != signal_side:
                    return False, f"Opposing {pos_side} exists on {account['name']}"
    
    return True, ""
```

### Scenarios

| Account A | Account B | Signal | Result |
|-----------|-----------|--------|--------|
| No MNQ | No MNQ | BUY MNQ | ✅ Execute both |
| LONG MNQ | No MNQ | BUY MNQ | ⚠️ Skip A (exists), ✅ Execute B |
| LONG MNQ | No MNQ | SELL MNQ | ❌ Block all (opposing) |
| SHORT MNQ | SHORT MNQ | SELL MNQ | ⚠️ Skip all (exists) |

---

## 7. Session Validation Logic

### Session Definitions (Brussels TZ)

| Session | Start | End |
|---------|-------|-----|
| ASIA | 00:00 | 08:59 |
| UK | 09:00 | 15:29 |
| US | 15:30 | 21:59 |

### Current Session Detection

```python
def get_current_session():
    now_bru = datetime.now(BRUSSELS_TZ).time()
    
    for session in db.query(TradingSession).all():
        if not session.is_active:
            continue
        
        start = parse_time(session.start_time)
        end = parse_time(session.end_time)
        
        if start <= now_bru <= end:
            return session.name
    
    return None
```

### Strategy Session Check

```python
def check_session_allowed(account_id, strategy_tv_id):
    current_session = get_current_session()
    config = get_strategy_config(account_id, strategy_tv_id)
    
    # If no active session, check allow_outside_sessions
    if not current_session:
        if config and config.allow_outside_sessions:
            return True, "Allowed outside sessions"
        return False, "Outside all trading sessions"
    
    if not config:
        return True, ""  # No config = use defaults
    
    allowed = config.allowed_sessions.split(",")
    
    if current_session in allowed:
        return True, ""
    
    # Not in allowed session, check allow_outside_sessions
    if config.allow_outside_sessions:
        return True, "Allowed outside defined sessions"
    
    return False, f"Session {current_session} not allowed"
```

---

## 8. Position Sizing Calculation

### Formula

```python
def calculate_position_size(entry_price, sl_price, risk_amount, tick_size, tick_value):
    # 1. Calculate stop distance in price
    stop_distance = abs(entry_price - sl_price)
    
    # 2. Convert to ticks
    ticks_at_risk = stop_distance / tick_size
    
    # 3. Calculate risk per contract
    risk_per_contract = ticks_at_risk * tick_value
    
    # 4. Calculate quantity
    if risk_per_contract <= 0:
        return 1  # Minimum
    
    qty = risk_amount / risk_per_contract
    
    # 5. Round down to integer
    return max(1, int(qty))
```

### Example

```
Entry: 20000.00
Stop: 19980.00
Risk Amount: $200
Tick Size: 0.25
Tick Value: $0.50

Stop Distance = |20000 - 19980| = 20 points
Ticks at Risk = 20 / 0.25 = 80 ticks
Risk per Contract = 80 × $0.50 = $40
Quantity = $200 / $40 = 5 contracts
```

### Effective Risk Calculation

```python
def get_risk_amount(account_id, strategy_tv_id):
    # 1. Get account base risk
    account_settings = get_account_settings(account_id)
    base_risk = account_settings.risk_per_trade  # e.g., $200
    
    # 2. Get strategy risk factor
    config = get_strategy_config(account_id, strategy_tv_id)
    factor = config.risk_factor if config else 1.0  # e.g., 0.5
    
    # 3. Calculate effective risk
    return base_risk * factor  # $200 × 0.5 = $100
```

---

## API Response Codes

### Webhook Responses

| Response | Meaning |
|----------|---------|
| `{status: "received", accounts: [...]}` | Signal processing on listed accounts |
| `{status: "rejected", reason: "..."}` | Global check failed |
| `{status: "skipped", reason: "..."}` | No eligible accounts |
| `{status: "processed", accounts: [...]}` | PARTIAL/CLOSE executed |
| `{status: "error", reason: "..."}` | System error |

### TopStep API Responses

| Field | Values |
|-------|--------|
| `success` | true/false |
| `errorCode` | 0 = Success |
| `errorMessage` | Human-readable error |

---

## 9. Strategy Configuration Management

### Overview

Strategy configurations exist at two levels:
1. **Global Templates** (`Strategy` table) - Default settings for each strategy
2. **Per-Account Configs** (`AccountStrategyConfig` table) - Overrides per account

### Data Model Hierarchy

```
Strategy (Global Template)
├── name, tv_id
├── default_risk_factor (e.g., 1.0)
├── default_allowed_sessions (e.g., "ASIA,UK,US")
├── default_partial_tp_percent (e.g., 50)
└── default_move_sl_to_entry (e.g., true)

AccountStrategyConfig (Per-Account Override)
├── account_id, strategy_id
├── enabled (bool)
├── risk_factor (overrides default)
├── allowed_sessions (overrides default)
├── partial_tp_percent (overrides default)
├── move_sl_to_entry (overrides default)
└── allow_outside_sessions (trade outside defined sessions)
```

### Configuration Flow

```
1. User creates Strategy Template (Global)
   - Defines default_* values
   
2. User adds Strategy to Account
   - Creates AccountStrategyConfig
   - Copies defaults from template
   
3. User edits Account Config (inline via UI)
   - Modifies: sessions, risk_factor, partial_%, SL→BE
   - Changes apply ONLY to that account
   
4. Signal Processing uses per-account values:
   - risk_factor from AccountStrategyConfig
   - allowed_sessions from AccountStrategyConfig
   - NOT from Strategy template
```

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `GET /strategies/` | GET | List all templates |
| `POST /strategies/` | POST | Create template |
| `PUT /strategies/{id}` | PUT | Update template |
| `DELETE /strategies/{id}` | DELETE | Delete template |
| `GET /settings/accounts/{id}/strategies` | GET | Get account configs |
| `POST /settings/accounts/{id}/strategies` | POST | Add/update account config |
| `DELETE /settings/accounts/{id}/strategies/{sid}` | DELETE | Remove from account |

### Important Notes

1. **Template changes don't propagate** - Modifying a global template does NOT update existing AccountStrategyConfigs. Changes only affect NEW additions.

2. **Risk calculation uses account config** - The `get_risk_amount()` function uses `AccountStrategyConfig.risk_factor`, not `Strategy.default_risk_factor`.



3. **All operations are logged** - Create/update/delete operations on both templates and account configs are recorded in System Logs with JSON details.

---

## 10. API Health Check Flow

### Trigger
Scheduled job every 60 seconds (backend).

### Sequence
```
1. Call TopStep: GET /api/Status/ping
2. Calculate response time (ms)
3. IF Success (200 OK):
   a. Update global health state (healthy=True)
   b. Reset failures counter = 0
   c. IF previously DOWN:
      - Log INFO "API Recovered"
      - Send recovery notification (Telegram)
4. IF Failure (4xx/5xx/Timeout):
   a. Update global health state (healthy=False)
   b. Increment failures counter
   c. Log ERROR "API Ping Failed"
   d. IF failures >= 3 AND not notified:
      - Send DOWN notification (Telegram)
      - Set notified flag = True
```
