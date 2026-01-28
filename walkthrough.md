# Walkthrough: Bug Fixes (Reconciliation, Notifications, Breakeven)

This document details the changes made to address three specific bugs reported by the user.

## 1. Reconciliation Duplicates

### Change
Updated `backend/services/reconciliation_service.py` to improve duplicate detection.

### Logic
- **Pre-Grouped Trades**: Before iterating orphans, we now group confirmed "matched" trades by their signature (Ticker + Side + Price + Time).
- **Duplicate Check**: When analyzing an "orphan" trade (a trade in DB not matched to a valid API Round Turn):
    - We check if it matches the signature of a *matched* trade (within 60s tolerance).
    - If it matches, it is flagged as a **duplicate** and marked for deletion.
- **Closed Orphans**: If a trade is marked `CLOSED` in DB but has no matching API history today, it is also flagged for deletion (likely a ghost trade or manual error).

## 2. Partial TP Notifications (Missing PnL)

### Change
Updated `backend/routers/webhook.py` inside `handle_partial`.

### Logic
- **Issue**: Previously, the code looked for a *single* fill matching the exact `reduced_qty`. If TopStep split the fill (e.g. 5 lots -> 2 + 3), the single-search failed, resulting in $0 PnL/Fees in notifications.
- **Fix**:
    - The code now fetches all recent fills for the contract.
    - It iterates through them (newest to oldest) and **accumulates** quantity, PnL, and Fees until the `reduced_qty` is reached.
    - **CRITICAL FIX 1**: Updated logic to check the `size` key (which TopStep returns) instead of just `quantity`.
    - **CRITICAL FIX 2**: Removed ambiguous Side filtering (checking Buy vs Sell). Instead, we now strictly filter for trades *with a PnL value* (entries have None PnL, exits have Realized PnL). This guarantees we only aggregate the closing portion.
    - This aggregated PnL is used for the "Realized PnL" notification.

## 3. Breakeven API Error ("Order not found")

### Change
Updated `backend/main.py` inside `execute_breakeven_all`.

### Logic
- **Issue**: The code was selecting the *first* order matching the contract ID and type `STOP/SL`, regardless of status. It often picked a cancelled or filled order, causing `modify_order` to fail with "Order not found".
- **Fix**:
    - Added a strict status filter: `if order_status not in ["Working", "Accepted", 1, 6]: continue`.
    - Added error handling to `modify_order` to return `False` on failure.
    - Added logic to skip incrementing the `total_modified` counter if the modification failed.

## Verification
- **Backend Startup**: Confirmed successful startup with no syntax errors.
- **Logs**: Monitor `backend.log` for:
    - `RECONCILIATION: Delete duplicate of #...` (when duplicate occurs)
    - `PARTIAL: Aggregated X qty...` (on partial close)
    - `BREAKEVEN: Failed to modify...` (if API rejects, but should be rarer now)
