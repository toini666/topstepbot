# Bug Fixes & Improvements: Reconciliation, Notifications, Breakeven

## Executive Summary
This document outlines the plan to address three specific issues reported by the user:
1.  **Reconciliation Duplicates**: Fix a logic flaw where duplicate trades in the database are not detected/removed during reconciliation.
2.  **Partial TP Notifications**: Ensure Realized and Latent PnL are correctly fetched and displayed in notifications after a partial close.
3.  **Breakeven API Error**: specialized handling for "Order not found" errors during breakeven operations and fixing the "modified" count logging.

## Business Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| BR-1 | Reconciliation must detect and remove duplicate DB trades that do not match valid API round-turns. | High |
| BR-2 | Partial Close notifications must display the correct Realized PnL (from the exit fill). | High |
| BR-3 | Partial Close notifications must display the correct Latent PnL (based on remaining size). | High |
| BR-4 | Breakeven process must blindly handle "Order not found" errors without crashing or logging false positives. | Medium |
| BR-5 | Breakeven logging must accurately reflect the number of successfully modified orders. | Low |

## 1. Reconciliation Fix (Duplicates)

### Problem
The current reconciliation logic (`backend/services/reconciliation_service.py`) groups API fills into "Round Turns" and matches them with DB trades.
- If a DB trade matches a Round Turn, it is marked as matched.
- If a DB trade *does not* match (e.g., a duplicate entry), it falls into `orphan_db_trades`.
- The `orphan_db_trades` logic **only** proposes deletion if the trade's entry time matches an API *Exit* timestamp (lines 260-268).
- A duplicate *entry* (e.g. created by a manual error or race condition) that doesn't match an exit timestamp is ignored and left in the DB.

### Proposed Solution
Modify `preview_reconciliation` in `reconciliation_service.py`:
1.  Retain the matching logic for valid Round Turns.
2.  For `orphan_db_trades` (DB trades of the day that matched no closed API round turn):
    - Check if the trade status is `CLOSED`. If `CLOSED` and unmatched -> **Mark for Deletion**.
    - If `OPEN`:
        - Verify against *current* open positions (requires fetching `get_open_positions` or passing them in).
        - If the open trade in DB does not match any current open position in TopStep -> **Mark for Deletion** (or mark as CLOSED if it was actually closed but missed).
        - **Refinement**: Since `preview_reconciliation` currently only fetches `get_historical_trades` (fills), verifying OPEN trades exactly is harder without `get_open_positions`.
        - **Simpler Logic for Duplicates**: If we have two identical DB trades (same ticker, side, price, approx time), and only ONE matched an API Round Turn, the other MUST be a duplicate.
        - **New Logic**:
            - Iterate `orphan_db_trades`.
            - If an orphan trade looks like a duplicate of a *matched* trade (same params), mark it for **DELETE**.
            - If an orphan trade is `CLOSED` but unmatched, mark for **DELETE** (or flagging).

## 2. Partial TP Notification Fix (Missing PnL)

### Problem
In `backend/routers/webhook.py` -> `handle_partial`:
- A partial close is executed.
- The code waits 4s and fetches history.
- It tries to find the trade by matching `contract_id` and `qty == reduced_qty`.
- **Issue**: If the partial close results in multiple fills (e.g. closing 5 lots results in 2+3 fill), looking for a single fill with `qty=5` fails. The PnL remains 0.

### Proposed Solution
Modify `handle_partial` in `backend/routers/webhook.py`:
1.  After executing partial close, fetch historical trades (last 1 minute).
2.  Filter for fills that:
    - Match the `contract_id`.
    - Are `side` opposite to the position (closing).
    - Occurred *after* the request start time.
3.  **Sum** the quantities of these fills until they equal (or approximate) the `reduced_qty`.
4.  **Sum** the `profitAndLoss` and `fees` from these fills.
5.  Use these aggregated values for the notification.

This ensures that split fills are correctly accounted for.

## 3. Breakeven API Error Fix

### Problem
In `backend/main.py` -> `execute_breakeven_all`:
- The code calls `topstep_client.get_orders()`, which returns *all* orders for the day (filled, cancelled, etc.).
- The iteration logic (lines 728-734) picks the **first** order matching the `contract_id` and type `STOP/SL`.
- **CRITICAL BUG**: It does **not** check the order status. It often picks an old, already-filled, or cancelled order instead of the currently active Stop Loss.
- This results in `modify_order` failing with "Order not found" (because the ID is invalid for modification) even though a valid active order exists.

### Proposed Solution
1.  Update `backend/main.py` -> `execute_breakeven_all`:
    - When iterating orders, strictly filter for active statuses: `["Working", "Accepted", 1, 6]`.
    - Only select the order if it matches the status AND type.
    - Also implement the "Order not found" error handling improvement (check return value) as a safety net.
2.  Update `backend/services/topstep_client.py`:
    - Ensure `modify_order` returns `False` on failure without crashing.

## Files to Modify

### `backend/services/reconciliation_service.py`
- Update `preview_reconciliation` to detect duplicate/orphan trades more aggressively, specifically those that are duplicates of matched trades.

### `backend/routers/webhook.py`
- Update `handle_partial` to aggregate multiple fills for PnL calculation.

### `backend/main.py`
- Update `execute_breakeven_all` to check result of `modify_order` and handle "Order not found" gracefully.

## Risks & Mitigations
- **Reconciliation**: Aggressive deletion might delete valid manual trades if not careful.
    - *Mitigation*: Only delete orphans that look *exactly* like duplicates (same ticker, price, side, within small time window of a matched trade) OR are `CLOSED` with no matching API history.
- **Partial PnL**: matching wrong fills if high frequency trading.
    - *Mitigation*: Strict time window (last 5-10s) and contract ID matching.
