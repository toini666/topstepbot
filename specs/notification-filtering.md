# Notification Filtering & System Logs

Filter Telegram notifications to reduce noise and add system logging for all notification types.

## User Review Required

> [!IMPORTANT]
> **Breaking Change**: SIGNAL/PARTIAL/CLOSE notifications will no longer be sent immediately upon webhook reception. They will only be sent when a trade is actually taken or explicitly rejected for a valid reason.

## Business Requirements

| ID | Requirement |
|----|-------------|
| BR-1 | SIGNAL notifications only sent if at least one eligible account exists OR if global rejection occurs |
| BR-2 | PARTIAL notifications only sent if a matching open position is found |
| BR-3 | CLOSE notifications only sent if a matching open position is found |
| BR-4 | Notify when trade rejected due to qty=0 (one notification per account) |
| BR-5 | Log all Telegram notifications in System Logs (like Discord) |

---

## Proposed Changes

### Backend Webhook Router

#### [MODIFY] [webhook.py](file:///Users/awagon/Documents/dev/topstepbot/backend/routers/webhook.py)

**SIGNAL Handler (lines 123-343)**:
- Move `notify_signal` call **after** eligibility checks (not before)
- Only call if `len(eligible_accounts) > 0` OR if global rejection occurred
- Add `notify_trade_rejection` call when qty=0 with reason "Position size < 1 contract"

```python
# BEFORE (current - line 136-152)
asyncio.create_task(_notify_signal_safe())  # Sent immediately!

# AFTER (new logic)
# 1. Run all validations first
# 2. Only notify SIGNAL if:
#    - Global rejection (market closed, blocked period, cross-account conflict)
#    - OR at least one eligible account found
# 3. Add qty=0 rejection notification per account
```

**PARTIAL Handler (lines 350-618)**:
- Remove immediate `notify_partial_signal` (lines 362-376)
- Only notify after finding matching trades

**CLOSE Handler (lines 625-777)**:
- Remove immediate `notify_close_signal` (lines 633-645)
- Only notify after finding matching trades

---

### Backend Telegram Service

#### [MODIFY] [telegram_service.py](file:///Users/awagon/Documents/dev/topstepbot/backend/services/telegram_service.py)

**Add logging after each send_message call**:

```python
async def send_message(self, message: str):
    # ... existing logic ...
    if response.status_code == 200:
        self._log_info(f"Telegram: Message sent successfully")
    # ...

def _log_info(self, message: str):
    """Log info to system logs."""
    db = SessionLocal()
    try:
        db.add(Log(level="INFO", message=message))
        db.commit()
    finally:
        db.close()
```

**Add more specific logging for each notification type**:
- `notify_signal`: Log `Telegram: Signal notification sent for {ticker}`
- `notify_partial_signal`: Log `Telegram: Partial signal notification sent for {ticker}`
- `notify_close_signal`: Log `Telegram: Close signal notification sent for {ticker}`
- `notify_trade_rejection`: Log `Telegram: Trade rejection notification sent for {ticker}`
- `notify_order_submitted`: Log `Telegram: Order submitted notification sent for {ticker}`
- etc.

---

## Data Flow

### Current Flow (SIGNAL)
```
Webhook received
    │
    ▼
┌─────────────────────────┐
│  notify_signal (SPAM!)  │ ← Sent for ALL signals
└─────────────────────────┘
    │
    ▼
Check market hours
    │
    ▼
Check blocked periods
    │
    ▼
Check per-account eligibility
    │
    ▼
Execute trades
```

### New Flow (SIGNAL)
```
Webhook received
    │
    ▼
Check market hours ─────────────────────┐
    │                                   │
    ▼                          (rejected)
Check blocked periods ──────────────────┤
    │                                   │
    ▼                                   ▼
Check per-account eligibility    ┌──────────────────────┐
    │                            │ notify_trade_rejection│
    ▼                            │ + notify_signal       │
┌───────────────────────┐        └──────────────────────┘
│ eligible_accounts > 0 │
└───────────────────────┘
    │ YES                 │ NO (no accounts configured)
    ▼                     ▼
┌────────────────┐   [No notification - silent skip]
│ notify_signal  │
└────────────────┘
    │
    ▼
Calculate qty per account
    │
    ├── qty > 0: Execute trade
    │
    └── qty = 0: notify_trade_rejection
                 "Position size < 1 contract (risk: $X, distance: Y ticks)"
```

---

## Implementation Checklist

### Phase 1: SIGNAL Filtering
- [ ] Move `notify_signal` call after eligibility validation
- [ ] Add condition: only send if eligible_accounts > 0 OR global rejection
- [ ] Add `notify_trade_rejection` for qty=0 with details
- [ ] Add System Log for qty=0 rejection

### Phase 2: PARTIAL/CLOSE Filtering  
- [ ] Move PARTIAL notification after matching trades found
- [ ] Move CLOSE notification after matching trades found

### Phase 3: Telegram System Logs
- [ ] Add `_log_info` method to TelegramService
- [ ] Add logging to `notify_signal`
- [ ] Add logging to `notify_partial_signal`
- [ ] Add logging to `notify_close_signal`
- [ ] Add logging to `notify_trade_rejection`
- [ ] Add logging to `notify_order_submitted`
- [ ] Add logging to `notify_position_opened`
- [ ] Add logging to `notify_position_closed`
- [ ] Add logging to `notify_partial_executed`
- [ ] Add logging to `notify_close_executed`

---

## Verification Plan

### Manual Testing

Since there are no automated tests for webhook/notification logic, manual testing is required:

1. **Test SIGNAL filtering (inactive strategy)**:
   - Send a webhook with a strategy not configured on any account
   - **Expected**: No Telegram notification, no System Log for signal
   
2. **Test SIGNAL filtering (active strategy)**:
   - Send a webhook with a strategy configured on at least one account
   - **Expected**: Telegram notification received, System Log shows "Telegram: Signal notification sent"

3. **Test SIGNAL rejection (market closed)**:
   - Configure market hours to exclude current time
   - Send a webhook with active strategy
   - **Expected**: "Signal Received" + "Trade Rejected" notifications

4. **Test qty=0 rejection**:
   - Configure very low risk amount (e.g., $1) with wide SL to get qty < 1
   - Send a webhook
   - **Expected**: "Signal Received" + "Trade Rejected: Position size < 1 contract" per account

5. **Test PARTIAL filtering**:
   - Send PARTIAL for ticker with no open position
   - **Expected**: No Telegram notification
   - Send PARTIAL for ticker with open position
   - **Expected**: Telegram notification received

6. **Test System Logs**:
   - Trigger various notifications
   - Check System Logs tab shows `Telegram: ...` entries

---

## Files to Modify

| File | Changes |
|------|---------|
| `backend/routers/webhook.py` | Move notification calls, add qty=0 rejection |
| `backend/services/telegram_service.py` | Add `_log_info`, add logging to all notify methods |
