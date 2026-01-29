# Implementation Plan - Partial PnL Logic Restoration

The user has indicated that the Partial PnL fixes might have been deleted or lost. I have inspected `backend/routers/webhook.py` and the fixes appear to be present, but I will rigorously verify and re-apply them if any discrepancy is found.

## User Review Required
> [!NOTE]
> I will verify the current code against the required logic. If the code is already correct, I will notify you and restart the backend to ensure the running version is up to date.

## Proposed Changes

### Backend
#### [VERIFY] [webhook.py](file:///Users/awagon/Documents/dev/topstepbot/backend/routers/webhook.py)
- **Goal**: Ensure the `handle_partial` function contains:
    1.  **Size Key Check**: `t.get('size')` must be checked before `quantity`.
    2.  **PnL Filter**: Logic must filter by `profitAndLoss is not None` and ignore `side`.

- **Action**:
    - If code matches: Do nothing (Logic is safe).
    - If code is missing/different: Re-apply the specific changes.

#### [MODIFY] [main.py](file:///Users/awagon/Documents/dev/topstepbot/backend/main.py)
- **Goal**: Ensure News Blocks are calculated on startup. currently, the calendar is only fetched at 7 AM, leaving the bot blind to news if restarted during the day.
- **Action**:
    - Call `await calendar_service.recalculate_news_blocks()` inside the `lifespan` startup sequence.
    - This will fetch the calendar and populate `_today_news_blocks` without sending duplicate notifications.

## Verification Plan

### Manual Verification
- **Partial PnL**:
    - **Code Inspection**: I have already viewed the file, but I will confirm the lines match exactly.
- **News Blocks**:
    - **Log Review**: After restart, check logs for "Recalculated news blocks" to confirm it ran.
    - **Dashboard**: Check if the "News Block" is now visible in the settings/status.
- **Backend Restart**: I will restart the backend service to ensure the latest file version is loaded in memory.

### Frontend
#### [MODIFY] [Calendar.tsx](file:///Users/awagon/Documents/dev/topstepbot/frontend/src/components/Calendar.tsx)
- **Goal**: Fix the "Settings" modal to be properly centered and have a full-screen backdrop.
- **Action**:
    - Locate the modal JSX (likely conditionally rendered).
    - Ensure the backdrop `div` uses `fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm`.
    - Ensure the modal content `div` has `relative` positioning and appropriate max-width/height.
    - Remove any hardcoded `top`/`left` or `translate` transforms if flex centering is used.

### Backend
#### [MODIFY] [reconciliation_service.py](file:///Users/awagon/Documents/dev/topstepbot/backend/services/reconciliation_service.py)
- **Goal**: Allow reconciliation to **import** missing trades from TopStep that are not in the DB.
- **Action**:
    - In `preview_reconciliation`, identify `api_round_turns` that were NOT matched to any DB trade.
    - For each unmatched round-turn, propose a `create` change.
    - Update `apply_reconciliation` to handle `type: "create"` by inserting a new `Trade` record with status `CLOSED` (since round-turns are completed trades).
